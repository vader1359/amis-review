# Copyright 2026 PSI Tool contributors
from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path
from typing import Literal, assert_never

import polars as pl
import pytest

import psi_tool.ingest as ingest_module
from psi_tool.cache import (
    CacheIntegrityError,
    CachePathError,
    relation_hash,
)
from psi_tool.contracts import (
    ManifestLoadError,
    RelationContract,
    ResolvedSourceIdentity,
    SourceManifest,
    VerifiedManifest,
    load_manifest,
    load_verified_manifest,
)
from psi_tool.ingest import IngestError, load_relation
from tests.psi_tool.fd_helpers import materialize_cache_path as materialize_cache

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "tests/psi_tool/fixtures/golden_manifest.toml"


class _SimulatedInterruptionError(OSError):
    pass


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
) -> Path:
    cache_root = tmp_path_factory.mktemp("c3-failure-cache-parent") / "cache"
    _ = materialize_cache(verified, cache_root)
    return cache_root


def _copy_sources(manifest: SourceManifest, workspace: Path) -> None:
    for source in manifest.sources:
        destination = workspace / source.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copy2(PROJECT_ROOT / source.relative_path, destination)


def _cache_state(cache_root: Path) -> tuple[tuple[str, str, int], ...]:
    return tuple(
        (
            path.name,
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_mtime_ns,
        )
        for path in sorted(cache_root.glob("*.parquet"))
    )


def test_warm_cache_revalidates_all_sources_before_hits(
    tmp_path: Path,
    manifest: SourceManifest,
) -> None:
    # Given
    workspace = tmp_path / "workspace"
    _copy_sources(manifest, workspace)
    cache_root = tmp_path / "cache"
    workspace_verified = load_verified_manifest(MANIFEST_PATH, workspace)
    cold = materialize_cache(workspace_verified, cache_root)
    before = _cache_state(cache_root)
    drifted_source = workspace / manifest.sources[0].relative_path
    _ = drifted_source.write_bytes(drifted_source.read_bytes() + b"drift")

    # When / Then
    with pytest.raises(ManifestLoadError, match="SHA-256"):
        _ = load_verified_manifest(MANIFEST_PATH, workspace)
    assert all(not item.cache_hit for item in cold)
    assert len(before) == 7
    assert _cache_state(cache_root) == before
    assert tuple(tmp_path.glob(".cache-*.tmp")) == ()


def test_materialize_cache_rejects_truncated_parquet(
    tmp_path: Path,
    golden_cache: Path,
    verified: VerifiedManifest,
) -> None:
    # Given
    cache_root = tmp_path / "cache"
    _ = shutil.copytree(golden_cache, cache_root)
    target = next(cache_root.glob("*.parquet"))
    _ = target.write_bytes(target.read_bytes()[:-16])

    # When / Then
    with pytest.raises(CacheIntegrityError):
        _ = materialize_cache(verified, cache_root)


def test_materialize_cache_rejects_valid_changed_content(
    tmp_path: Path,
    golden_cache: Path,
    verified: VerifiedManifest,
) -> None:
    # Given
    cache_root = tmp_path / "cache"
    _ = shutil.copytree(golden_cache, cache_root)
    target = next(cache_root.glob("*.parquet"))
    embedded = pl.read_parquet_metadata(target)
    original = pl.read_parquet(target)
    changed = original.with_columns(
        pl.when(pl.int_range(pl.len()) == 0)
        .then(pl.lit("tampered"))
        .otherwise(pl.first())
        .alias(original.columns[0]),
    )
    changed.write_parquet(target, metadata=embedded)

    # When / Then
    with pytest.raises(CacheIntegrityError, match="content"):
        _ = materialize_cache(verified, cache_root)


def test_warm_cache_rejects_self_consistent_metadata_tamper(
    tmp_path: Path,
    golden_cache: Path,
    verified: VerifiedManifest,
) -> None:
    # Given
    cache_root = tmp_path / "cache"
    _ = shutil.copytree(golden_cache, cache_root)
    target = next(cache_root.glob("crm_sales-*.parquet"))
    original = pl.read_parquet(target)
    changed = original.with_columns(
        pl.when(pl.int_range(pl.len()) == 0)
        .then(pl.lit("tampered"))
        .otherwise(pl.first())
        .alias(original.columns[0]),
    )
    forged = pl.read_parquet_metadata(target)
    forged["psi.relation_hash"] = relation_hash(changed)
    changed.write_parquet(target, metadata=forged)

    # When / Then
    with pytest.raises(CacheIntegrityError, match="trusted manifest"):
        _ = materialize_cache(verified, cache_root)


