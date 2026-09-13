"""Independent workbook recomputation; never imports preparation logic."""

from __future__ import annotations

import hashlib
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from ._online_manual_check import load_manual_check


class ValidationFailure(RuntimeError):
    pass


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def norm(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", text(value))
    return "".join(char for char in raw if not unicodedata.combining(char)).casefold()


def number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value.strip()[:10], pattern).date()
            except ValueError:
                pass
    return None


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def headers(values: Iterable[Any]) -> dict[str, int]:
    return {norm(value): index for index, value in enumerate(values) if text(value)}


def field(row: tuple[Any, ...], index: dict[str, int], *names: str) -> Any:
    for name in names:
        position = index.get(norm(name))
        if position is not None and position < len(row):
            return row[position]
    return None


def read_sheet(
    path: Path, sheet: str, header_row: int
) -> tuple[list[Any], list[tuple[Any, ...]]]:
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = book[sheet]
        header = list(
            next(
                worksheet.iter_rows(
                    min_row=header_row, max_row=header_row, values_only=True
                )
            )
        )
        return header, list(
            worksheet.iter_rows(min_row=header_row + 1, values_only=True)
        )
    finally:
        book.close()


def close(
    left: float, right: float, label: str, failures: list[str], tolerance: float = 0.01
) -> None:
    if abs(left - right) > tolerance:
        failures.append(f"{label}: expected {left:.6f}, payload {right:.6f}")


def payload_rows(
    payload: dict[str, Any], key: str, width: int, failures: list[str]
) -> list[list[Any]]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        failures.append(f"payload {key} is not a list")
        return []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, list) or len(row) != width:
            failures.append(
                f"payload {key} row {index} has width {len(row) if isinstance(row, list) else 'non-list'}, expected {width}"
            )
            break
    return rows


def stable_mismatch_key(row: list[Any]) -> tuple[str, str, str]:
    return (text(row[1]), text(row[2]), text(row[3]))


def load_prior_keys(path: Path) -> set[tuple[str, str, str]]:
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = book["Mismatch"]
        return {
            (text(row[1]), text(row[2]), text(row[3]))
            for row in worksheet.iter_rows(min_row=4, values_only=True)
            if len(row) >= 4 and any(value not in (None, "") for value in row)
        }
    finally:
        book.close()


