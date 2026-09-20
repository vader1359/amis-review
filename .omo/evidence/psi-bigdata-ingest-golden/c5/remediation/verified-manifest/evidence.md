# VerifiedManifest remediation evidence

## Scope

Implemented the immutable manifest boundary only. Descriptor-safe output publication
and signal handling were not changed in this batch.

Changed product files:

- `src/psi_tool/contracts.py`
- `src/psi_tool/_contract_models.py`
- `src/psi_tool/_workbook_validation.py`
- `src/psi_tool/cache.py`
- `src/psi_tool/ingest.py`
- `src/psi_tool/report.py`
- `src/psi_tool/cli.py`
- `docs/psi_tool_v1/contract.md`

Changed tests:

- `tests/psi_tool/test_verified_manifest.py`
- `tests/psi_tool/test_contracts.py`
- `tests/psi_tool/test_ingest.py`
- `tests/psi_tool/test_cache_failures.py`
- `tests/psi_tool/test_cli.py`
- `tests/psi_tool/test_e2e.py`

## Behavioral scenarios

1. Exact byte snapshot: monkeypatched `Path.read_bytes` returned different manifest
   bytes on a hypothetical second read. `load_verified_manifest` called it once;
   parsed contract version and SHA-256 both matched the first byte snapshot.
2. CWD isolation: two distinct workspace roots were verified concurrently while
   `os.chdir` was monkeypatched to raise. Both resolved to their own canonical root
   and returned the same immutable manifest SHA.
3. Frozen report identity: after manifest verification, the manifest file was
   changed. `build_inspect_report` emitted the SHA captured in `VerifiedManifest`,
   not a re-hash of the changed path.
4. Real CLI regression: cold/warm cache, corrupted cache, unsafe output, malformed
   manifest, source drift, and source immutability scenarios remained green.

## Test invocations and binary observables

```text
rtk uv run pytest tests/psi_tool/test_contracts.py tests/psi_tool/test_verified_manifest.py -q
14 passed in 115.62s

rtk uv run pytest tests/psi_tool/test_ingest.py tests/psi_tool/test_cache_failures.py tests/psi_tool/test_cli.py tests/psi_tool/test_verified_manifest.py -q
24 passed in 224.91s

rtk uv run pytest tests/psi_tool/test_e2e.py -q
7 passed in 56.46s
```

The three runs contain 45 passing test executions and 42 unique scenarios; the
three `VerifiedManifest` tests were intentionally repeated in the integrated batch.
No full repository suite was run, per the bounded batch instruction.

## Strict gates

```text
rtk uv run basedpyright src/psi_tool tests/psi_tool
0 errors, 0 warnings, 0 notes

rtk uv run ruff check <13 changed Python files>
All checks passed

rtk uv run ruff format --check <13 changed Python files>
13 files already formatted

rtk uv run check-no-excuse-rules.py <13 changed Python files>
no violations in 13 file(s)
```

The three exhaustive `Literal` matches retain `MATCH_OK` annotations because
basedpyright rejects an explicit unreachable case as an unnecessary comparison.
Ruff exits zero but reports those skill-specific pseudo-code annotations as unknown.

Pure LOC for every changed Python file is at most 250. The maximum is
`src/psi_tool/_contract_models.py` at 226; it is in the 200-250 warning band and
should be split before another material addition.

## Production search

```text
rtk grep -R "os\.chdir\|chdir(" -n src/psi_tool
exit 1; zero matches

rtk grep -R "Path\.cwd\|\.cwd()" -n src/psi_tool
src/psi_tool/cli.py:70: result = run_inspect(manifest, output_dir, Path.cwd())

rtk grep -R "read_bytes\|read_text\|sha256_file(manifest\|load_manifest\|load_verified_manifest" -n src/psi_tool
one manifest byte read at src/psi_tool/contracts.py:61
one CLI load at src/psi_tool/cli.py:99
compatibility load_manifest delegates to the same loader

rtk grep -R "manifest_path" -n src/psi_tool/cache.py src/psi_tool/ingest.py src/psi_tool/report.py
exit 1; zero matches
```

The only production `Path.cwd()` is the public CLI boundary capture. Cache,
ingest, and report receive `VerifiedManifest` and have no manifest path to reload.

## Residual assumption

The manifest and source tree must remain immutable for the duration of one
invocation. Source hash/open TOCTOU is documented and is not presented as an
authenticity guarantee.
