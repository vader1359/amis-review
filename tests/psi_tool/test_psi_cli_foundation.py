from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_psi_help_is_a_deterministic_public_surface() -> None:
    # Given
    command = ["psi", "--help"]

    # When
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    # Then
    assert completed.returncode == 0, completed.stderr
    assert "Usage: psi" in completed.stdout
    assert "inspect" in completed.stdout


def test_psi_inspect_help_reserves_the_subcommand_without_running_ingest() -> None:
    # Given
    command = ["psi", "inspect", "--help"]

    # When
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    # Then
    assert completed.returncode == 0, completed.stderr
    assert "Usage: psi inspect" in completed.stdout
