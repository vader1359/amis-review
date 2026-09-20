"""Offline checks for the read-only Power Query package and corrected fixture."""

import json
from pathlib import Path


ROOT = Path(__file__).parent
CARDINALITY = json.loads((ROOT / "fixture-cardinality.json").read_text())


def test_helper_is_parameterized_read_only_and_pinned() -> None:
    source = (ROOT / "GetPSIPayload.m").read_text()
    assert "WHERE id = @report_id" in source
    assert "Table.RowCount(Snapshot) = 1" in source
    assert "INSERT" not in source and "UPDATE" not in source and "DELETE" not in source


def test_each_payload_relation_has_a_matching_query() -> None:
    for relation, filename in {
        "inventory_rows": "inventory.m", "purchase_rows": "purchase.m",
        "crm_product_rows": "sales_crm.m", "revenue_rows": "revenue.m",
        "preorder_rows": "preorder.m",
    }.items():
        assert relation in (ROOT / filename).read_text()


def test_corrected_fixture_cardinality_is_the_expected_psI_snapshot() -> None:
    assert {key: CARDINALITY[key] for key in ("inventory_rows", "purchase_rows", "crm_product_rows", "revenue_rows", "preorder_rows")} == {
        "inventory_rows": 3168, "purchase_rows": 2605, "crm_product_rows": 8426,
        "revenue_rows": 8786, "preorder_rows": 402,
    }


def test_unavailable_facts_are_explicitly_null_or_empty() -> None:
    assert "each null" in (ROOT / "preorder.m").read_text()
    assert "each null" in (ROOT / "sales_crm.m").read_text()
    assert "#table" in (ROOT / "stock_in.m").read_text()


def test_brand_code_is_never_relabelled_as_brand_name() -> None:
    for filename in ("inventory.m", "revenue.m", "preorder.m"):
        source = (ROOT / filename).read_text()
        assert 'Table.RenameColumns(Selected, {{"BRAND CODE", "BRAND NAME"}})' not in source
        assert 'Table.AddColumn(Selected, "BRAND NAME", each null' in source
