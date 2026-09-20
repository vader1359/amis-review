# VerifiedManifest independent verification

> Historical first-pass rejection. The defect was remediated and independently
> re-verified. Current verdict: VERIFIED in `reverification.md`.

## Verdict

REJECTED for this batch because the requested preservation of external
relation-pin enforcement is broken on a cold cache. The immutable
`VerifiedManifest` / no-CWD portion itself is verified. Overall C5 also remains
blocked on the separately queued output-lifecycle TOCTOU and signal handling
work, which were outside this narrow review.

## Verified behavior

- `load_verified_manifest` reads the manifest once as bytes; those same bytes
  feed `tomllib` and SHA-256. It captures an explicit resolved workspace root,
  validates source identities, and returns frozen typed `VerifiedManifest`,
  `SourceManifest`, and `ResolvedSourceIdentity` values.
- Production search found no `os.chdir` or `getcwd`. The only `Path.cwd()` is
  the CLI boundary capture at `src/psi_tool/cli.py:70`. Downstream cache,
  ingest, and report APIs receive `VerifiedManifest` and contain no manifest
  path or manifest reload.
- Mutating a manifest file after verification did not change cache/report
  identity: an independent cold-cache probe produced seven relations, PASS,
  and the SHA of the original byte snapshot.
- Two-root concurrent verification with `os.chdir` monkeypatched to fail,
  malformed/drifted inputs, renamed header failure, and a self-consistent warm
  cache tamper all passed their targeted tests with sanitized failure behavior.
- The fixture contains exactly seven literal 64-hex
  `expected_relation_sha256` pins and declares
  `psi-semantic-string-v1`. Report/cache v2 structures expose expected and
  actual relation hashes.
- No `Any`, `cast`, type-ignore, pyright-ignore, broad exception, pandas,
  DuckDB, database, web-client, or web-framework usage was found in product or
  tests. Every changed Python file is at or below 250 pure LOC; maximum is
  `_contract_models.py` at 226 (warning band).

## Blocking finding

### Cold-cache relation pin is not enforced and CLI reports PASS for a FAIL report

- Violated criterion: preserve external relation-pin/cache/report v2 behavior;
  trusted relation pins must reject mismatched decoded content on cold and warm
  paths.
- Evidence: `src/psi_tool/cache.py:182-195` computes and writes cold metadata
  without comparing `metadata.relation_hash` to
  `context.relation.expected_relation_sha256`. The equivalent check exists only
  on warm reads at `src/psi_tool/cache.py:215-218`.
- Independent probe replaced the first trusted pin with 64 zeros while keeping
  the validated source unchanged. `materialize_cache` completed and printed:

  ```text
  cold_wrong_pin_rejected=False
  actual=a8da7cd3326448ced75f89412db8167619cbf0a48aa6020c56dfa4ed0a9e279a expected=0000000000000000000000000000000000000000000000000000000000000000
  ```

  The probe assertion failed, proving the cold path accepted the mismatch.
- A second public-command probe used a valid TOML manifest with that wrong pin.
  `run_inspect` printed:

  ```text
  command_overall=PASS report_overall=FAIL report_published=True
  ```

  This follows directly from `src/psi_tool/cli.py:109-115`, where the report is
  built but `_InspectResult("PASS", report, ...)` is returned unconditionally.
- Required remediation: fail closed before publishing the cold cache when any
  computed relation hash differs from its trusted manifest pin, and derive the
  command result from the report/integrity outcome rather than hardcoding PASS.
  Add a cold wrong-pin regression test; the existing self-consistent tamper test
  covers only warm reads.

## Commands and outcomes

```text
rtk test uv run pytest -q tests/psi_tool/test_verified_manifest.py \
  tests/psi_tool/test_cache_failures.py::test_warm_cache_rejects_self_consistent_metadata_tamper \
  tests/psi_tool/test_cache_failures.py::test_load_relation_rejects_renamed_projected_header \
  tests/psi_tool/test_e2e.py::test_inspect_malformed_manifest_does_not_create_first_run_output \
  tests/psi_tool/test_e2e.py::test_inspect_hash_drift_manifest_does_not_create_first_run_output
7 passed in 72.11s

rtk test uv run ruff check src/psi_tool tests/psi_tool
All checks passed

rtk test uv run ruff format --check src/psi_tool tests/psi_tool
21 files already formatted

rtk test uv run basedpyright src/psi_tool tests/psi_tool
0 errors, 0 warnings, 0 notes

rtk test uv run python .../check-no-excuse-rules.py <13 changed Python files>
no violations in 13 file(s)
```

The no-excuse script run over all 21 files additionally reports two pre-existing
mutable-dataclass findings in `_contract_errors.py`; that file is outside this
VerifiedManifest batch. The exact changed-file gate is green.

## Residual C5 blockers outside this batch

Output publication/cleanup still has the previously identified ancestor-symlink
and replacement TOCTOU exposure, and real SIGINT/SIGTERM cleanup/exit behavior is
still unremediated. They do not change this narrow verdict but continue to block
overall C5 approval.
