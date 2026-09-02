# Copyright 2026 PSI Tool contributors
from __future__ import annotations

import re
from pathlib import Path

import pytest

from psi_tool.contracts import ManifestLoadError, load_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "tests/psi_tool/fixtures/golden_manifest.toml"


def test_load_manifest_locks_the_seven_golden_source_relations() -> None:
    # Given
    expected_relation_ids = {
        "crm_sales",
        "crm_sale_items",
        "product_master",
        "sales_detail_misa",
        "inventory",
        "purchase_po",
        "target",
    }

    # When
    manifest = load_manifest(MANIFEST_PATH, PROJECT_ROOT)

    # Then
    assert manifest.schema_version == "1.0"
    assert manifest.contract_version == "1.1"
    assert manifest.relation_hash_algorithm == "psi-semantic-string-v1"
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", relation.expected_relation_sha256)
        for relation in manifest.relations
    )
    assert manifest.as_of.isoformat() == "2026-08-30"
    assert {relation.relation_id for relation in manifest.relations} == (
        expected_relation_ids
    )
    assert len(manifest.relations) == 7
    assert len(manifest.sources) == 6
    assert manifest.relation("crm_sales").physical_shape == (9983, 40)
    assert manifest.relation("crm_sales").logical_data_shape == (9982, 40)
    assert manifest.relation("sales_detail_misa").physical_shape == (12053, 38)
    assert manifest.relation("sales_detail_misa").logical_data_shape == (12049, 38)
    assert manifest.relation("inventory").physical_shape == (3412, 15)
    assert manifest.relation("inventory").logical_data_shape == (3409, 15)
    assert manifest.relation("purchase_po").physical_shape == (2627, 86)
    assert manifest.relation("purchase_po").logical_data_shape == (2624, 86)
    assert manifest.relation("target").physical_shape == (20, 9)
    assert manifest.relation("target").logical_data_shape == (19, 9)
    assert manifest.relation("crm_sales").source_id == "crm_sale_workbook"
    assert manifest.relation("crm_sale_items").source_id == "crm_sale_workbook"
    assert manifest.relation("product_master").projection_source_header("category") == (
        "Category "
    )
    assert (
        manifest.relation("product_master").projection_source_header("sub_category")
        == "Sub Category "
    )
    assert (
        manifest.relation("target").projection_source_header(
            "internal_target_value_2026",
        )
        == "Internal Target value\n2026"
    )
    assert (
        manifest.relation("purchase_po").projection_source_header(
            "total_transport_cost",
        )
        == "TOTAL COST\nVận chuyển"
    )
    assert manifest.relation("inventory").header_strategy.parent_row_index == 2
    assert manifest.relation("inventory").header_strategy.child_row_index == 3
    assert (
        manifest.relation("inventory").projection_source_header("closing_quantity")
        == "Cuối kỳ - Số lượng"
    )


def test_manifest_projects_only_unique_string_columns_from_relative_sources() -> None:
    # Given
    manifest = load_manifest(MANIFEST_PATH, PROJECT_ROOT)

    # When
    sources = manifest.sources
    relations = manifest.relations

    # Then
    assert all(
        source.relative_path.parts[0] == "PSI_SAMPLE_INPUT" for source in sources
    )
    assert all(".." not in source.relative_path.parts for source in sources)
    assert all(re.fullmatch(r"[0-9a-f]{64}", source.sha256) for source in sources)
    assert all(
        len({field.canonical_name for field in relation.projection})
        == len(relation.projection)
        for relation in relations
    )
    assert all(
        field.dtype == "String"
        for relation in relations
        for field in relation.projection
    )
    sales_detail_strategy = manifest.relation("sales_detail_misa").header_strategy
    purchase_strategy = manifest.relation("purchase_po").header_strategy
    assert sales_detail_strategy.nonblank_header_count == 38
    assert purchase_strategy.blank_column_numbers_one_based == (
        1,
        85,
        86,
    )
    assert manifest.relation("purchase_po").header_strategy.distinguished_headers == (
        (60, "OF | AF\n"),
        (69, "OF | AF\n/mã"),
    )


def test_manifest_fails_closed_when_carry_forward_reason_is_missing(
    tmp_path: Path,
) -> None:
    # Given
    invalid_manifest = tmp_path / "missing-carry-forward-reason.toml"
    content = MANIFEST_PATH.read_text(encoding="utf-8")
    bytes_written = invalid_manifest.write_text(
        content.replace(
            (
                "carry_forward_reason = "
                '"sanitized golden fixture approved for ingest checkpoint"\n'
            ),
            "",
            1,
        ),
        encoding="utf-8",
    )
    assert bytes_written > 0

    # When / Then
    with pytest.raises(ManifestLoadError, match="carry-forward"):
        _ = load_manifest(invalid_manifest, PROJECT_ROOT)


@pytest.mark.parametrize(
    ("scenario", "old", "new", "error_pattern"),
    [
        (
            "missing_source_file",
            "PSI_SAMPLE_INPUT/CRM_Sale_sample.xlsx",
            "PSI_SAMPLE_INPUT/missing-source.xlsx",
            "source file",
        ),
        (
            "hash_drift",
            "d3c7ddb0835d3ec12c52d50a34e96ca57f5a5126f2d531cc35173213e0fe3c4d",
            "0000000000000000000000000000000000000000000000000000000000000000",
            "SHA-256",
        ),
        (
            "missing_projected_header",
            'source_header = "Số đơn hàng"',
            'source_header = "missing projected header"',
            "projected header",
        ),
        (
            "duplicate_source_header",
            'source_header = "Ngày duyệt"',
            'source_header = "Số đơn hàng"',
            "duplicate source header",
        ),
        (
            "invalid_header_row",
            'header_strategy = { kind = "single_row", row_index = 0 }',
            'header_strategy = { kind = "single_row", row_index = 99999 }',
            "header row",
        ),
        (
            "missing_sheet",
            'sheet_name = "Danh sách"',
            'sheet_name = "missing sheet"',
            "sheet",
        ),
        (
            "invalid_nonblank_header_count",
            "nonblank_header_count = 38",
            "nonblank_header_count = 999",
            "nonblank header count",
        ),
    ],
)
def test_load_manifest_fails_closed_for_invalid_workspace_source_contract(
    tmp_path: Path,
    scenario: str,
    old: str,
    new: str,
    error_pattern: str,
) -> None:
    # Given
    invalid_manifest = tmp_path / f"{scenario}.toml"
    content = MANIFEST_PATH.read_text(encoding="utf-8")
    bytes_written = invalid_manifest.write_text(
        content.replace(old, new, 1),
        encoding="utf-8",
    )
    assert bytes_written > 0

    # When / Then
    with pytest.raises(ManifestLoadError, match=error_pattern):
        _ = load_manifest(invalid_manifest, PROJECT_ROOT)


def test_load_manifest_serializes_independent_loads_stably() -> None:
    # Given
    first_load = load_manifest(MANIFEST_PATH, PROJECT_ROOT)

    # When
    second_load = load_manifest(MANIFEST_PATH, PROJECT_ROOT)

    # Then
    assert first_load is not second_load
    assert first_load.to_deterministic_json() == second_load.to_deterministic_json()
