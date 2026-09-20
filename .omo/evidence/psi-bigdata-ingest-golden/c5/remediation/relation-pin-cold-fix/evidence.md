# Cold relation-pin remediation evidence

## Scope and changed files

- `src/psi_tool/cache.py`: validates the computed cold semantic hash against the
  immutable manifest pin before writing any Parquet file.
- `src/psi_tool/cli.py`: derives command outcome from `report.overall` instead of
  returning a hardcoded PASS.
- `tests/psi_tool/test_relation_pin_enforcement.py`: cold, warm, and report/result
  regressions.
- `tests/psi_tool/test_e2e.py`: public CLI wrong-pin failure and no-output scenario.

No descriptor-safe output publication or signal-handling code was changed.

## Red reproduction

Invocation:

```text
rtk uv run pytest tests/psi_tool/test_relation_pin_enforcement.py -q
```

Before the fix:

```text
FAILED test_cold_cache_rejects_wrong_relation_pin_before_publication
Failed: DID NOT RAISE CacheIntegrityError

FAILED test_failed_report_cannot_produce_pass_result
AssertionError: assert 'PASS' == 'FAIL'

2 failed, 1 passed in 55.29s
```

This independently reproduced both confirmed defects. The warm wrong-pin scenario
already rejected the mismatch.

## Green focused scenarios

Invocation:

```text
rtk uv run pytest tests/psi_tool/test_relation_pin_enforcement.py -q
3 passed in 43.05s
```

Binary observables:

- Cold wrong pin raises `CacheIntegrityError` containing the sanitized trusted
  manifest message.
- The requested cache root does not exist after failure.
- No `.cache-*.tmp` staging directory remains.
- A warm cache arranged under the wrong manifest-derived key rejects the actual
  semantic hash before accepting embedded metadata.
- A FAIL report produces `_InspectResult.overall == "FAIL"` and cannot become PASS.

Integrated invocation:

```text
rtk uv run pytest tests/psi_tool/test_relation_pin_enforcement.py \
  tests/psi_tool/test_e2e.py::test_inspect_real_cold_then_warm_cache_is_stable \
  tests/psi_tool/test_e2e.py::test_inspect_wrong_relation_pin_fails_without_first_run_output \
  tests/psi_tool/test_cache_failures.py::test_warm_cache_rejects_self_consistent_metadata_tamper \
  tests/psi_tool/test_verified_manifest.py -q
9 passed in 102.53s
```

This proves correct cold/warm PASS behavior, public CLI wrong-pin nonzero exit with
exact sanitized stderr and no first-run output, warm self-consistent tamper rejection,
and preservation of one-read/no-CWD/concurrent-workspace behavior. No full suite was
run, per the bounded follow-up instruction.

## Strict gates

```text
rtk uv run ruff check <4 changed Python files>
All checks passed!

rtk uv run ruff format --check <4 changed Python files>
4 files already formatted

rtk uv run basedpyright <4 changed Python files>
0 errors, 0 warnings, 0 notes

rtk uv run check-no-excuse-rules.py <4 changed Python files>
no violations in 4 file(s)
```

Pure LOC:

```text
src/psi_tool/cache.py 195
src/psi_tool/cli.py 168
tests/psi_tool/test_relation_pin_enforcement.py 75
tests/psi_tool/test_e2e.py 201
```

All changed Python files are at or below the 250 pure-LOC ceiling.
