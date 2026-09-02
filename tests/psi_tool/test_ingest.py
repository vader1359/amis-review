# Copyright 2026 PSI Tool contributors
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

import psi_tool.cache as cache_module
from psi_tool.contracts import (
    SourceManifest,
    VerifiedManifest,
    load_manifest,
    load_verified_manifest,
)
from psi_tool.ingest import load_relation
from tests.psi_tool.fd_helpers import materialize_cache_path as materialize_cache

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "tests/psi_tool/fixtures/golden_manifest.toml"


def test_relation_hash_distinguishes_null_empty_and_csv_boundaries() -> None:
    # Given
    null_frame = pl.DataFrame({"value": [None, 'a,"b\nc']}, schema={"value": pl.String})
    empty_frame = pl.DataFrame({"value": ["", 'a,"b\nc']}, schema={"value": pl.String})
    boundary_frame = pl.DataFrame(
        {"value": [None, 'a,"b', "c"]},
        schema={"value": pl.String},
    )

    # When
    hashes = {
        cache_module.relation_hash(null_frame),
        cache_module.relation_hash(empty_frame),
        cache_module.relation_hash(boundary_frame),
    }

    # Then
    assert len(hashes) == 3


def test_relation_hash_is_stable_across_processes() -> None:
    # Given
    frame = pl.DataFrame({"value": [None, 'a,"b\nc']}, schema={"value": pl.String})
    expected = cache_module.relation_hash(frame)
    script = (
        "import polars as pl; from psi_tool.cache import relation_hash; "
        "frame=pl.DataFrame({'value':[None,'a,\"b\\nc']},"
        "schema={'value':pl.String}); print(relation_hash(frame))"
    )

    # When
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    # Then
    assert completed.stdout.strip() == expected


@pytest.fixture(scope="module")
def manifest() -> SourceManifest:
    return load_manifest(MANIFEST_PATH, PROJECT_ROOT)


@pytest.fixture(scope="module")
def verified() -> VerifiedManifest:
    return load_verified_manifest(MANIFEST_PATH, PROJECT_ROOT)


@pytest.fixture(scope="module")
def golden_cache(
    tmp_path_factory: pytest.TempPathFactory,
    verified: VerifiedManifest,
) -> tuple[Path, tuple[str, ...], tuple[str, ...]]:
    cache_root = tmp_path_factory.mktemp("c3-cache-parent") / "cache"
    cold = materialize_cache(verified, cache_root)
    warm = materialize_cache(verified, cache_root)
    return (
        cache_root,
        tuple(item.parquet_sha256 for item in cold),
        tuple(item.parquet_sha256 for item in warm),
    )


def test_materialize_cache_misses_then_hits_all_seven_relations(
    tmp_path: Path,
    verified: VerifiedManifest,
) -> None:
    # Given
    cache_root = tmp_path / "cache"

    # When
    cold = materialize_cache(verified, cache_root)
    warm = materialize_cache(verified, cache_root)

    # Then
    assert len(cold) == len(warm) == 7
    assert all(not item.cache_hit for item in cold)
    assert all(item.cache_hit for item in warm)
    assert tuple(item.stable_fields() for item in cold) == tuple(
        item.stable_fields() for item in warm
    )
    assert len(tuple(cache_root.glob("*.parquet"))) == 7


def test_cache_parquet_matches_contract_and_polars_readback(
    golden_cache: tuple[Path, tuple[str, ...], tuple[str, ...]],
    manifest: SourceManifest,
    verified: VerifiedManifest,
) -> None:
    # Given
    cache_root, cold_hashes, warm_hashes = golden_cache

    # When
    metadata = materialize_cache(verified, cache_root)

    # Then
    assert cold_hashes == warm_hashes
    for item in metadata:
        relation = manifest.relation(item.relation_id)
        frame = pl.read_parquet(cache_root / item.relative_path)
        assert frame.height == relation.logical_data_shape[0]
        assert frame.width == len(relation.projection)
        assert tuple(frame.columns) == tuple(
            field.canonical_name for field in relation.projection
        )
        assert all(dtype == pl.String for dtype in frame.dtypes)
        assert tuple(
            frame.get_column(name).null_count() for name in frame.columns
        ) == tuple(nulls.null_count for nulls in item.null_counts)
        assert (
            hashlib.sha256(
                (cache_root / item.relative_path).read_bytes(),
            ).hexdigest()
            == item.parquet_sha256
        )


def test_load_relation_projects_ordered_string_columns(
    manifest: SourceManifest,
    verified: VerifiedManifest,
) -> None:
    # Given
    relation = manifest.relation("inventory")

    # When
    frame = load_relation(verified, relation)

    # Then
    assert frame.shape == (relation.logical_data_shape[0], len(relation.projection))
    assert frame.columns == [field.canonical_name for field in relation.projection]
    assert all(dtype == pl.String for dtype in frame.dtypes)
