# Copyright 2026 PSI Tool contributors
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import psi_tool._output_lifecycle as lifecycle_module
import psi_tool.cli as cli_module
from psi_tool._exclusive_rename import rename_exclusive

if TYPE_CHECKING:
    import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "tests/psi_tool/fixtures/golden_manifest.toml"


def _swap_ancestor(ancestor: Path, moved: Path, outside: Path) -> None:
    _ = ancestor.rename(moved)
    _ = ancestor.symlink_to(outside, target_is_directory=True)


def test_ancestor_swap_before_parent_acquisition_cannot_redirect_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    base = tmp_path / "base"
    ancestor = base / "ancestor"
    parent = ancestor / "parent"
    parent.mkdir(parents=True)
    moved = base / "moved-ancestor"
    outside = tmp_path / "outside"
    outside_parent = outside / "parent"
    outside_parent.mkdir(parents=True)
    sentinel = outside_parent / "sentinel.bin"
    original_bytes = b"outside-parent-must-remain-unchanged"
    _ = sentinel.write_bytes(original_bytes)
    original_open = os.open
    swapped = False

    def swap_then_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if not swapped and path in (parent, "parent"):
            _swap_ancestor(ancestor, moved, outside)
            swapped = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", swap_then_open)

    # When
    result = cli_module.run_inspect(MANIFEST_PATH, parent / "run", PROJECT_ROOT)

    # Then
    assert result.overall == "FAIL"
    assert sentinel.read_bytes() == original_bytes
    assert not (outside_parent / "run").exists()
    assert not tuple(outside_parent.glob(".run-*.tmp"))
    assert not tuple((moved / "parent").glob(".run-*.tmp"))


def test_ancestor_swap_during_publish_cannot_leave_claimable_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    base = tmp_path / "base"
    ancestor = base / "ancestor"
    parent = ancestor / "parent"
    parent.mkdir(parents=True)
    moved = base / "moved-ancestor"
    outside = tmp_path / "outside"
    outside_parent = outside / "parent"
    outside_parent.mkdir(parents=True)
    sentinel = outside_parent / "sentinel.bin"
    original_bytes = b"outside-publish-target-must-remain-unchanged"
    _ = sentinel.write_bytes(original_bytes)
    original_rename = rename_exclusive

    def swap_then_publish(
        source_dir_fd: int,
        source_name: str,
        destination_dir_fd: int,
        destination_name: str,
    ) -> None:
        _swap_ancestor(ancestor, moved, outside)
        original_rename(
            source_dir_fd,
            source_name,
            destination_dir_fd,
            destination_name,
        )

    monkeypatch.setattr(lifecycle_module, "rename_exclusive", swap_then_publish)

    # When
    result = cli_module.run_inspect(MANIFEST_PATH, parent / "run", PROJECT_ROOT)

    # Then
    assert result.overall == "FAIL"
    assert sentinel.read_bytes() == original_bytes
    assert not (outside_parent / "run").exists()
    assert not (moved / "parent" / "run").exists()
    assert not tuple((moved / "parent").glob(".run-*.tmp"))
