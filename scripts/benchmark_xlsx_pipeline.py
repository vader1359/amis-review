#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "fastexcel>=0.18",
#     "numpy>=2",
#     "polars>=1.35",
#     "pyarrow>=20",
#     "typer>=0.16",
# ]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run scripts/benchmark_xlsx_pipeline.py --input FILE.xlsx --sheet SHEET --output-dir RUN_DIR
# 3. Or make executable and run:
#      chmod +x scripts/benchmark_xlsx_pipeline.py && ./scripts/benchmark_xlsx_pipeline.py --help
# ──────────────────

from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final

import numpy as np
import polars as pl
import typer

REPORT_NAME: Final = "benchmark-report.json"
PARQUET_NAME: Final = "source.parquet"
HASH_CHUNK_BYTES: Final = 1024 * 1024


@dataclass(frozen=True, slots=True)
class BenchmarkSpec:
    source: Path
    sheet: str
    header_row: int
    output_dir: Path
    runs: int


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    source_sha256: str
    source_bytes: int
    sheet: str
    header_row: int
    rows: int
    columns: int
    parquet_sha256: str
    parquet_bytes: int
    xlsx_read_seconds: float
    parquet_write_seconds: float
    warm_read_seconds: tuple[float, ...]
    warm_median_seconds: float
    parity: bool
    peak_rss_bytes: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_xlsx(spec: BenchmarkSpec) -> tuple[pl.DataFrame, float]:
    started = time.perf_counter()
    frame = pl.read_excel(
        source=spec.source,
        sheet_name=spec.sheet,
        engine="calamine",
        read_options={"header_row": spec.header_row},
    )
    return frame, time.perf_counter() - started


def write_parquet(frame: pl.DataFrame, path: Path) -> float:
    started = time.perf_counter()
    frame.write_parquet(path, compression="zstd", statistics=True)
    return time.perf_counter() - started


def replay_parquet(
    expected: pl.DataFrame,
    path: Path,
    runs: int,
) -> tuple[tuple[float, ...], bool]:
    timings: list[float] = []
    warmup = pl.scan_parquet(path).collect(engine="streaming")
    parity = warmup.equals(expected)
    for _ in range(runs):
        started = time.perf_counter()
        replayed = pl.scan_parquet(path).collect(engine="streaming")
        timings.append(time.perf_counter() - started)
        parity = parity and replayed.equals(expected)
    return tuple(timings), parity


def peak_rss_bytes() -> int:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    scale = 1 if sys.platform.startswith("darwin") else 1024
    return int(rss * scale)


def write_report(report: BenchmarkReport, path: Path) -> None:
    payload = {
        "source_sha256": report.source_sha256,
        "source_bytes": report.source_bytes,
        "sheet": report.sheet,
        "header_row": report.header_row,
        "rows": report.rows,
        "columns": report.columns,
        "parquet_sha256": report.parquet_sha256,
        "parquet_bytes": report.parquet_bytes,
        "xlsx_read_seconds": report.xlsx_read_seconds,
        "parquet_write_seconds": report.parquet_write_seconds,
        "warm_read_seconds": report.warm_read_seconds,
        "warm_median_seconds": report.warm_median_seconds,
        "parity": report.parity,
        "peak_rss_bytes": report.peak_rss_bytes,
    }
    _ = path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def run_benchmark(spec: BenchmarkSpec) -> BenchmarkReport:
    spec.output_dir.mkdir(parents=True, exist_ok=False)
    source_hash = sha256_file(spec.source)
    frame, xlsx_seconds = read_xlsx(spec)
    parquet_path = spec.output_dir / PARQUET_NAME
    parquet_seconds = write_parquet(frame, parquet_path)
    warm_seconds, parity = replay_parquet(frame, parquet_path, spec.runs)
    report = BenchmarkReport(
        source_sha256=source_hash,
        source_bytes=spec.source.stat().st_size,
        sheet=spec.sheet,
        header_row=spec.header_row,
        rows=frame.height,
        columns=frame.width,
        parquet_sha256=sha256_file(parquet_path),
        parquet_bytes=parquet_path.stat().st_size,
        xlsx_read_seconds=xlsx_seconds,
        parquet_write_seconds=parquet_seconds,
        warm_read_seconds=warm_seconds,
        warm_median_seconds=float(
            np.median(np.asarray(warm_seconds, dtype=np.float64))
        ),
        parity=parity,
        peak_rss_bytes=peak_rss_bytes(),
    )
    write_report(report, spec.output_dir / REPORT_NAME)
    return report


def main(
    input_path: Annotated[
        Path,
        typer.Option(
            "--input",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    sheet: Annotated[str, typer.Option("--sheet")],
    output_dir: Annotated[
        Path, typer.Option("--output-dir", file_okay=False, resolve_path=True)
    ],
    header_row: Annotated[int, typer.Option("--header-row", min=0)] = 0,
    runs: Annotated[int, typer.Option("--runs", min=1, max=20)] = 3,
) -> None:
    """Benchmark XLSX materialization and lazy Parquet replay."""
    report = run_benchmark(
        BenchmarkSpec(input_path, sheet, header_row, output_dir, runs)
    )
    typer.echo(
        " ".join(
            (
                f"rows={report.rows} columns={report.columns}",
                f"xlsx={report.xlsx_read_seconds:.6f}s",
                f"warm_median={report.warm_median_seconds:.6f}s",
                f"parity={str(report.parity).lower()}",
                f"report={output_dir / REPORT_NAME}",
            )
        )
    )


if __name__ == "__main__":
    typer.run(main)
