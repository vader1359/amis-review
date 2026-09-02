# Copyright 2026 PSI Tool contributors
from __future__ import annotations

import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from psi_tool.contracts import load_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "tests/psi_tool/fixtures/golden_manifest.toml"


@dataclass(frozen=True, slots=True)
class _ReportSummary:
    overall: str
    semantic_sha256: str
    cache_hits: tuple[bool, ...]


def _independent_json_summary(path: Path) -> _ReportSummary:
    line_break = "\n"
    script = line_break.join(
        (
            "import hashlib, json, sys",
            "from pathlib import Path",
            "payload=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))",
            "relations=[]",
            "for item in payload['relations']:",
            "  actual=[item['actual']['shape'],item['actual']['schema']]",
            "  expected=[item['expected']['shape'],item['expected']['schema']]",
            "  entry={}",
            "  entry['actual']=actual",
            "  entry['expected']=expected",
            "  entry['relation_hash']=item['relation_hash']",
            "  entry['expected_relation_hash']=item['expected_relation_hash']",
            "  entry['relation_id']=item['relation_id']",
            "  relations.append(entry)",
            "canonical={}",
            "canonical['contract_version']=payload['contract_version']",
            "canonical['manifest_sha256']=payload['manifest']['sha256']",
            "canonical['overall']=payload['overall']",
            "canonical['relations']=relations",
            "canonical['report_version']=payload['report_version']",
            "canonical['schema_version']=payload['schema_version']",
            "canonical['source_hashes']=payload['manifest']['source_sha256']",
            "options={}",
            "options['ensure_ascii']=False",
            "options['separators']=(',',':')",
            "options['sort_keys']=True",
            "encoded=json.dumps(canonical,**options)",
            "actual_hash=hashlib.sha256(encoded.encode()).hexdigest()",
            "assert actual_hash==payload['semantic_sha256']",
            "print(payload['overall'])",
            "print(payload['semantic_sha256'])",
            "hits=[]",
            "for item in payload['relations']:",
            "  hits.append('1' if item['cache_hit'] else '0')",
            "print(','.join(hits))",
        ),
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    overall, semantic_sha256, cache_hits = completed.stdout.splitlines()
    return _ReportSummary(
        overall=overall,
        semantic_sha256=semantic_sha256,
        cache_hits=tuple(value == "1" for value in cache_hits.split(",")),
    )


def _run_inspect(
    output_dir: Path,
    manifest: Path = MANIFEST_PATH,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "psi_tool",
            "inspect",
            "--manifest",
            str(manifest),
            "--output-dir",
            str(output_dir),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _parquet_state(cache_dir: Path) -> tuple[tuple[str, str, int], ...]:
    return tuple(
        (
            path.name,
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_mtime_ns,
        )
        for path in sorted(cache_dir.glob("*.parquet"))
    )


def test_inspect_real_cold_then_warm_cache_is_stable(tmp_path: Path) -> None:
    # Given
    output_dir = tmp_path / "run"

    # When
    cold = _run_inspect(output_dir)
    cold_payload = _independent_json_summary(output_dir / "inspect-report.json")
    before = _parquet_state(output_dir / "cache")
    warm = _run_inspect(output_dir)
    warm_payload = _independent_json_summary(output_dir / "inspect-report.json")

    # Then
    assert cold.returncode == warm.returncode == 0
    assert "PASS report=inspect-report.json" in cold.stdout
    assert len(tuple((output_dir / "cache").glob("*.parquet"))) == 7
    assert cold_payload.overall == warm_payload.overall == "PASS"
    assert cold_payload.semantic_sha256 == warm_payload.semantic_sha256
    assert cold_payload.cache_hits == (False,) * 7
    assert warm_payload.cache_hits == (True,) * 7
    assert _parquet_state(output_dir / "cache") == before


def test_inspect_replaces_stale_pass_with_fail_for_corrupt_warm_cache(
    tmp_path: Path,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    assert _run_inspect(output_dir).returncode == 0
    target = next((output_dir / "cache").glob("*.parquet"))
    _ = target.write_bytes(target.read_bytes()[:-16])

    # When
    completed = _run_inspect(output_dir)
    payload = _independent_json_summary(output_dir / "inspect-report.json")

    # Then
    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    assert str(PROJECT_ROOT) not in completed.stderr
    assert payload.overall == "FAIL"
    assert not tuple(output_dir.glob(".*.tmp"))


def test_inspect_rejects_foreign_output_without_creating_report(tmp_path: Path) -> None:
    # Given
    output_dir = tmp_path / "foreign"
    output_dir.mkdir()
    _ = (output_dir / "foreign.txt").write_text("foreign", encoding="utf-8")

    # When
    completed = _run_inspect(output_dir)

    # Then
    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    assert not (output_dir / "inspect-report.json").exists()
    assert not (output_dir / "cache").exists()


def test_inspect_rejects_traversal_output_without_creating_artifacts(
    tmp_path: Path,
) -> None:
    # Given
    traversal_output = tmp_path / "safe" / ".." / "run"

    # When
    completed = _run_inspect(traversal_output)

    # Then
    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    assert not (tmp_path / "run").exists()


def test_inspect_malformed_manifest_does_not_create_first_run_output(
    tmp_path: Path,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    malformed = tmp_path / "bad.toml"
    _ = malformed.write_text("schema_version = [", encoding="utf-8")

    # When
    completed = _run_inspect(output_dir, malformed)

    # Then
    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    assert not output_dir.exists()


def test_inspect_hash_drift_manifest_does_not_create_first_run_output(
    tmp_path: Path,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    drifted_manifest = tmp_path / "drifted.toml"
    original = MANIFEST_PATH.read_text(encoding="utf-8")
    drifted = original.replace(
        "d3c7ddb0835d3ec12c52d50a34e96ca57f5a5126f2d531cc35173213e0fe3c4d",
        "0" * 64,
        1,
    )
    _ = drifted_manifest.write_text(drifted, encoding="utf-8")

    # When
    completed = _run_inspect(output_dir, drifted_manifest)

    # Then
    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    assert not output_dir.exists()


def test_inspect_wrong_relation_pin_fails_without_first_run_output(
    tmp_path: Path,
) -> None:
    # Given
    output_dir = tmp_path / "run"
    wrong_manifest = tmp_path / "wrong-pin.toml"
    original = MANIFEST_PATH.read_text(encoding="utf-8")
    first_pin = "a8da7cd3326448ced75f89412db8167619cbf0a48aa6020c56dfa4ed0a9e279a"
    _ = wrong_manifest.write_text(
        original.replace(first_pin, "0" * 64, 1),
        encoding="utf-8",
    )

    # When
    completed = _run_inspect(output_dir, wrong_manifest)

    # Then
    assert completed.returncode != 0
    assert completed.stderr.splitlines() == ["inspect failed: validation_failed"]
    assert "Traceback" not in completed.stderr
    assert not output_dir.exists()


def test_inspect_does_not_mutate_six_manifest_sources(tmp_path: Path) -> None:
    # Given
    manifest = load_manifest(MANIFEST_PATH, PROJECT_ROOT)
    source_files = tuple(
        PROJECT_ROOT / source.relative_path for source in manifest.sources
    )
    before = tuple(
        (path.name, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in source_files
    )

    # When
    completed = _run_inspect(tmp_path / "run")

    # Then
    after = tuple(
        (path.name, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in source_files
    )
    assert completed.returncode == 0
    assert len(before) == len(after) == 6
    assert before == after
