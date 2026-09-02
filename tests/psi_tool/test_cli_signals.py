# Copyright 2026 PSI Tool contributors
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pytest
from typer.testing import CliRunner

import psi_tool.cli as cli_module
from psi_tool._output_lifecycle import OutputSession
from psi_tool._signals import InspectCancelled
from psi_tool.cache import materialize_cache

if TYPE_CHECKING:
    from psi_tool._cache_models import RelationCacheMetadata
    from psi_tool._fd_types import DirectoryFd
    from psi_tool._fd_walk import OpenedParent
    from psi_tool.contracts import VerifiedManifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "tests/psi_tool/fixtures/golden_manifest.toml"


def _start_real_inspect(output_dir: Path) -> subprocess.Popen[str]:
    uv_path = shutil.which("uv")
    assert uv_path is not None
    return subprocess.Popen(
        [
            uv_path,
            "run",
            "psi",
            "inspect",
            "--manifest",
            str(MANIFEST_PATH),
            "--output-dir",
            str(output_dir),
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def _wait_for_partial_parquet(parent: Path, output_name: str) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        stages = tuple(parent.glob(f".{output_name}-*.tmp"))
        if stages and tuple(stages[0].glob("cache/*.parquet")):
            return
        time.sleep(0.02)
    pytest.fail("real inspect did not create a partial Parquet before deadline")


@pytest.mark.parametrize(
    ("sent_signal", "expected_code"),
    [(signal.SIGINT, 130), (signal.SIGTERM, 143)],
)
def test_real_cold_process_group_signal_cleans_private_output(
    tmp_path: Path,
    sent_signal: signal.Signals,
    expected_code: Literal[130, 143],
) -> None:
    # Given
    output_dir = tmp_path / "run"
    process = _start_real_inspect(output_dir)
    _wait_for_partial_parquet(tmp_path, output_dir.name)

    # When
    os.killpg(process.pid, sent_signal)
    stdout, stderr = process.communicate(timeout=30)

    # Then
    assert process.returncode == expected_code
    assert stdout.startswith("FAIL report=none")
    assert stderr.splitlines() == ["inspect cancelled"]
    assert not output_dir.exists()
    assert not tuple(tmp_path.glob(".run-*.tmp"))


def test_second_signal_is_ignored_during_controlled_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    original_cleanup = OutputSession.cleanup

    def interrupt_first(
        _verified: VerifiedManifest,
        _output_root_fd: DirectoryFd,
    ) -> tuple[RelationCacheMetadata, ...]:
        raise InspectCancelled(signal.SIGINT)

    def cleanup_with_second_signal(session: OutputSession) -> None:
        os.kill(os.getpid(), signal.SIGTERM)
        original_cleanup(session)

    monkeypatch.setattr(cli_module, "materialize_cache", interrupt_first)
    monkeypatch.setattr(OutputSession, "cleanup", cleanup_with_second_signal)

    # When
    result = cli_module.run_inspect(MANIFEST_PATH, output_dir, PROJECT_ROOT)

    # Then
    assert result.exit_code == 130
    assert not output_dir.exists()
    assert not tuple(tmp_path.glob(".run-*.tmp"))


@pytest.mark.parametrize(
    ("sent_signal", "expected_code"),
    [(signal.SIGINT, 130), (signal.SIGTERM, 143)],
)
def test_signal_after_stage_before_session_binding_is_deferred_and_cleaned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sent_signal: signal.Signals,
    expected_code: Literal[130, 143],
) -> None:
    # Given
    output_dir = tmp_path / "run"
    open_fds = len(tuple(Path("/dev/fd").iterdir()))
    original_init = OutputSession.__init__
    original_cleanup = OutputSession.cleanup

    def signal_before_assignment(
        session: OutputSession,
        parent: OpenedParent,
        root_fd: DirectoryFd,
        owned_name: str | None,
    ) -> None:
        original_init(session, parent, root_fd, owned_name)
        os.kill(os.getpid(), sent_signal)

    def cleanup_with_second_signal(session: OutputSession) -> None:
        second = signal.SIGTERM if sent_signal == signal.SIGINT else signal.SIGINT
        os.kill(os.getpid(), second)
        original_cleanup(session)

    monkeypatch.setattr(OutputSession, "__init__", signal_before_assignment)
    monkeypatch.setattr(OutputSession, "cleanup", cleanup_with_second_signal)

    # When
    result = CliRunner().invoke(
        cli_module.app,
        [
            "inspect",
            "--manifest",
            str(MANIFEST_PATH),
            "--output-dir",
            str(output_dir),
        ],
    )

    # Then
    assert result.exit_code == expected_code
    assert result.stdout.startswith("FAIL report=none")
    assert result.stderr.splitlines() == ["inspect cancelled"]
    assert not output_dir.exists()
    assert not tuple(tmp_path.glob(".run-*.tmp"))
    assert len(tuple(Path("/dev/fd").iterdir())) == open_fds


def test_warm_cancellation_replaces_prior_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    cold = cli_module.run_inspect(MANIFEST_PATH, output_dir, PROJECT_ROOT)
    assert cold.overall == "PASS"

    def interrupt_warm(
        _verified: VerifiedManifest,
        _output_root_fd: DirectoryFd,
    ) -> tuple[RelationCacheMetadata, ...]:
        raise InspectCancelled(signal.SIGINT)

    monkeypatch.setattr(cli_module, "materialize_cache", interrupt_warm)

    # When
    result = cli_module.run_inspect(MANIFEST_PATH, output_dir, PROJECT_ROOT)

    # Then
    report = (output_dir / "inspect-report.json").read_text(encoding="utf-8")
    assert result.exit_code == 130
    assert '"overall":"FAIL"' in report
    assert '"failure":"validation_failed"' in report


def test_active_warm_output_swap_does_not_mutate_external_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    cold = cli_module.run_inspect(MANIFEST_PATH, output_dir, PROJECT_ROOT)
    assert cold.overall == "PASS"
    moved = tmp_path / "moved-run"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.bin"
    original_bytes = b"preserve-external-target"
    _ = sentinel.write_bytes(original_bytes)
    original_materialize = materialize_cache

    def swap_then_materialize(
        verified: VerifiedManifest,
        output_root_fd: DirectoryFd,
    ) -> tuple[RelationCacheMetadata, ...]:
        _ = output_dir.rename(moved)
        _ = output_dir.symlink_to(outside, target_is_directory=True)
        return original_materialize(verified, output_root_fd)

    monkeypatch.setattr(cli_module, "materialize_cache", swap_then_materialize)

    # When
    result = cli_module.run_inspect(MANIFEST_PATH, output_dir, PROJECT_ROOT)

    # Then
    assert result.overall == "FAIL"
    assert sentinel.read_bytes() == original_bytes
    assert not (outside / "inspect-report.json").exists()
    assert '"overall":"FAIL"' in (moved / "inspect-report.json").read_text(
        encoding="utf-8",
    )
