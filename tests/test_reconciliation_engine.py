import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(ROOT / "web"))
import server  # noqa: E402


IssueCell = str | int | float | None

EXPECTED_SHEETS = {
    "PSI Summary",
    "Mismatch",
    "Data gaps",
    "PO excluded",
    "PSI by Product",
    "Product detail",
    "Product final",
    "Purchase PO detail",
    "Purchase final",
    "Inventory source",
    "Inventory final",
    "Pre-order source",
    "Pre-orders final",
    "Revenue raw",
    "Revenue final",
    "CRM orders",
    "CRM items",
    "Target detail",
    "Target final",
}


def fixture_files() -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(FIXTURES.glob("*.xlsx"))
        if path.name != "malformed_product.xlsx"
    }


def issue_fingerprint(issues: list[list[IssueCell]]) -> str:
    payload = json.dumps(issues, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


@pytest.mark.parametrize(
    ("filename", "source_class"),
    [
        ("product_fixture.xlsx", "product"),
        ("loading_purchase_fixture.xlsx", "purchase"),
        ("so_chi_tiet_revenue_fixture.xlsx", "revenue"),
        ("tong_hop_ton_kho_inventory_fixture.xlsx", "inventory"),
        ("pre-order_fixture.xlsx", "preorder"),
        ("crm_sale_fixture.xlsx", "crm"),
        ("target_fixture.xlsx", "target"),
    ],
)
def test_classify_returns_current_source_class_when_fixture_filename_is_uploaded(
    filename: str, source_class: str
) -> None:
    # Given: a stable fixture filename matching one supported export class.
    # When: the upload classifier receives the filename.
    actual = server.classify(filename)
    # Then: the current source-class contract is preserved.
    assert actual == source_class


def test_norm_trims_and_uppercases_values_when_normalizing_headers() -> None:
    # Given: whitespace-padded mixed-case text and an empty source value.
    # When: the PSI normalizer processes those values.
    normalized = (server.norm("  Mã hàng  "), server.norm(None))
    # Then: text is canonicalized while absent values remain empty.
    assert normalized == ("MÃ HÀNG", "")


def test_build_reports_current_schema_gap_when_required_product_header_is_absent() -> None:
    # Given: a product workbook whose data header omits required PSI columns.
    malformed = FIXTURES / "malformed_product.xlsx"
    # When: the reconciliation build processes the malformed upload.
    result = server.build({"product_fixture.xlsx": malformed.read_bytes()})
    # Then: current behavior returns a workbook and reports the missing schema.
    assert ["Product", "Nguồn gốc", "Không tìm thấy cột bắt buộc"] in result["gaps"]


def test_build_returns_deterministic_mismatch_fingerprint_when_fixture_set_is_processed() -> None:
    # Given: the complete stable PSI fixture set.
    files = fixture_files()
    # When: the same input is processed twice.
    first = server.build(files)
    second = server.build(files)
    # Then: observable mismatch content and its fingerprint are deterministic.
    assert first["issues"] == second["issues"]
    assert first["issues"][0] == ["Revenue", "so_chi_tiet_revenue_fixture.xlsx", "Sheet", 6, "SKU-MISSING", "Missing revenue", "Missing Product mapping"]
    assert issue_fingerprint(first["issues"]) == "ff37cbbba03d3ea7a29ba2b269834d87fe056eb2bdc3dd8a2d8f8e98f2b5fd07"


def test_reviewed_preorder_feedback_never_changes_mismatch_detection() -> None:
    files = fixture_files()
    without_feedback = {name: content for name, content in files.items() if name != "pre-order_fixture.xlsx"}

    with_feedback_result = server.build(files)
    without_feedback_result = server.build(without_feedback)

    assert with_feedback_result["issues"] == without_feedback_result["issues"]
    assert with_feedback_result["gaps"] == without_feedback_result["gaps"]
