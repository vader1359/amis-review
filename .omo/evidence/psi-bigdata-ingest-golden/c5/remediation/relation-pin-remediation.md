# C5 relation-pin remediation

## Implemented

- Manifest contract version 1.1 requires `psi-semantic-string-v1` and seven literal expected relation SHA-256 values.
- Cache format v2 includes the expected relation digest in its key and rejects cold or warm content whose independently computed semantic digest differs from the manifest pin.
- Report format v2 publishes expected and actual relation digests; parity requires equality and the report semantic digest covers both.
- The contract documents the exact trust boundary: cache/output are untrusted, PASS is consistency with an externally trusted manifest, not a digital signature.

## Observable scenarios

1. Self-consistent tamper: modify a same-shape String Parquet relation and update its embedded `psi.relation_hash`. Invocation: `uv run pytest tests/psi_tool/test_cache_failures.py::test_warm_cache_rejects_self_consistent_metadata_tamper -q`. Observable: `1 passed in 6.13s`; warm validation raises the trusted-manifest integrity error.
2. Contract/report regression: `uv run pytest tests/psi_tool/test_contracts.py tests/psi_tool/test_e2e.py::test_inspect_real_cold_then_warm_cache_is_stable tests/psi_tool/test_cache_failures.py::test_warm_cache_rejects_self_consistent_metadata_tamper -q`. Observable: `13 passed in 25.03s`.
3. Static gates: `uv run ruff check src/psi_tool tests/psi_tool`, `uv run ruff format --check src/psi_tool tests/psi_tool`, `uv run basedpyright`. Observable: all checks passed, 20 files formatted, 0 errors/warnings/notes.

## Incomplete blockers

Immutable `VerifiedManifest`, no-CWD/reentrant execution, descriptor-bound output publication/cleanup, and controlled SIGINT/SIGTERM behavior were not completed in this bounded attempt. A final full-suite rerun entered a job-control stopped state, was resumed, then terminated by the executor after more than four minutes without output; it is not claimed green. No database, web, business-transform, workbook, plan, ledger, status, commit, or push action occurred.
