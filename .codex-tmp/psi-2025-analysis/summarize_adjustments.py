from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import openpyxl


PSI_PATH = Path("/Users/iant1359/Downloads/PSI 23.07 _KT check.xlsx")
MISA_PATH = Path(
    "/Users/iant1359/Downloads/mismatch/So_chi_tiet_ban_hang 22.07.xlsx"
)


def emit(label: str, value: object) -> None:
    print(f"{label}\t{json.dumps(value, ensure_ascii=False, default=str)}")


def date_key(value: object) -> str:
    return str(value)[:10] if value not in (None, "") else ""


def number(value: object) -> float:
    return float(value or 0) if isinstance(value, (int, float)) else 0.0


psi = openpyxl.load_workbook(
    PSI_PATH, data_only=True, read_only=True, keep_links=False
)
revenue = psi["Revenue final"]

final_negative: dict[tuple[str, str, float], list[dict[str, object]]] = defaultdict(
    list
)
for row_number, row in enumerate(
    revenue.iter_rows(min_row=7, max_col=17, values_only=True), start=7
):
    quantity = number(row[8])
    if quantity >= 0:
        continue
    key = (date_key(row[1]), str(row[2] or "").strip(), abs(quantity))
    final_negative[key].append(
        {
            "row": row_number,
            "net_rev_sold": number(row[9]),
            "sale_order": str(row[11] or "").strip(),
            "accounting_expected": row[15],
            "accounting_variance": row[16],
        }
    )

misa = openpyxl.load_workbook(
    MISA_PATH, data_only=True, read_only=True, keep_links=False
)
misa_sheet = misa[misa.sheetnames[0]]

by_year = defaultdict(
    lambda: {
        "source_adjustment_rows": 0,
        "rows_with_negative_discount": 0,
        "rows_where_discount_changes_net": 0,
        "matched_final_rows": 0,
        "mismatched_final_rows": 0,
        "mismatch_total": 0.0,
        "unmatched_source_rows": 0,
        "documents": set(),
    }
)
details = []

for row_number, row in enumerate(
    misa_sheet.iter_rows(min_row=5, max_col=37, values_only=True), start=5
):
    returned_quantity = number(row[21])
    returned_value = number(row[22])
    if returned_quantity <= 0 and returned_value <= 0:
        continue

    year = date_key(row[0])[:4]
    if year not in {"2024", "2025", "2026"}:
        continue

    sales = number(row[16])
    discount = number(row[19])
    price_reduction = number(row[23])
    correct_net = sales - discount - returned_value - price_reduction
    key = (
        date_key(row[0]),
        str(row[10] or "").strip(),
        returned_quantity,
    )
    final_candidates = final_negative.get(key, [])

    summary = by_year[year]
    summary["source_adjustment_rows"] += 1
    summary["documents"].add(str(row[2] or ""))
    if discount < 0:
        summary["rows_with_negative_discount"] += 1
    if abs(discount) > 0.5 or abs(price_reduction) > 0.5 or abs(sales) > 0.5:
        summary["rows_where_discount_changes_net"] += 1

    if not final_candidates:
        summary["unmatched_source_rows"] += 1
        continue

    summary["matched_final_rows"] += 1
    final_row = final_candidates[0]
    delta = correct_net - number(final_row["net_rev_sold"])
    if abs(delta) > 1:
        summary["mismatched_final_rows"] += 1
        summary["mismatch_total"] += delta
        details.append(
            {
                "year": year,
                "source_row": row_number,
                "final_row": final_row["row"],
                "date": row[0],
                "document": row[2],
                "description": row[8],
                "sku": row[10],
                "sale_order": row[28],
                "sales": sales,
                "discount": discount,
                "returned_value": returned_value,
                "price_reduction": price_reduction,
                "correct_net": correct_net,
                "final_net": final_row["net_rev_sold"],
                "delta": delta,
            }
        )

serializable_summary = {}
for year, summary in sorted(by_year.items()):
    serializable_summary[year] = {
        **summary,
        "documents": sorted(summary["documents"]),
        "mismatch_total": round(summary["mismatch_total"]),
    }

emit("SUMMARY_BY_YEAR", serializable_summary)
emit("MISMATCH_DETAIL_COUNT", len(details))
for detail in details:
    emit("MISMATCH_DETAIL", detail)
