from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def test_cli_materializes_parquet_when_xlsx_is_valid(tmp_path: Path) -> None:
    # Given
    source = (
        Path(__file__).resolve().parents[1] / "PSI_SAMPLE_INPUT" / "Target_sample.xlsx"
    )
    output_dir = tmp_path / "run"
    script = (
        Path(__file__).resolve().parents[1] / "scripts" / "benchmark_xlsx_pipeline.py"
    )

    # When
    completed = subprocess.run(
        [
            str(script),
            "--input",
            str(source),
            "--sheet",
            "Target",
            "--output-dir",
            str(output_dir),
            "--runs",
            "2",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    # Then
    assert completed.returncode == 0, completed.stderr
    report_text = (output_dir / "benchmark-report.json").read_text()
    source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    assert "rows=19 columns=9" in completed.stdout
    assert "parity=true" in completed.stdout
    assert '"rows": 19' in report_text
    assert '"columns": 9' in report_text
    assert '"sheet": "Target"' in report_text
    assert '"parity": true' in report_text
    assert f'"source_sha256": "{source_sha256}"' in report_text
    assert (output_dir / "source.parquet").stat().st_size > 0
