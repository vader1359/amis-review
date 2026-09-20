# VerifiedManifest independent re-verification

## Verdict

VERIFIED for the immutable `VerifiedManifest`, no-CWD, and external
relation-pin batch on product snapshot
`09deaaaf6cd00489453fb86a996101fa9db83139897c5b011b5946ce35fcb7fd`
(HEAD `3e686be94834e343e3018bce1ddc69d20fa5957d`).

Overall C5 remains blocked separately on the queued descriptor-safe output
lifecycle/TOCTOU and SIGINT/SIGTERM remediation. Those concerns were outside
this narrow re-verification.

## Prior rejection remediated

- Cold writes now compare the computed semantic relation hash with the trusted
  manifest pin before writing Parquet (`src/psi_tool/cache.py:182-199`).
- Warm reads retain the same trusted-pin comparison
  (`src/psi_tool/cache.py:202-227`).
- `run_inspect` returns `report.overall` rather than an unconditional PASS
  (`src/psi_tool/cli.py:109-115`).
- A dedicated regression module covers cold wrong-pin cleanup, warm wrong-pin
  rejection, and FAIL-report/result consistency.

## Independent behavioral evidence

### Public cold wrong-pin probe

A valid manifest was copied and its first external relation pin replaced with
64 zeros. The real `python -m psi_tool inspect` surface produced:

```text
exit=1
stdout=FAIL report=none semantic_sha256=04dda1e3ccc6dcfb68b3d97014910337667f09ee6a75b7502a06fd16f8a3bb03
stderr=inspect failed: validation_failed
output_exists=False
leftovers=()
```

The error contained no traceback or workspace path. Neither the requested final
output nor sibling/staging artifacts survived.

### Targeted regression tests

```text
rtk test uv run pytest -q \
  tests/psi_tool/test_relation_pin_enforcement.py \
  tests/psi_tool/test_verified_manifest.py \
  tests/psi_tool/test_cache_failures.py::test_warm_cache_rejects_self_consistent_metadata_tamper \
  tests/psi_tool/test_cache_failures.py::test_load_relation_rejects_renamed_projected_header \
  tests/psi_tool/test_ingest.py::test_materialize_cache_misses_then_hits_all_seven_relations \
  tests/psi_tool/test_e2e.py::test_inspect_malformed_manifest_does_not_create_first_run_output \
  tests/psi_tool/test_e2e.py::test_inspect_hash_drift_manifest_does_not_create_first_run_output
11 passed in 153.03s
```

This covers cold and warm wrong pins, self-consistent Parquet plus `psi.*`
tamper, FAIL-report/result consistency, correct seven-relation cold/warm cache,
one-read manifest identity, post-verification manifest mutation, concurrent
explicit roots with `os.chdir` patched to fail, malformed manifest, source hash
drift, and renamed projected-header failure.

## Static and quality gates

```text
rtk test uv run ruff check src/psi_tool tests/psi_tool
All checks passed

rtk test uv run ruff format --check src/psi_tool tests/psi_tool
22 files already formatted

rtk test uv run basedpyright src/psi_tool tests/psi_tool
0 errors, 0 warnings, 0 notes

rtk test uv run python .../check-no-excuse-rules.py <14 changed Python files>
no violations in 14 file(s)
```

Production search found no `os.chdir` or `getcwd`; the sole `Path.cwd()` is the
CLI boundary capture at `src/psi_tool/cli.py:70`. There is one manifest-byte
read in `contracts.py`; downstream cache/ingest/report receive the frozen
`VerifiedManifest` and do not reload or re-hash its path.

No typing `Any`, `typing.cast`, type-ignore, pyright-ignore, broad exception,
pandas, DuckDB, database, HTTP client, or web framework was found. The two
`.cast(...)` search hits are typed Polars expression casts. Every production and
test Python file is at most 250 pure LOC; the maximum changed production file is
`_contract_models.py` at 226, in the documented warning band. The manifest still
contains exactly seven literal 64-hex relation pins.

No full suite was run, per the bounded re-verification instruction. All verifier
temporary directories were managed by `TemporaryDirectory` and removed.
