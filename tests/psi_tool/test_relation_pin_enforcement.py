# Copyright 2026 PSI Tool contributors
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import psi_tool.cli as cli_module
from psi_tool._cache_hash import cache_key
from psi_tool.cache import CacheIntegrityError
from psi_tool.contracts import VerifiedManifest, load_verified_manifest
from psi_tool.report import build_failure_report
from tests.psi_tool.fd_helpers import materialize_cache_path as materialize_cache

if TYPE_CHECKING:
    from psi_tool._cache_models import RelationCacheMetadata
    from psi_tool._fd_types import DirectoryFd
    from psi_tool._report_models import InspectReport

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "tests/psi_tool/fixtures/golden_manifest.toml"


def _with_wrong_first_pin(verified: VerifiedManifest) -> VerifiedManifest:
    first, *remaining = verified.manifest.relations
    wrong_first = first.model_copy(update={"expected_relation_sha256": "0" * 64})
    wrong_manifest = verified.manifest.model_copy(
        update={"relations": (wrong_first, *remaining)},
    )
    return replace(verified, manifest=wrong_manifest)


def test_cold_cache_rejects_wrong_relation_pin_before_publication(
    tmp_path: Path,
) -> None:
    # Given
    verified = _with_wrong_first_pin(
        load_verified_manifest(MANIFEST_PATH, PROJECT_ROOT),
    )
    cache_root = tmp_path / "cache"

    # When / Then
    with pytest.raises(CacheIntegrityError, match="trusted manifest"):
        _ = materialize_cache(verified, cache_root)
    assert not cache_root.exists()
    assert tuple(tmp_path.glob(".cache-*.tmp")) == ()


def test_warm_cache_rejects_wrong_relation_pin(
    tmp_path: Path,
) -> None:
    # Given
    verified = load_verified_manifest(MANIFEST_PATH, PROJECT_ROOT)
    cache_root = tmp_path / "cache"
    _ = materialize_cache(verified, cache_root)
    wrong = _with_wrong_first_pin(verified)
    original_relation = verified.manifest.relations[0]
    wrong_relation = wrong.manifest.relations[0]
    original_path = cache_root / (
        f"{original_relation.relation_id}-"
        f"{cache_key(verified.manifest, original_relation)}.parquet"
    )
    wrong_path = cache_root / (
        f"{wrong_relation.relation_id}-"
        f"{cache_key(wrong.manifest, wrong_relation)}.parquet"
    )
    _ = original_path.rename(wrong_path)

    # When / Then
    with pytest.raises(CacheIntegrityError, match="trusted manifest"):
        _ = materialize_cache(wrong, cache_root)


def test_failed_report_cannot_produce_pass_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    output_dir = tmp_path / "run"

    def empty_cache(
        _verified: VerifiedManifest,
        _output_root_fd: DirectoryFd,
    ) -> tuple[RelationCacheMetadata, ...]:
        return ()

    def failed_report(
        _verified: VerifiedManifest,
        _metadata: tuple[RelationCacheMetadata, ...],
        _elapsed: int,
    ) -> InspectReport:
        return build_failure_report()

    monkeypatch.setattr(cli_module, "materialize_cache", empty_cache)
    monkeypatch.setattr(cli_module, "build_inspect_report", failed_report)

    # When
    result = cli_module.run_inspect(MANIFEST_PATH, output_dir, PROJECT_ROOT)

    # Then
    assert result.report.overall == "FAIL"
    assert result.overall == "FAIL"
    assert not result.report_published
    assert not output_dir.exists()
