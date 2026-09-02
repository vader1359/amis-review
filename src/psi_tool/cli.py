# Copyright 2026 PSI Tool contributors
"""Public Typer interface for redacted PSI cache inspection."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

import typer

from ._output_lifecycle import (
    OutputLifecycleError,
    OutputSession,
    open_output_session,
)
from ._signals import (
    InspectCancelled,
    controlled_signals,
    signals_ignored,
)
from .cache import CacheIntegrityError, CachePathError, materialize_cache
from .contracts import ManifestLoadError, SourceContractError, load_verified_manifest
from .ingest import IngestError
from .report import build_failure_report, build_inspect_report, write_report_atomic

if TYPE_CHECKING:
    from ._fd_types import DirectoryFd
    from ._report_models import InspectReport

app = typer.Typer(
    add_completion=False,
    help="PSI data inspection tooling.",
    name="psi",
    no_args_is_help=True,
)


@dataclass(frozen=True, slots=True)
class _InspectResult:
    overall: Literal["PASS", "FAIL"]
    report: InspectReport
    report_published: bool
    exit_code: int = 0


@app.callback()
def psi() -> None:
    """PSI data inspection tooling."""


@app.command()
def inspect(
    manifest: Annotated[Path, typer.Option("--manifest")],
    output_dir: Annotated[Path, typer.Option("--output-dir")],
) -> None:
    """Materialize or verify seven relations and write a redacted parity report."""
    result = run_inspect(manifest, output_dir, Path.cwd())
    report_location = "inspect-report.json" if result.report_published else "none"
    typer.echo(
        " ".join(
            (
                result.overall,
                f"report={report_location}",
                f"semantic_sha256={result.report.semantic_sha256}",
            ),
        ),
    )
    if result.exit_code:
        typer.echo("inspect cancelled", err=True)
        raise typer.Exit(code=result.exit_code)
    if result.overall == "FAIL":
        typer.echo("inspect failed: validation_failed", err=True)
        raise typer.Exit(code=1)


def main() -> None:
    """Run the public PSI command-line application."""
    app(prog_name="psi")


def run_inspect(
    manifest_path: Path,
    output_dir: Path,
    workspace_root: Path,
) -> _InspectResult:
    """Execute one descriptor-anchored inspect run."""
    failure = build_failure_report()
    session: OutputSession | None = None
    try:
        with controlled_signals() as cancellation:
            with cancellation.deferred():
                session = open_output_session(output_dir, workspace_root)
            session.invalidate_warm_report()
            verified = load_verified_manifest(manifest_path, workspace_root)
            started = time.perf_counter_ns()
            metadata = materialize_cache(verified, session.root_fd)
            report = build_inspect_report(
                verified,
                metadata,
                time.perf_counter_ns() - started,
            )
            if report.overall != "PASS":
                return _finish_failure(session, failure)
            write_report_atomic(session.root_fd, "inspect-report.json", report)
            with signals_ignored():
                session.verify_warm_identity()
                session.publish_cold()
            return _InspectResult("PASS", report, report_published=True)
    except InspectCancelled as cancelled:
        if session is not None:
            with signals_ignored():
                _cancel_session(session, failure)
        return _InspectResult(
            "FAIL",
            failure,
            report_published=False,
            exit_code=cancelled.exit_code,
        )
    except (
        CacheIntegrityError,
        CachePathError,
        IngestError,
        ManifestLoadError,
        OSError,
        OutputLifecycleError,
        SourceContractError,
    ):
        if session is None:
            return _InspectResult("FAIL", failure, report_published=False)
        return _finish_failure(session, failure)
    finally:
        if session is not None:
            session.close()


def _finish_failure(
    session: OutputSession,
    failure: InspectReport,
) -> _InspectResult:
    with signals_ignored():
        if session.is_warm:
            published = _publish_failure(session.root_fd, failure)
            return _InspectResult("FAIL", failure, published)
        session.cleanup()
        return _InspectResult("FAIL", failure, report_published=False)


def _cancel_session(session: OutputSession, failure: InspectReport) -> None:
    if session.is_warm:
        _ = _publish_failure(session.root_fd, failure)
    else:
        session.cleanup()


def _publish_failure(directory_fd: DirectoryFd, failure: InspectReport) -> bool:
    try:
        write_report_atomic(directory_fd, "inspect-report.json", failure)
    except OSError:
        try:
            os.unlink("inspect-report.json", dir_fd=directory_fd)
        except OSError:
            return False
        return False
    return True
