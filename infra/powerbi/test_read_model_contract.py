"""Static contract checks for the reviewable Power BI read-model migration."""

from pathlib import Path


SQL = (Path(__file__).with_name("001_psi_powerbi_read_model.sql").read_text())


def test_never_selects_latest_psi_draft() -> None:
    assert "FROM psi_powerbi.report_selections s" in SQL
    assert "ORDER BY s.dataset_key, s.selection_id DESC" in SQL
    assert "reports_created_at_idx" not in SQL
    assert "r.created_at DESC" not in SQL


def test_selection_pins_immutable_report_and_reference_snapshots() -> None:
    assert "report_id text NOT NULL REFERENCES psi_preview.reports(id)" in SQL
    assert "product_reference_id text NOT NULL" in SQL
    assert "target_reference_id text NOT NULL" in SQL
    assert "report_selections_immutable BEFORE UPDATE OR DELETE" in SQL
    assert "reference_snapshots_immutable BEFORE UPDATE OR DELETE" in SQL
    assert "operator_selected_corrected_local_snapshot" in SQL


def test_current_powerbi_business_tables_are_exposed() -> None:
    for view in (
        "product_reference", "target_reference", "inventory", "revenue",
        "preorder", "sales_crm", "purchase", "stock_in", "lineage",
    ):
        assert (
            f"CREATE OR REPLACE VIEW psi_powerbi.{view}" in SQL
            or f"CREATE VIEW psi_powerbi.{view}" in SQL
        )


def test_powerbi_m_template_maps_all_eight_model_tables() -> None:
    template = Path(__file__).with_name("powerbi-postgresql-source.m").read_text()
    for table in (
        '#"1. Product"', '#"2. Inventory"', '#"3. Purchase"',
        '#"4. Sales_CRM"', '#"5. Revenue"', '#"6. Preorder"',
        '#"7. Stock_In"', 'Target = Target',
    ):
        assert table in template


def test_missing_inputs_are_explicit_nulls_not_fabricated_values() -> None:
    for column in (
        'NULL::text AS "F.O.C"', 'NULL::numeric AS "PRICE ORDER"',
        'WHERE FALSE',
    ):
        assert column in SQL
    assert 'AS "F.O.C"' in SQL
    assert "COALESCE(NULL" not in SQL


def test_current_supported_derived_columns_match_the_clone_contract() -> None:
    for expression in (
        'NULLIF(NULLIF(row.value->>8, \'\')::numeric, 0)',
        'NULLIF(NULLIF(row.value->>10, \'\')::numeric, 0)',
        'row.value->>13, \'\')::date AS "HẠN GIAO HÀNG"',
        'NULL::text AS "CUSTOMER"',
        'AS "Index"',
    ):
        assert expression in SQL


def test_reader_gets_views_only() -> None:
    assert "GRANT USAGE ON SCHEMA psi_powerbi TO powerbi_reader" in SQL
    assert "GRANT SELECT ON psi_powerbi.product_reference" in SQL
    assert "GRANT INSERT" not in SQL
