# Copyright 2026 PSI Tool contributors
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import psi_tool.cli as cli_module
import psi_tool.ingest as ingest_module
from psi_tool.report import write_report_atomic

if TYPE_CHECKING:
    import polars as pl
    import pytest

    from psi_tool._cache_models import RelationCacheMetadata
    from psi_tool._fd_types import DirectoryFd
    from psi_tool._report_models import InspectReport
    from psi_tool.contracts import RelationContract, VerifiedManifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "tests/psi_tool/fixtures/golden_manifest.toml"


class _SimulatedOutputInterruptionError(OSError):
    pass


def test_inspect_rejects_lexical_symlink_parent_without_mutating_target(
    tmp_path: Path,
) -> None:
    # Given
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    _ = sentinel.write_text("preserve", encoding="utf-8")
    (outside / "existing").mkdir()
    linked_parent = tmp_path / "linked-parent"
    _ = linked_parent.symlink_to(outside, target_is_directory=True)

    # When
    result = cli_module.run_inspect(
        MANIFEST_PATH,
        linked_parent / "existing" / "run",
        PROJECT_ROOT,
    )

    # Then
    assert result.overall == "FAIL"
    assert sentinel.read_text(encoding="utf-8") == "preserve"
    assert not (outside / "existing" / "run").exists()


def test_inspect_cleanup_does_not_follow_swapped_staging_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    _ = sentinel.write_text("preserve", encoding="utf-8")

    def swap_staging_then_interrupt(
        _verified: VerifiedManifest,
        _output_root_fd: DirectoryFd,
    ) -> tuple[RelationCacheMetadata, ...]:
        staging = next(tmp_path.glob(".run-*.tmp"))
        moved = staging.with_name(f"{staging.name}-moved")
        _ = staging.rename(moved)
        _ = staging.symlink_to(outside, target_is_directory=True)
        raise _SimulatedOutputInterruptionError

    monkeypatch.setattr(cli_module, "materialize_cache", swap_staging_then_interrupt)

    # When
    result = cli_module.run_inspect(MANIFEST_PATH, output_dir, PROJECT_ROOT)

    # Then
    assert result.overall == "FAIL"
    assert sentinel.read_text(encoding="utf-8") == "preserve"
    assert not output_dir.exists()
    assert not tuple(tmp_path.glob(".run-*.tmp-moved"))


def test_inspect_exclusive_publish_preserves_destination_that_appears(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    sentinel = output_dir / "sentinel.txt"

    def publish_destination_before_report(
        directory_fd: DirectoryFd,
        name: str,
        report: InspectReport,
    ) -> None:
        write_report_atomic(directory_fd, name, report)
        output_dir.mkdir()
        _ = sentinel.write_text("preserve", encoding="utf-8")

    monkeypatch.setattr(
        cli_module,
        "write_report_atomic",
        publish_destination_before_report,
    )

    # When
    result = cli_module.run_inspect(MANIFEST_PATH, output_dir, PROJECT_ROOT)

    # Then
    assert result.overall == "FAIL"
    assert sentinel.read_text(encoding="utf-8") == "preserve"
    assert not tuple(tmp_path.glob(".run-*.tmp"))


def test_active_stage_rename_during_write_does_not_mutate_symlink_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.bin"
    original_bytes = b"external-target-must-not-change"
    _ = sentinel.write_bytes(original_bytes)
    original_load = ingest_module.load_relation
    swapped = False

    def swap_during_first_relation(
        verified: VerifiedManifest,
        relation: RelationContract,
    ) -> pl.DataFrame:
        nonlocal swapped
        if not swapped:
            staging = next(tmp_path.glob(".run-*.tmp"))
            moved = staging.with_name(f"{staging.name}-moved")
            _ = staging.rename(moved)
            _ = staging.symlink_to(outside, target_is_directory=True)
            swapped = True
        return original_load(verified, relation)

    monkeypatch.setattr(ingest_module, "load_relation", swap_during_first_relation)

    # When
    result = cli_module.run_inspect(MANIFEST_PATH, output_dir, PROJECT_ROOT)

    # Then
    assert result.overall == "FAIL"
    assert sentinel.read_bytes() == original_bytes
    assert not (outside / "cache").exists()
    assert not tuple(tmp_path.glob(".run-*.tmp-moved"))