def validate(
    payload: dict[str, Any], sources: dict[str, Path], as_of: date, prior_psi: Path
) -> dict[str, Any]:
    start = date(2024, 1, 1)

    def normal_sku(raw: Any, registry: Any, scope: str) -> str:
        code = text(raw).upper()
        # Legacy aliases are also in the governed registry.  The manual registry
        # receives the raw text and source scope so source-specific exact rules
        # (notably the INVENTORY mappings) cannot be skipped.
        return registry.map_sku(code, source_scope=scope, as_of=as_of)

    failures: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {
        "as_of": as_of.isoformat(),
        "checks": {},
        "warnings": warnings,
    }

    if payload.get("as_of") != as_of.isoformat():
        failures.append(
            f"payload as_of {payload.get('as_of')!r} is not {as_of.isoformat()}"
        )
    source_paths = sources
    if payload.get("sources") != {name: str(path) for name, path in sources.items()}:
        failures.append("payload source provenance does not match supplied sources")
    mandatory = {
        "CRM Sales Order",
        "Product Master",
        "Revenue",
        "Inventory",
        "Purchase/PO",
        "Target",
        "Manual Check",
    }
    if set(source_paths) != mandatory:
        failures.append(f"source keys mismatch: {sorted(source_paths)}")
    hashes: dict[str, str] = {}
    for name in sorted(mandatory):
        path = source_paths.get(name)
        if path is None or not path.is_file():
            failures.append(f"source missing: {name} => {path}")
            continue
        hashes[name] = digest(path)
        claimed = (payload.get("source_hashes") or {}).get(name)
        if claimed != hashes[name]:
            failures.append(f"SHA-256 mismatch for {name}")
    evidence["source_hashes"] = hashes

    if failures:
        raise ValidationFailure("\n".join(failures))
    registry = load_manual_check(source_paths["Manual Check"])
    approved_order_exclusions = {
        rule.order_id
        for rule in registry.order_exclusions
        if rule.is_active(as_of)
        and rule.action == "EXCLUDE ORDER FROM PSI"
        and rule.disposition == "PERMANENT / DONE"
    }
    approved_preorder_exclusions = {
        (rule.order_id, rule.canonical_sku)
        for rule in registry.preorder_exclusions
        if rule.is_active(as_of)
        and rule.action == "EXCLUDE FROM PREORDER"
        and rule.disposition == "PERMANENT / DONE"
    }
    duplicate_preorders = [
        key
        for key, count in Counter(
            (rule.order_id, rule.canonical_sku)
            for rule in registry.preorder_exclusions
            if rule.is_active(as_of)
            and rule.action == "EXCLUDE FROM PREORDER"
            and rule.disposition == "PERMANENT / DONE"
        ).items()
        if count > 1
    ]
    if duplicate_preorders:
        warnings.append(
            f"Manual Check contains {len(duplicate_preorders)} duplicate active preorder exclusion identities; semantic set applied once."
        )
    evidence["manual"] = {
        **registry.summary(as_of),
        "active_order_exclusions": len(approved_order_exclusions),
        "active_preorder_exclusion_identities": len(approved_preorder_exclusions),
        "duplicate_preorder_identities": len(duplicate_preorders),
    }

    # Product Master: source-scoped canonical product identity.
    product_header, product_source = read_sheet(
        source_paths["Product Master"], "Danh sách", 1
    )
    product_idx = headers(product_header)
    products: dict[str, dict[str, str]] = {}
    for row in product_source:
        code = normal_sku(
            field(row, product_idx, "Mã hàng hóa", "Mã hàng", "Product ID"),
            registry,
            "PRODUCT MASTER",
        )
        if not code:
            continue
        products[code] = {
            "name": text(
                field(row, product_idx, "Tên hàng hóa", "Tên hàng", "Product name")
            ),
            "brand": text(field(row, product_idx, "Nguồn gốc")),
            "category": text(
                field(row, product_idx, "Category", "Nhóm hàng hóa", "Nhóm hàng")
            ),
            "subcategory": text(
                field(row, product_idx, "Sub Category", "Sub-category", "Nhóm con")
            ),
            "brand_code": text(field(row, product_idx, "Mã hãng", "Brand Code")),
            "supplier": text(field(row, product_idx, "Nhà cung cấp", "Supplier")),
        }
    evidence["checks"]["product_master"] = {
        "source_rows": len(product_source),
        "unique_canonical_skus": len(products),
    }

    # CRM Final and product lines.  Product lines are required at grain (order, SKU).
    crm_header, crm_source = read_sheet(source_paths["CRM Sales Order"], "Danh sách", 1)
    crm_idx = headers(crm_header)
    crm_orders: dict[str, dict[str, Any]] = {}
    all_crm: dict[str, dict[str, str]] = {}
    for row in crm_source:
        order_id = text(field(row, crm_idx, "Số đơn hàng", "Số đơn hàng")).upper()
        approved = date_value(field(row, crm_idx, "Ngày duyệt"))
        approval_status = norm(field(row, crm_idx, "Trạng thái phê duyệt"))
        state = norm(field(row, crm_idx, "Tình trạng"))
        if order_id.startswith("DH-"):
            all_crm[order_id] = {
                "approved": approved.isoformat() if approved else "",
                "status": text(field(row, crm_idx, "Trạng thái phê duyệt")),
                "state": text(field(row, crm_idx, "Tình trạng")),
            }
        if (
            not order_id.startswith("DH-")
            or approved is None
            or not start <= approved <= as_of
        ):
            continue
        if (
            approval_status != norm("Đã duyệt")
            or "huy" in state
            or "cancel" in state
            or order_id in approved_order_exclusions
        ):
            continue
        crm_orders[order_id] = {
            "approval_date": approved.isoformat(),
            "customer": text(field(row, crm_idx, "Khách hàng")),
            "customer_code": text(field(row, crm_idx, "Mã khách hàng")),
            "order_value": number(field(row, crm_idx, "Giá trị đơn hàng")),
            "invoiced_value": number(field(row, crm_idx, "Giá trị đã xuất hóa đơn")),
            "state": text(field(row, crm_idx, "Tình trạng")),
            "approval_status": text(field(row, crm_idx, "Trạng thái phê duyệt")),
            "delivery_status": text(field(row, crm_idx, "Tình trạng giao hàng")),
            "payment_status": text(field(row, crm_idx, "Tình trạng thanh toán")),
        }
    crm_product_header, crm_product_source = read_sheet(
        source_paths["CRM Sales Order"], "Bảng hàng hóa", 1
    )
    crm_product_idx = headers(crm_product_header)
    crm_lines: dict[tuple[str, str], dict[str, Any]] = {}
    for row in crm_product_source:
        order_id = text(
            field(row, crm_product_idx, "Số đơn hàng", "Số đơn hàng")
        ).upper()
        if order_id not in crm_orders:
            continue
        raw_sku = text(
            field(row, crm_product_idx, "Mã hàng hóa", "Mã hàng hóa", "Mã hàng")
        )
        code = normal_sku(raw_sku, registry, "CRM")
        if not code:
            continue
        key = (order_id, code)
        entry = crm_lines.setdefault(
            key,
            {
                "qty": 0.0,
                "value": 0.0,
                "description": text(field(row, crm_product_idx, "Diễn giải", "Mô tả")),
            },
        )
        entry["qty"] += number(field(row, crm_product_idx, "Số lượng"))
        entry["value"] += number(
            field(row, crm_product_idx, "Thành tiền sau CK", "Tổng tiền")
        )
    evidence["checks"]["crm"] = {
        "orders": len(crm_orders),
        "product_keys": len(crm_lines),
        "source_order_rows": len(crm_source),
        "source_product_rows": len(crm_product_source),
    }

    # Revenue source and net formula.  Each payload row is a direct official ledger row.
    rev_header, rev_source = read_sheet(
        source_paths["Revenue"], "SỔ CHI TIẾT BÁN HÀNG", 4
    )
    rev_idx = headers(rev_header)
    revenue_expected: list[tuple[str, str, float, float, float, str]] = []
    revenue_by_key: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    revenue_by_sku: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    raw_revenue_missing_sku: list[str] = []
    for row_number, row in enumerate(rev_source, start=5):
        posting = date_value(field(row, rev_idx, "Ngày hạch toán"))
        if posting is None or not start <= posting <= as_of:
            continue
        debit, credit = (
            text(field(row, rev_idx, "TK Nợ")),
            text(field(row, rev_idx, "TK Có")),
        )
        if not {debit, credit}.intersection({"5111", "5112", "5113"}):
            continue
        raw_sku = text(field(row, rev_idx, "Mã hàng"))
        code = normal_sku(raw_sku, registry, "REVENUE")
        order_id = text(field(row, rev_idx, "Đơn hàng")).upper()
        if order_id in approved_order_exclusions:
            continue
        if not code:
            raw_revenue_missing_sku.append(f"ledger row {row_number}")
            continue
        qty = number(field(row, rev_idx, "Tổng số lượng bán"))
        net = (
            number(field(row, rev_idx, "Doanh số bán"))
            - number(field(row, rev_idx, "Chiết khấu"))
            - number(field(row, rev_idx, "Giá trị trả lại"))
            - number(field(row, rev_idx, "Giá trị giảm giá"))
        )
        cogs = number(field(row, rev_idx, "Giá vốn"))
        revenue_expected.append((posting.isoformat(), code, qty, net, cogs, order_id))
        revenue_by_key[(order_id, code)][0] += qty
        revenue_by_key[(order_id, code)][1] += net
        revenue_by_sku[code][0] += qty
        revenue_by_sku[code][1] += net
        revenue_by_sku[code][2] += cogs
    revenue_rows = payload_rows(payload, "revenue_rows", 18, failures)
    if len(revenue_rows) != len(revenue_expected):
        failures.append(
            f"Revenue row count: source {len(revenue_expected)}, payload {len(revenue_rows)}"
        )
    expected_revenue_tuple = Counter(revenue_expected)
    actual_revenue_tuple = Counter(
        (
            text(row[1]),
            text(row[2]),
            number(row[8]),
            number(row[9]),
            number(row[10]),
            text(row[11]),
        )
        for row in revenue_rows
    )
    if expected_revenue_tuple != actual_revenue_tuple:
        failures.append("Revenue direct-row grain/formula reconciliation failed")
    evidence["checks"]["revenue"] = {
        "rows": len(revenue_expected),
        "quantity": sum(row[2] for row in revenue_expected),
        "net_revenue": sum(row[3] for row in revenue_expected),
        "cogs": sum(row[4] for row in revenue_expected),
        "blank_sku_source_rows": len(raw_revenue_missing_sku),
    }

    # Inventory: preserve the historical warehouse-level output.  Exclude named
    # warehouses, map in INVENTORY scope, retain only raw rows with positive closing
    # quantity, then independently aggregate those retained rows for PSI by Product.
    # Row 4 has the merged semantic headings; row 5 is only quantity/value
    # sub-headings, and data begins at row 6.
    inv_header, inv_source = read_sheet(
        source_paths["Inventory"], "TỔNG HỢP TỒN KHO", 4
    )
    inv_idx = headers(inv_header)
    excluded_warehouses = {
        norm(name)
        for name in [
            "Kho Bình Phú Hàng Lỗi (Kho ảo)",
            "Kho Bình Phú (Kho lỗi)",
            "Kho Chị Kathy",
            "Kho chưa xuất hóa đơn",
        ]
    }
    inventory_expected: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    inventory_expected_rows: list[tuple[str, float, float, str]] = []
    inventory_raw: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    inventory_raw_missing_sku: list[str] = []
    for source_no, row in enumerate(inv_source, start=6):
        warehouse_name = text(field(row, inv_idx, "Tên kho")) or text(
            row[0] if len(row) > 0 else ""
        )
        warehouse = text(field(row, inv_idx, "Mã kho")) or text(
            row[1] if len(row) > 1 else ""
        )
        raw_sku = text(
            field(row, inv_idx, "Mã hàng", "Mã hàng hóa", "PRODUCT ID")
        ) or text(row[2] if len(row) > 2 else "")
        if norm(warehouse_name) in excluded_warehouses:
            continue
        code = normal_sku(raw_sku, registry, "INVENTORY")
        if not code:
            inventory_raw_missing_sku.append(f"inventory row {source_no}")
            continue
        # The official inventory export has several repeated "Số lượng" and
        # "Giá trị" headers.  Its closing balance fields are unambiguously the
        # final positional pair L/M (zero-based 11/12), never the first pair.
        qty = number(row[11] if len(row) > 11 else None)
        value = number(row[12] if len(row) > 12 else None)
        if qty <= 0.001:
            continue
        warehouse = text(row[1] if len(row) > 1 else None)
        inventory_expected[code][0] += qty
        inventory_expected[code][1] += value
        inventory_expected_rows.append((code, qty, value, warehouse))
    inv_rows = payload_rows(payload, "inventory_rows", 11, failures)
    for row in inv_rows:
        code = text(row[2])
        inventory_raw[code][0] += number(row[8])
        inventory_raw[code][1] += number(row[9])
        if code not in inventory_expected:
            failures.append(
                f"Inventory payload contains SKU without positive raw eligible stock: {code}"
            )
    if set(inventory_raw) != set(inventory_expected):
        missing = sorted(set(inventory_expected) - set(inventory_raw))[:10]
        extra = sorted(set(inventory_raw) - set(inventory_expected))[:10]
        failures.append(f"Inventory SKU set mismatch; missing={missing}, extra={extra}")
    for code, values in inventory_expected.items():
        close(values[0], inventory_raw[code][0], f"Inventory quantity {code}", failures)
        close(values[1], inventory_raw[code][1], f"Inventory value {code}", failures)
    expected_inventory_counter = Counter(inventory_expected_rows)
    payload_inventory_counter = Counter(
        (text(row[2]), number(row[8]), number(row[9]), text(row[10]))
        for row in inv_rows
    )
    if expected_inventory_counter != payload_inventory_counter:
        missing = list(
            (expected_inventory_counter - payload_inventory_counter).elements()
        )[:5]
        extra = list(
            (payload_inventory_counter - expected_inventory_counter).elements()
        )[:5]
        failures.append(
            f"Inventory raw warehouse rows mismatch; missing={missing}, extra={extra}"
        )
    evidence["checks"]["inventory"] = {
        "eligible_canonical_skus": len(inventory_expected),
        "payload_rows": len(inv_rows),
        "quantity": sum(v[0] for v in inventory_expected.values()),
        "value": sum(v[1] for v in inventory_expected.values()),
        "blank_sku_source_rows": len(inventory_raw_missing_sku),
    }

    # Purchase/PO: all blank SKU records must be excluded from PO balances and
    # visible as both an exclusion row and a deduplicated data-gap identity.
    purchase_book = load_workbook(
        source_paths["Purchase/PO"], read_only=True, data_only=True
    )
    try:
        purchase_sheet = purchase_book["LDL"]
        purchase_source = list(purchase_sheet.iter_rows(min_row=5, values_only=True))
    finally:
        purchase_book.close()
    purchase_expected: list[tuple[str, str, str, str, float]] = []
    blank_po_source: list[tuple[str, str]] = []
    purchase_full_expected: list[list[Any]] = []
    for source_row, row in enumerate(purchase_source, start=5):
        if not any(item not in (None, "", 0) for item in row[:80]):
            continue
        raw_sku = text(row[18] if len(row) > 18 else None)
        code = normal_sku(raw_sku, registry, "PURCHASE/PO")
        product_name = text(row[19] if len(row) > 19 else None)
        if not code and not product_name:
            continue
        status = text(row[1] if len(row) > 1 else None)
        po, order_id = (
            text(row[4] if len(row) > 4 else None),
            text(row[8] if len(row) > 8 else None),
        )
        qty = number(row[20] if len(row) > 20 else None)
        if not code:
            blank_po_source.append(
                (po or order_id or f"row {source_row}", product_name)
            )
            continue
        purchase_expected.append((status, po, order_id, code, qty))

        def source_value(position: int) -> Any:
            return row[position] if position < len(row) else None

        def source_date(position: int) -> Any:
            raw = source_value(position)
            if isinstance(raw, datetime):
                return raw.date().isoformat()
            return raw.isoformat() if isinstance(raw, date) else raw

        purchase_full_expected.append(
            [
                len(purchase_full_expected) + 1,
                status,
                text(source_value(2)),
                po,
                order_id,
                source_date(5),
                text(source_value(6)),
                text(source_value(7)),
                code,
                products.get(code, {}).get("name") or product_name,
                qty,
                number(source_value(77)),
                text(source_value(21)),
                number(source_value(27)),  # AB: net contract value excluding F.O.C
                source_date(43),  # AR: ETA, not BC stock-in date
            ]
        )

    purchase_rows = payload_rows(payload, "purchase_rows", 15, failures)
    if purchase_rows != purchase_full_expected:
        failures.append("Purchase/PO full-row reconciliation failed")
    actual_purchase = Counter(
        (text(row[1]), text(row[3]), text(row[4]), text(row[8]), number(row[10]))
        for row in purchase_rows
    )
    if Counter(purchase_expected) != actual_purchase:
        failures.append("Purchase/PO row and canonical SKU reconciliation failed")
    po_excluded_rows = payload_rows(payload, "po_excluded_rows", 4, failures)
    actual_po_excluded = Counter(
        (text(row[2]), text(row[3])) for row in po_excluded_rows
    )
    expected_po_excluded = Counter(
        (name, "Blank SKU in approved PO source") for _, name in blank_po_source
    )
    if actual_po_excluded != expected_po_excluded:
        failures.append(
            "PO excluded rows do not exactly reconcile to blank-SKU source records"
        )
    evidence["checks"]["purchase"] = {
        "purchase_rows": len(purchase_expected),
        "blank_sku_excluded_rows": len(blank_po_source),
        "unique_blank_sku_gap_keys": len({key for key, _ in blank_po_source}),
    }

    # Payload CRM sheets must agree with independent source filtering and aggregation.
    crm_final_rows = payload_rows(payload, "crm_final_rows", 10, failures)
    crm_product_rows = payload_rows(payload, "crm_product_rows", 6, failures)
    if len(crm_final_rows) != len(crm_orders) or {
        text(row[0]) for row in crm_final_rows
    } != set(crm_orders):
        failures.append("CRM Final order filtering mismatch")
    actual_crm_lines = {
        (text(row[0]), text(row[1])): [number(row[3]), number(row[4])]
        for row in crm_product_rows
    }
    if set(actual_crm_lines) != set(crm_lines):
        failures.append("Final CRM Products key set mismatch")
    for key, expected in crm_lines.items():
        actual = actual_crm_lines.get(key, [0.0, 0.0])
        close(expected["qty"], actual[0], f"CRM quantity {key}", failures)
        close(expected["value"], actual[1], f"CRM net value {key}", failures)

    # Preorder math/review.  Open values must stay a mismatch, not an open line,
    # where the open quantity is zero.  Exclusions are permanent by (order, SKU).
    expected_preorders: dict[tuple[str, str], tuple[float, float]] = {}
    expected_excluded: dict[tuple[str, str], tuple[float, float]] = {}
    revenue_exceeds: set[tuple[str, str]] = set()
    zero_qty_open_value: set[tuple[str, str]] = set()
    for key, crm_line in crm_lines.items():
        sold_qty, sold_value = revenue_by_key[key]
        open_qty, open_value = (
            crm_line["qty"] - sold_qty,
            crm_line["value"] - sold_value,
        )
        if open_qty < -0.001 or open_value < -0.5:
            revenue_exceeds.add(key)
        if open_qty <= 0.001:
            if open_value > 0.5:
                zero_qty_open_value.add(key)
            continue
        destination = (
            expected_excluded
            if key in approved_preorder_exclusions
            else expected_preorders
        )
        destination[key] = (max(0.0, open_qty), max(0.0, open_value))
    pre_rows = payload_rows(payload, "preorder_rows", 18, failures)
    excluded_rows = payload_rows(payload, "preorder_excluded_rows", 18, failures)
    actual_pre = {
        (text(row[12]), text(row[2])): (number(row[8]), number(row[9]))
        for row in pre_rows
    }
    actual_excluded = {
        (text(row[12]), text(row[2])): (number(row[8]), number(row[9]))
        for row in excluded_rows
    }
    if len(actual_pre) != len(pre_rows):
        failures.append("Pre-order output has duplicate Order ID + canonical SKU")
    if len(actual_excluded) != len(excluded_rows):
        failures.append(
            "Preorder excluded output has duplicate Order ID + canonical SKU"
        )
    if set(actual_pre) != set(expected_preorders):
        failures.append(
            f"Open pre-order key set mismatch (expected {len(expected_preorders)}, actual {len(actual_pre)})"
        )
    if set(actual_excluded) != set(expected_excluded):
        failures.append(
            f"Excluded pre-order key set mismatch (expected {len(expected_excluded)}, actual {len(actual_excluded)})"
        )
    for key, expected in expected_preorders.items():
        actual = actual_pre.get(key, (0.0, 0.0))
        close(expected[0], actual[0], f"Open preorder qty {key}", failures)
        close(expected[1], actual[1], f"Open preorder value {key}", failures)
    for key, expected in expected_excluded.items():
        actual = actual_excluded.get(key, (0.0, 0.0))
        close(expected[0], actual[0], f"Excluded preorder qty {key}", failures)
        close(expected[1], actual[1], f"Excluded preorder value {key}", failures)
    evidence["checks"]["preorders"] = {
        "open_keys": len(expected_preorders),
        "excluded_keys": len(expected_excluded),
        "revenue_exceeds_crm_keys": len(revenue_exceeds),
        "zero_qty_open_value_keys": len(zero_qty_open_value),
    }

    # No approved order-level exclusion may leak to business sheets.
    business_order_ids = {
        *[text(row[11]) for row in revenue_rows],
        *[text(row[0]) for row in crm_final_rows],
        *[text(row[0]) for row in crm_product_rows],
        *[text(row[12]) for row in pre_rows],
        *[text(row[12]) for row in excluded_rows],
    }
    leaked_orders = sorted(approved_order_exclusions & business_order_ids)
    if leaked_orders:
        failures.append(
            f"Approved order exclusions leaked into business output: {leaked_orders}"
        )

    # Mismatch rows: unique stable key, correct NEW membership vs exact prior PSI.
    mismatch_rows = payload_rows(payload, "mismatch_rows", 6, failures)
    mismatch_keys = [stable_mismatch_key(row) for row in mismatch_rows]
    if len(set(mismatch_keys)) != len(mismatch_keys):
        failures.append("Mismatch stable keys are not unique")
    prior_path = prior_psi
    if text(payload.get("prior_psi_final")) != str(prior_path):
        failures.append("payload prior PSI provenance does not match supplied baseline")
    if not prior_path.is_file():
        failures.append(f"prior PSI baseline missing: {prior_path}")
        prior_keys: set[tuple[str, str, str]] = set()
    else:
        prior_keys = load_prior_keys(prior_path)
        prior_sha = digest(prior_path)
        claimed_prior_sha = text(payload.get("prior_psi_sha256"))
        if claimed_prior_sha != prior_sha:
            failures.append("Prior PSI SHA-256 mismatch")
    expected_new = set(mismatch_keys) - prior_keys
    actual_new_raw = payload.get("new_mismatch_keys", [])
    actual_new = {
        tuple(text(part) for part in row)
        for row in actual_new_raw
        if isinstance(row, list) and len(row) == 3
    }
    if actual_new != expected_new:
        failures.append(
            f"NEW mismatch membership mismatch: expected {len(expected_new)}, payload {len(actual_new)}"
        )
    expected_mismatch_keys: set[tuple[str, str, str]] = set()
    for key in revenue_exceeds:
        expected_mismatch_keys.add(
            (
                "CRM / Revenue",
                f"{key[0]} / {key[1]}",
                "Revenue exceeds approved CRM line",
            )
        )
    for key in zero_qty_open_value:
        expected_mismatch_keys.add(
            (
                "CRM / Revenue",
                f"{key[0]} / {key[1]}",
                "CRM exceeds Revenue with no open quantity",
            )
        )
    for _, code, _, net, cost, order_id in revenue_expected:
        if cost > net + 0.5:
            expected_mismatch_keys.add(
                ("Revenue", f"{order_id} / {code}", "COGS > NET REV SOLD")
            )
        if code not in products:
            expected_mismatch_keys.add(
                ("Revenue", f"{order_id} / {code}", "SKU not found in Product Master")
            )
    for code in inventory_expected:
        if code not in products:
            expected_mismatch_keys.add(
                ("Inventory", code, "SKU not found in Product Master")
            )
    for order_id, code in {*expected_preorders, *expected_excluded}:
        if code not in products:
            expected_mismatch_keys.add(
                (
                    "CRM Final Products",
                    f"{order_id} / {code}",
                    "SKU not found in Product Master",
                )
            )
    for order_id, code in revenue_by_key:
        if (
            not order_id.startswith("DH-")
            or order_id in crm_orders
            or order_id in approved_order_exclusions
        ):
            continue
        raw = all_crm.get(order_id)
        if raw is not None and raw["approved"] and raw["approved"] < start.isoformat():
            continue
        if raw is None:
            issue = "Revenue order missing CRM source"
        elif norm(raw["status"]) != norm("Đã duyệt"):
            issue = "Revenue order excluded from CRM Final by approval status"
        else:
            issue = "Revenue order excluded from CRM Final"
        expected_mismatch_keys.add(("Revenue / CRM", f"{order_id} / {code}", issue))
    expected_mismatch_keys = {
        (text(source), text(key), text(issue))
        for source, key, issue in expected_mismatch_keys
    }
    if set(mismatch_keys) != expected_mismatch_keys:
        evidence["mismatch_identity_difference"] = {
            "missing": dict(
                Counter(
                    f"{source}: {issue}"
                    for source, _, issue in expected_mismatch_keys - set(mismatch_keys)
                )
            ),
            "extra": dict(
                Counter(
                    f"{source}: {issue}"
                    for source, _, issue in set(mismatch_keys) - expected_mismatch_keys
                )
            ),
        }
        failures.append(
            "Mismatch identities do not reconcile to independently recomputed source issues"
        )
    evidence["checks"]["mismatches"] = {
        "rows": len(mismatch_rows),
        "new_rows": len(expected_new),
        "prior_rows": len(prior_keys),
    }

    # Data gap rows must at least report each nonblank source/payload SKU that
    # cannot be joined to Product Master and every blank official SKU retained.
    gap_rows = payload_rows(payload, "data_gap_rows", 4, failures)
    actual_gap_keys = {(text(row[0]), text(row[1]), text(row[2])) for row in gap_rows}
    expected_missing_product = set()
    for source, rows, sku_position, key_position in [
        ("Revenue", revenue_rows, 2, 11),
        ("Inventory", inv_rows, 2, 2),
        ("CRM Final Products", crm_product_rows, 1, 0),
    ]:
        for row in rows:
            code = text(row[sku_position])
            if code and code not in products:
                expected_missing_product.add(
                    (
                        source,
                        f"{text(row[key_position])} / {code}"
                        if source != "Inventory"
                        else code,
                    )
                )
    for source, key in expected_missing_product:
        if not any(
            gap_source == source and gap_key == key and "SKU not found" in issue
            for gap_source, gap_key, issue in actual_gap_keys
        ):
            failures.append(
                f"Data gaps omits missing Product Master case: {source} {key}"
            )
    for key, _ in set(blank_po_source):
        if not any(
            gap_source == "Purchase/PO"
            and gap_key == key
            and issue == "Blank SKU in approved PO source"
            for gap_source, gap_key, issue in actual_gap_keys
        ):
            failures.append(f"Data gaps omits blank approved PO SKU: {key}")
    evidence["checks"]["data_gaps"] = {
        "rows": len(gap_rows),
        "missing_product_cases": len(expected_missing_product),
        "blank_revenue_sku_source_rows": len(raw_revenue_missing_sku),
        "blank_inventory_sku_source_rows": len(inventory_raw_missing_sku),
    }

    # PSI product rows must aggregate every supplied business stream exactly.
    psi_rows = payload_rows(payload, "psi_product_rows", 15, failures)
    psi_by_sku = {text(row[0]): row for row in psi_rows}
    if len(psi_by_sku) != len(psi_rows):
        failures.append("PSI by Product has duplicate canonical SKU")
    preorder_by_sku: dict[str, float] = defaultdict(float)
    for row in pre_rows:
        preorder_by_sku[text(row[2])] += number(row[8])
    po_by_sku: dict[str, float] = defaultdict(float)
    for row in purchase_rows:
        if norm(row[1]) != norm("Done"):
            po_by_sku[text(row[8])] += number(row[10])
    expected_active = (
        set(revenue_by_sku)
        | set(inventory_expected)
        | set(preorder_by_sku)
        | set(po_by_sku)
    )
    if set(psi_by_sku) != expected_active:
        failures.append(
            f"PSI by Product active SKU set mismatch: expected {len(expected_active)}, actual {len(psi_by_sku)}"
        )
    for code in expected_active:
        row = psi_by_sku.get(code)
        if row is None:
            continue
        product = products.get(code, {})
        expected_status = "MAPPED" if code in products else "MISSING PRODUCT"
        if text(row[2]) != product.get("brand", ""):
            failures.append(
                f"PSI Brand {code}: expected {product.get('brand', '')!r}, payload {text(row[2])!r}"
            )
        if text(row[3]) != product.get("category", "") or text(row[4]) != product.get(
            "subcategory", ""
        ):
            failures.append(f"PSI category mapping mismatch for {code}")
        if text(row[5]) != expected_status:
            failures.append(f"PSI code status mismatch for {code}")
        sold = revenue_by_sku[code]
        inv = inventory_expected.get(code, [0.0, 0.0])
        close(sold[0], number(row[6]), f"PSI sold qty {code}", failures)
        close(sold[1], number(row[7]), f"PSI net revenue {code}", failures)
        close(sold[2], number(row[8]), f"PSI COGS {code}", failures)
        close(inv[0], number(row[11]), f"PSI inventory qty {code}", failures)
        close(inv[1], number(row[12]), f"PSI inventory value {code}", failures)
        close(
            preorder_by_sku[code], number(row[13]), f"PSI preorder qty {code}", failures
        )
        close(po_by_sku[code], number(row[14]), f"PSI PO qty {code}", failures)
    evidence["checks"]["psi_by_product"] = {
        "rows": len(psi_rows),
        "active_skus": len(expected_active),
    }

    brand_rows = payload_rows(payload, "brand_rows", 2, failures)
    expected_brand_rows = {
        (details["brand"], details["brand_code"])
        for details in products.values()
        if details["brand"] or details["brand_code"]
    }
    actual_brand_rows = {(text(row[0]), text(row[1])) for row in brand_rows}
    if actual_brand_rows != expected_brand_rows:
        failures.append(
            f"Brand lookup mismatch: expected {len(expected_brand_rows)} pairs, payload {len(actual_brand_rows)}"
        )
    evidence["checks"]["brand"] = {
        "rows": len(brand_rows),
        "pairs": len(expected_brand_rows),
    }

    # Independently reconcile supporting relations that the historical validator
    # did not inspect, so every relation consumed by the online workbook is gated.
    category_expected = sorted(
        {
            (p["category"], p["subcategory"])
            for p in products.values()
            if p["category"] or p["subcategory"]
        }
    )
    if payload.get("category_rows") != [list(row) for row in category_expected]:
        failures.append("Category lookup reconciliation failed")
    target_book = load_workbook(source_paths["Target"], read_only=True, data_only=True)
    try:
        target_expected = [
            [
                v.date().isoformat()
                if isinstance(v, datetime)
                else v.isoformat()
                if isinstance(v, date)
                else v
                for v in row
            ]
            for row in target_book["Target"].iter_rows(values_only=True)
            if any(v not in (None, "") for v in row)
        ]
    finally:
        target_book.close()
    if payload.get("target_rows") != target_expected:
        failures.append("Target source rows reconciliation failed")
    if payload.get("data_gaps_rows") != gap_rows:
        failures.append(
            "Data gap compatibility relation differs from canonical relation"
        )
    expected_crm_rows = [
        [
            key,
            rec["customer"],
            rec["customer_code"],
            rec["approval_date"],
            rec["order_value"],
            rec["invoiced_value"],
            rec["state"],
            rec["approval_status"],
            rec["delivery_status"],
            rec["payment_status"],
        ]
        for key, rec in sorted(crm_orders.items())
    ]
    if crm_final_rows != expected_crm_rows:
        failures.append("CRM Final full-row reconciliation failed")
    expected_crm_products = [
        [
            order_id,
            code,
            products.get(code, {}).get("name") or rec["description"],
            rec["qty"],
            rec["value"],
            crm_orders[order_id]["approval_date"],
        ]
        for (order_id, code), rec in sorted(crm_lines.items())
    ]
    if crm_product_rows != expected_crm_products:
        failures.append("Final CRM Products full-row reconciliation failed")
    if len(actual_crm_lines) != len(crm_product_rows):
        failures.append("Final CRM Products has duplicate Order ID + canonical SKU")
    for row in psi_rows:
        profit = number(row[7]) - number(row[8])
        close(profit, number(row[9]), f"PSI gross profit {text(row[0])}", failures)
        if abs(number(row[7])) > 0.005:
            close(
                profit / number(row[7]),
                number(row[10]),
                f"PSI gross margin {text(row[0])}",
                failures,
            )
        elif row[10] is not None:
            failures.append(
                f"PSI zero revenue gross margin must be blank: {text(row[0])}"
            )
    if payload.get("period_start") != start.isoformat():
        failures.append("PSI period_start mismatch")
    evidence["checks"]["supporting_relations"] = {
        "category_rows": len(category_expected),
        "target_rows": len(target_expected),
        "crm_full_rows": len(expected_crm_rows),
        "data_gap_alias": True,
    }

    summary = payload.get("summary") or {}
    for label, expected, actual in [
        (
            "summary revenue rows",
            len(revenue_rows),
            number(summary.get("revenue_rows")),
        ),
        (
            "summary net revenue",
            sum(row[3] for row in revenue_expected),
            number(summary.get("net_revenue")),
        ),
        (
            "summary cogs",
            sum(row[4] for row in revenue_expected),
            number(summary.get("cogs")),
        ),
        (
            "summary inventory qty",
            sum(v[0] for v in inventory_expected.values()),
            number(summary.get("inventory_qty")),
        ),
        (
            "summary inventory value",
            sum(v[1] for v in inventory_expected.values()),
            number(summary.get("inventory_value")),
        ),
        (
            "summary CRM orders",
            len(crm_orders),
            number(summary.get("crm_final_orders")),
        ),
        (
            "summary CRM product keys",
            len(crm_lines),
            number(summary.get("crm_final_products")),
        ),
        ("summary preorders", len(pre_rows), number(summary.get("preorder_rows"))),
        (
            "summary excluded preorders",
            len(excluded_rows),
            number(summary.get("preorder_excluded_rows")),
        ),
        (
            "summary mismatches",
            len(mismatch_rows),
            number(summary.get("mismatch_rows")),
        ),
        (
            "summary new mismatches",
            len(expected_new),
            number(summary.get("new_mismatch_rows")),
        ),
    ]:
        close(float(expected), float(actual), label, failures)

    gates = payload.get("gates")
    if not isinstance(gates, list) or not gates:
        failures.append("payload contains no release gates")
    elif any(
        text(gate.get("status")).upper() == "FAIL"
        for gate in gates
        if isinstance(gate, dict)
    ):
        failures.append("payload release gates include a FAIL result")
    elif any(
        text(gate.get("status")).upper() not in {"PASS", "WARN"}
        for gate in gates
        if isinstance(gate, dict)
    ):
        failures.append("payload release gates include an invalid status")
    required_gates = {
        "source_files_readable",
        "manual_check_validator_pass",
        "prior_psi_baseline_found",
        "revenue_quantity_header_exact",
        "revenue_quantity_total_matches_rows",
        "inventory_raw_positive_only",
        "preorder_exclusion_no_leak",
        "preorder_excluded_rows_authorized",
        "preorder_excluded_output_unique",
        "preorder_registry_set_semantics",
        "order_exclusion_no_leak",
        "mismatch_identity_unique",
    }
    gates_by_name = {
        text(g["check"]): g for g in gates if isinstance(g, dict) and "check" in g
    }
    if not required_gates.issubset(gates_by_name):
        failures.append("Payload omits required release gates")
    for name in required_gates & gates_by_name.keys():
        gate = gates_by_name[name]
        if (
            gate.get("expected") is not True
            or gate.get("actual") is not True
            or gate.get("status") != "PASS"
        ):
            failures.append(
                f"Required release gate is not a passing true observable: {name}"
            )
    if payload.get("gate_results") != dict.fromkeys(required_gates, True):
        failures.append("Release gate result observables mismatch")
    evidence["checks"]["payload_gates"] = {
        "count": len(gates) if isinstance(gates, list) else 0
    }

    evidence["result"] = "PASS" if not failures else "FAIL"
    evidence["failure_count"] = len(failures)
    evidence["failures"] = failures
    evidence["status"] = evidence["result"]
    return evidence
