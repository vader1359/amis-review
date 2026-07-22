from pathlib import Path

from psi_engine import PsiBuildResult, build, classify, norm


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


def test_engine_public_api_returns_typed_result_for_fixture_upload() -> None:
    # Given: one supported product workbook at the engine boundary.
    files = {"product_fixture.xlsx": (FIXTURES / "product_fixture.xlsx").read_bytes()}
    # When: the side-effect-free engine builds the reconciliation artifact.
    result = build(files)
    # Then: the result exposes typed reconciliation data and a workbook payload.
    assert isinstance(result, PsiBuildResult)
    assert result.summary["Product master rows"] == 1
    assert result.xlsx.startswith(b"PK")


def test_engine_public_api_preserves_filename_and_header_normalization() -> None:
    # Given: the current supported filename and a padded mixed-case header.
    # When: the public engine helpers normalize and classify those values.
    actual = (classify("loading_purchase_fixture.xlsx"), norm("  Mã hàng  "))
    # Then: compatibility classification and normalization remain unchanged.
    assert actual == ("purchase", "MÃ HÀNG")