def test_materialize_cache_rejects_embedded_key_mismatch(
    tmp_path: Path,
    golden_cache: Path,
    verified: VerifiedManifest,
) -> None:
    # Given
    cache_root = tmp_path / "cache"
    _ = shutil.copytree(golden_cache, cache_root)
    target = next(cache_root.glob("*.parquet"))
    embedded = pl.read_parquet_metadata(target)
    embedded["psi.cache_key"] = "0" * 64
    pl.read_parquet(target).write_parquet(target, metadata=embedded)

    # When / Then
    with pytest.raises(CacheIntegrityError, match="metadata"):
        _ = materialize_cache(verified, cache_root)


def test_load_relation_rejects_renamed_projected_header(
    tmp_path: Path,
    manifest: SourceManifest,
) -> None:
    # Given
    relation = manifest.relation("crm_sales")
    source = manifest.source(relation.source_id)
    copied_source = tmp_path / source.relative_path
    copied_source.parent.mkdir(parents=True)
    original_header = relation.projection[0].source_header.encode()
    replaced = False
    with (
        zipfile.ZipFile(PROJECT_ROOT / source.relative_path) as source_archive,
        zipfile.ZipFile(copied_source, "w") as copied_archive,
    ):
        for member in source_archive.infolist():
            payload = source_archive.read(member.filename)
            if original_header in payload:
                payload = payload.replace(
                    original_header,
                    b"renamed projected header",
                    1,
                )
                replaced = True
            copied_archive.writestr(member, payload)
    assert replaced
    changed_source = source.model_copy(
        update={"sha256": hashlib.sha256(copied_source.read_bytes()).hexdigest()},
    )
    changed_manifest = manifest.model_copy(
        update={
            "sources": tuple(
                changed_source if item.source_id == source.source_id else item
                for item in manifest.sources
            ),
        },
    )
    verified = VerifiedManifest(
        manifest=changed_manifest,
        manifest_sha256="0" * 64,
        workspace_root=tmp_path.resolve(),
        sources=(ResolvedSourceIdentity(source=changed_source, path=copied_source),),
    )

    # When / Then
    with pytest.raises(IngestError, match="projected header"):
        _ = load_relation(verified, relation)


@pytest.mark.parametrize("scenario", ["symlink", "regular_file", "foreign"])
def test_materialize_cache_rejects_unsafe_output_state(
    tmp_path: Path,
    scenario: Literal["symlink", "regular_file", "foreign"],
    verified: VerifiedManifest,
) -> None:
    # Given
    cache_root = tmp_path / "cache"
    match scenario:
        case "symlink":
            outside = tmp_path / "outside"
            outside.mkdir()
            _ = cache_root.symlink_to(outside, target_is_directory=True)
        case "regular_file":
            _ = cache_root.write_text("foreign", encoding="utf-8")
        case "foreign":
            cache_root.mkdir()
            _ = (cache_root / "foreign.txt").write_text("foreign", encoding="utf-8")
        case _:
            assert_never(scenario)

    # When / Then
    with pytest.raises(CachePathError):
        _ = materialize_cache(verified, cache_root)


def test_materialize_cache_cleans_interrupted_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    verified: VerifiedManifest,
) -> None:
    # Given
    cache_root = tmp_path / "cache"
    original = ingest_module.load_relation
    calls = 0

    def interrupt_after_first(
        source_manifest: VerifiedManifest,
        relation: RelationContract,
    ) -> pl.DataFrame:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise _SimulatedInterruptionError
        return original(source_manifest, relation)

    monkeypatch.setattr(ingest_module, "load_relation", interrupt_after_first)

    # When / Then
    with pytest.raises(_SimulatedInterruptionError):
        _ = materialize_cache(verified, cache_root)
    assert not cache_root.exists()
    assert tuple(tmp_path.glob(".cache-*.tmp")) == ()
