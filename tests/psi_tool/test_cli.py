# Copyright 2026 PSI Tool contributors
from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import psi_tool.cli as cli_module
from psi_tool._report_json import serialize_report
from psi_tool.contracts import load_verified_manifest
from tests.psi_tool.fd_helpers import materialize_cache_path as materialize_cache

if TYPE_CHECKING:
    import pytest

    from psi_tool._fd_types import DirectoryFd
    from psi_tool._report_models import InspectReport
from psi_tool.report import (
    build_inspect_report,
    semantic_sha256,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "tests/psi_tool/fixtures/golden_manifest.toml"


def test_report_semantic_hash_is_stable_when_cache_status_and_timing_change(
    tmp_path: Path,
) -> None:
    # Given
    verified = load_verified_manifest(MANIFEST_PATH, PROJECT_ROOT)
    cold_cache = materialize_cache(verified, tmp_path / "cache")
    warm_cache = materialize_cache(verified, tmp_path / "cache")

    # When
    cold = build_inspect_report(verified, cold_cache, 10)
    warm = build_inspect_report(verified, warm_cache, 20)

    # Then
    assert cold.overall == warm.overall == "PASS"
    assert cold.semantic_sha256 == warm.semantic_sha256
    assert serialize_report(cold) != serialize_report(warm)


def test_report_fails_for_schema_or_shape_mismatch(tmp_path: Path) -> None:
    # Given
    verified = load_verified_manifest(MANIFEST_PATH, PROJECT_ROOT)
    metadata = materialize_cache(verified, tmp_path / "cache")
    malformed = replace(metadata[0], rows=metadata[0].rows + 1)

    # When
    report = build_inspect_report(
        verified,
        (malformed, *metadata[1:]),
        1,
    )

    # Then
    assert report.overall == "FAIL"


def test_report_fails_for_ordered_schema_mismatch(tmp_path: Path) -> None:
    # Given
    verified = load_verified_manifest(MANIFEST_PATH, PROJECT_ROOT)
    metadata = materialize_cache(verified, tmp_path / "cache")
    malformed = replace(metadata[0], schema=metadata[0].schema[::-1])

    # When
    report = build_inspect_report(
        verified,
        (malformed, *metadata[1:]),
        1,
    )

    # Then
    assert report.overall == "FAIL"


def test_report_is_redacted_and_json_is_canonical(tmp_path: Path) -> None:
    # Given
    verified = load_verified_manifest(MANIFEST_PATH, PROJECT_ROOT)
    metadata = materialize_cache(verified, tmp_path / "cache")

    # When
    report = build_inspect_report(verified, metadata, 1)
    serialized = serialize_report(report)
    # Then
    assert serialized.endswith("\n")
    assert str(PROJECT_ROOT) not in serialized
    assert "PSI_SAMPLE_INPUT/CRM_Sale_sample.xlsx" not in serialized
    assert "timestamp" not in serialized
    assert f'"semantic_sha256":"{semantic_sha256(report)}"' in serialized


def test_inspect_removes_new_run_root_when_report_publication_is_interrupted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    error_detail = "simulated report interruption"

    def interrupt_report_write(
        _directory_fd: DirectoryFd,
        _name: str,
        _report: InspectReport,
    ) -> None:
        raise OSError(error_detail)

    monkeypatch.setattr(
        cli_module,
        "write_report_atomic",
        interrupt_report_write,
    )

    # When
    result = cli_module.run_inspect(MANIFEST_PATH, output_dir, PROJECT_ROOT)

    # Then
    assert result.overall == "FAIL"
    assert not output_dir.exists()
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_inspect_rejects_regular_file_output_without_leaking_or_mutating(
    tmp_path: Path,
) -> None:
    # Given
    output_file = tmp_path / "output-file"
    original_bytes = b"do not modify"
    _ = output_file.write_bytes(original_bytes)

    # When
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "psi_tool",
            "inspect",
            "--manifest",
            str(MANIFEST_PATH),
            "--output-dir",
            str(output_file),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    # Then
    assert completed.returncode != 0
    assert completed.stderr.splitlines() == ["inspect failed: validation_failed"]
    assert "Traceback" not in completed.stderr
    assert str(PROJECT_ROOT) not in completed.stderr
    assert str(tmp_path) not in completed.stderr
    assert "NotADirectoryError" not in completed.stderr
    assert output_file.read_bytes() == original_bytes
    assert not tuple(tmp_path.glob(".*.tmp"))
