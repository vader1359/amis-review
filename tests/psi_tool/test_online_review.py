import hashlib
import io
from copy import deepcopy
from typing import Any

import pytest
from openpyxl import Workbook

from psi_tool._online_workbook_schema import SCHEMA
from psi_tool.online_review import analyze_report


def report(
    as_of: str = "2026-09-03", quantity: int = 3, revenue: int = 1
) -> dict[str, Any]:
    preorder = [None] * 18
    preorder[2], preorder[8], preorder[9], preorder[12] = (
        "SKU-A",
        quantity - revenue,
        (quantity - revenue) * 100,
        "DH-1",
    )
    ledger = [None] * 18
    ledger[2], ledger[8], ledger[9], ledger[10], ledger[11] = (
        "SKU-A",
        revenue,
        revenue * 100,
        revenue * 60,
        "DH-1",
    )
    return {
        "as_of": as_of,
        "crm_final_rows": [
            [
                "DH-1",
                "Customer",
                "C1",
                "2026-08-01",
                300,
                revenue * 100,
                "Done",
                "Đã duyệt",
                "Delivered",
                "Paid",
            ]
        ],
        "crm_product_rows": [
            ["DH-1", "SKU-A", "Product", quantity, quantity * 100, "2026-08-01"]
        ],
        "revenue_rows": [ledger],
        "preorder_rows": [preorder] if quantity > revenue else [],
        "preorder_excluded_rows": [],
        "mismatch_rows": [],
    }


def test_missing_baseline_is_unknown_not_new_and_input_unchanged() -> None:
    payload = report()
    saved = deepcopy(payload)
    review = analyze_report(payload)
    assert payload == saved
    assert review["baseline"]["status"] == "missing"
    assert review["changes"] == []
    assert review["preorder_checks"][0]["is_new"] is None
    assert review["summary"]["new_preorder_count"] is None


def test_completed_order_changes_are_included_without_suspicion() -> None:
    previous = report("2026-08-27", 1, 1)
    current = report(quantity=2, revenue=2)
    result = analyze_report(current, previous)
    change = result["changes"][0]
    assert change["order_id"] == "DH-1"
    assert "revenue_quantity" in change["changed_fields"]
    assert change["needs_attention"] is False
    assert result["preorder_checks"] == []


def test_split_revenue_lines_aggregate_and_reordering_does_not_make_changes() -> None:
    previous = report("2026-08-27")
    current = report()
    half = deepcopy(current["revenue_rows"][0])
    half[8:11] = [0.5, 50, 30]
    current["revenue_rows"] = [half, deepcopy(half)]
    assert analyze_report(current, previous)["changes"] == []


def test_new_preorder_reopened_line_math_mismatch_and_evidence() -> None:
    previous = report("2026-08-27", 1, 1)
    current = report()
    current["preorder_rows"][0][8] = 4
    current["mismatch_rows"] = [
        [
            "OPEN",
            "CRM / Revenue",
            "DH-1 / SKU-A",
            "Observed conflict",
            "Check invoice",
            "CRM=3; Revenue=1",
        ]
    ]
    current["new_mismatch_keys"] = [
        ["CRM / Revenue", "DH-1 / SKU-A", "Observed conflict"]
    ]
    result = analyze_report(current, previous)
    check = result["preorder_checks"][0]
    assert check["is_new"] is True
    assert check["verdict"] == "needs_review"
    assert len(check["reasons"]) == 2
    assert result["mismatches"][0]["is_new"] is True
    assert result["mismatches"][0]["evidence"] == "CRM=3; Revenue=1"
    assert "CRM=3; Revenue=1" not in result["mismatches"][0]["explanation"]


@pytest.mark.parametrize(
    ("issue", "meaning"),
    [
        ("COGS > NET REV SOLD", "Giá vốn cao hơn doanh thu thuần"),
        ("Revenue exceeds approved CRM line", "Số lượng hoặc giá trị"),
        ("CRM exceeds Revenue with no open quantity", "không còn số lượng"),
        ("SKU not found in Product Master", "chưa có trong danh mục"),
        ("Revenue order missing CRM source", "không xuất hiện trong file CRM"),
        (
            "Revenue order excluded from CRM Final by approval status",
            "không phải Đã duyệt",
        ),
        ("Revenue order excluded from CRM Final", "điều kiện lọc trạng thái"),
    ],
)
def test_vietnamese_explanations_preserve_separate_evidence(
    issue: str, meaning: str
) -> None:
    payload = report()
    payload["mismatch_rows"] = [
        [
            "OPEN",
            "Revenue",
            "DH-1 / SKU-A",
            issue,
            "Original action",
            "NET REV SOLD=0; COGS=100",
        ]
    ]
    mismatch = analyze_report(payload)["mismatches"][0]
    assert mismatch["issue"] == issue
    assert meaning in mismatch["explanation"]
    assert mismatch["evidence"] == "NET REV SOLD=0; COGS=100"
    assert mismatch["evidence"] not in mismatch["explanation"]
    assert mismatch["suggested_action"] != "Original action"
    assert mismatch["source_action"] == "Original action"


def test_removed_line_not_silently_omitted() -> None:
    current = report()
    current["crm_product_rows"] = []
    current["revenue_rows"] = []
    current["preorder_rows"] = []
    assert (
        analyze_report(current, report("2026-08-27"))["changes"][0]["kind"] == "removed"
    )


def test_wrong_or_future_baseline_rejected() -> None:
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        analyze_report(report(), prior_workbook=b"wrong")
    with pytest.raises(ValueError, match="NOT_EARLIER"):
        analyze_report(report(), report())
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        analyze_report(report(), report(), b"wrong")


def baseline_bytes(previous: dict[str, Any]) -> bytes:
    book = Workbook()
    book.remove(book.active)
    for schema in SCHEMA:
        sheet = book.create_sheet(schema["name"])
        sheet.append(
            [
                "PSI SUMMARY — 27.08.2026"
                if schema["name"] == "PSI Summary"
                else schema["title"]
            ]
        )
        sheet.append([])
        sheet.append(schema["headers"] or [])
        for row in previous.get(schema["key"], []):
            sheet.append(row)
    book["Checks"].append(["Test", None, None, "PASS"])
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def test_actual_selected_final_workbook_hash_and_header_validation() -> None:
    content = baseline_bytes(report("2026-08-27"))
    current = report()
    current.update(
        prior_psi_final="PSI_Final_27.08.2026.xlsx",
        prior_psi_sha256=hashlib.sha256(content).hexdigest(),
    )
    review = analyze_report(current, prior_workbook=content)
    assert review["baseline"]["source"] == "selected_final_workbook"
    assert review["changes"] == []
    current["prior_psi_final"] = "PSI_Draft.xlsx"
    with pytest.raises(ValueError, match="FINAL_REQUIRED"):
        analyze_report(current, prior_workbook=content)
