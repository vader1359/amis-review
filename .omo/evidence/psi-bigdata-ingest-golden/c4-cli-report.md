# C4 CLI and deterministic parity report

## Outcome

`psi inspect --manifest PATH --output-dir DIR` now materializes the verified C3 cache in `DIR/cache/`, publishes an atomic redacted `DIR/inspect-report.json`, and gives one concise result line only after publication. Reusing an exact completed run root reads all seven cache relations as warm hits without rewriting Parquet bytes or mtimes. Handled invalid manifest, source/cache validation, traversal, symlink, foreign state, and report publication failures return nonzero and cannot leave a stale PASS report.

The report contains versions, manifest and source identities, ordered expected/actual schema and shapes, null counts, cache key/relation/Parquet hashes, cache status, monotonic materialization timing, overall result, and a semantic SHA-256. Its semantic hash omits timing, hit status, output path, mtime, wall clock, raw rows, and PII.

## Evidence ledger

| Scenario | Invocation | Binary observable | Captured artifact |
|---|---|---|---|
| Unit parity and redaction | `uv run pytest tests/psi_tool/test_cli.py -q` as part of the C4 suite | Cold and warm semantic hashes match; shape/schema order mismatch is FAIL; no absolute path or timestamp key | `c4/pytest-c4-repair.xml` (13 targeted C4 tests, 0 failures) |
| Real subprocess cold then warm | `uv run pytest tests/psi_tool/test_e2e.py -q` | Fresh run PASS with seven Parquets; repeat PASS with seven hits, same semantic hash, unchanged Parquet bytes/mtimes | `c4/pytest-e2e-repair.xml` (7 tests, 0 failures) |
| Manual public CLI cold then warm | `uv run psi inspect --manifest tests/psi_tool/fixtures/golden_manifest.toml --output-dir <temporary>/run` twice | Both exit 0/PASS; semantic SHA `c7a7f8c4878b0ae96fb8b1cf5a28151d097902b9cdd4b42d45da455881424fd2`; second report has 7 warm hits and independently re-derived SHA | This ledger; temporary run removed after verification |
| Regular-file output safety | Public subprocess against a pre-existing regular file | Nonzero; exactly one sanitized stderr line; no traceback/path/raw exception; file bytes unchanged and no temp residue | `c4/pytest-c4-repair.xml`; manual probe recorded in this ledger |
| Stale PASS resistance | Corrupt one warm Parquet then rerun public subprocess | Nonzero, sanitized stderr, report atomically replaced with `overall=FAIL`; no temp residue | `c4/pytest-c4-repair.xml` and manual probe in this ledger |
| Invalid first run | Malformed/hash-drift manifests, foreign output, and traversal output subprocess cases | Nonzero; no report/cache/root artifacts written for invalid first state | `c4/pytest-e2e-repair.xml` |
| Report write interruption | Monkeypatched atomic publisher during a newly-created run | FAIL; newly-created output root and temporary report absent | `c4/pytest-c4-repair.xml` |
| Source immutability | Hash all manifest-declared files after real CLI runs | 6 sources; every current SHA-256 equals manifest | This ledger, `c4/pytest-c4-repair.xml` |
| Programming/remove-ai-slops self-review | Explicit C4 source/test review after fresh behavior lock | No implementation-mirroring, tautology, deletion-only, or overfit defect remains | `c4/remove-ai-slops-self-review.md` |
| Static quality | Ruff, formatter, basedpyright, no-excuse on owned files | Ruff/format pass; basedpyright 0 errors; no-excuse 0 C4 violations | This ledger |

## Verification results

- `uv run pytest tests/psi_tool/test_cli.py tests/psi_tool/test_e2e.py -q --junitxml=.omo/evidence/psi-bigdata-ingest-golden/c4/pytest-c4-repair.xml`: 13 tests, 0 failures, 0 errors, 0 skipped, 196.15 seconds.
- Full C1–C4 package sweep: `uv run pytest tests/psi_tool -q --junitxml=.omo/evidence/psi-bigdata-ingest-golden/c4/pytest-psi-tool-repair.xml`: 40 tests, 0 failures, 0 errors, 0 skipped, 430.43 seconds.
- Public E2E after the repair: `uv run pytest tests/psi_tool/test_e2e.py -q --junitxml=.omo/evidence/psi-bigdata-ingest-golden/c4/pytest-e2e-repair.xml`: 7 tests, 0 failures, 0 errors, 0 skipped, 46.89 seconds.
- `uv sync --locked`, `uv run ruff check src tests`, `uv run ruff format --check src tests`, and C4-owned `uv run ruff check --select ALL ...`: pass.
- `uv run basedpyright`: 0 errors, 0 warnings, 0 notes.
- `check-no-excuse-rules.py` over C4-owned files: no violations in 7 files. Package-wide scan remains out of C4 scope because it reports pre-existing C1/C3 findings in `_contract_errors.py`, `_contract_models.py`, and `_workbook_validation.py`.
- `uv run psi --help` and `uv run psi inspect --help`: both exit 0 and display the expected command/options.

## Cleanup and residual risk

Fresh manual cold/warm, corrupt-warm, source-hash, and regular-file probes used private temporary roots and removed them after capture. No source workbook, manifest, C1/C3 adapter/cache logic, database, web code, or business rules changed. Atomic report replacement fsyncs the file before same-directory replace; power-loss durability of the containing directory itself is not simulated.
