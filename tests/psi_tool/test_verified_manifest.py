# Copyright 2026 PSI Tool contributors
from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

from psi_tool.contracts import load_verified_manifest
from psi_tool.report import build_inspect_report

if TYPE_CHECKING:
    import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "tests/psi_tool/fixtures/golden_manifest.toml"


def test_verified_manifest_hash_and_contract_share_one_byte_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    original = MANIFEST_PATH.read_bytes()
    changed = original.replace(b'contract_version = "1.1"', b'contract_version = "9.9"')
    reads = 0

    def changing_read_bytes(_path: Path) -> bytes:
        nonlocal reads
        reads += 1
        return original if reads == 1 else changed

    monkeypatch.setattr(Path, "read_bytes", changing_read_bytes)

    # When
    verified = load_verified_manifest(MANIFEST_PATH, PROJECT_ROOT)

    # Then
    assert reads == 1
    assert verified.manifest.contract_version == "1.1"
    assert verified.manifest_sha256 == hashlib.sha256(original).hexdigest()


def test_verified_manifest_loads_two_workspace_roots_without_cwd_cross_talk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    sources = load_verified_manifest(MANIFEST_PATH, PROJECT_ROOT).manifest.sources
    for root in (first_root, second_root):
        for source in sources:
            destination = root / source.relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.link(PROJECT_ROOT / source.relative_path, destination)

    def reject_chdir(
        _path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    ) -> None:
        detail = "production code must not change process CWD"
        raise AssertionError(detail)

    monkeypatch.setattr(os, "chdir", reject_chdir)

    # When
    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(
            load_verified_manifest,
            MANIFEST_PATH,
            first_root,
        )
        second_future = executor.submit(
            load_verified_manifest,
            MANIFEST_PATH,
            second_root,
        )
        first = first_future.result()
        second = second_future.result()

    # Then
    assert first.workspace_root == first_root.resolve()
    assert second.workspace_root == second_root.resolve()
    assert first.manifest_sha256 == second.manifest_sha256
    assert {item.path.parent.parent for item in first.sources} != {
        item.path.parent.parent for item in second.sources
    }


def test_report_uses_frozen_manifest_sha_after_manifest_path_changes(
    tmp_path: Path,
) -> None:
    # Given
    manifest_path = tmp_path / "manifest.toml"
    original = MANIFEST_PATH.read_bytes()
    _ = manifest_path.write_bytes(original)
    verified = load_verified_manifest(manifest_path, PROJECT_ROOT)
    _ = manifest_path.write_bytes(original + b"\n# changed after verification\n")

    # When
    report = build_inspect_report(verified, (), 1)

    # Then
    assert report.manifest_sha256 == hashlib.sha256(original).hexdigest()
