# C5 independent output/signals gate

Verdict: **REJECTED**

- HEAD: `3e686be94834e343e3018bce1ddc69d20fa5957d`
- Product snapshot method: `shasum -a 256 pyproject.toml uv.lock src/psi_tool/*.py tests/psi_tool/*.py tests/psi_tool/fixtures/golden_manifest.toml docs/psi_tool_v1/contract.md | shasum -a 256`
- Product snapshot: `021e34de4b899885543358745c548c4b4c3e7043f01a3a6a35c182daa91b480d`

## Blocking findings

### 1. Parent descriptor acquisition has an ancestor-swap TOCTOU

`_validated_lexical_output()` checks each lexical ancestor with `lstat`, but
`open_output_session()` subsequently opens the complete parent path with one
`os.open(parent, O_DIRECTORY | O_NOFOLLOW)`. `O_NOFOLLOW` protects only the
final path component; a writable ancestor can be replaced after validation and
before this open.

An independent deterministic driver replaced `base/ancestor` with a symlink to
`outside` immediately before the parent `os.open`. The production call then
created its private `.run-*.tmp` under `outside/parent`, not under the validated
original parent:

```text
redirected_stage True
original_parent_stage False
```

This violates the required descriptor-anchored final parent boundary. The
parent must be reached by component-wise descriptor walking with no-follow and
identity checks, or an equivalent primitive that cannot traverse a swapped
ancestor.

Evidence pointer: `src/psi_tool/_output_lifecycle.py:137-177`.

### 2. Strict formatting gate is red

`uv run ruff check src/psi_tool tests/psi_tool` passes, but
`uv run ruff format --check src/psi_tool tests/psi_tool` reports
`tests/psi_tool/test_cli.py:161` would be reformatted: 1 unformatted file and
27 formatted files.

### 3. Obsolete path-based production surfaces remain callable

The public `psi_tool.cache.materialize_cache()` still uses path-based
`tempfile.mkdtemp`, `Path.replace`, and `shutil.rmtree`; the public
`report.write_report_atomic()` still uses a path-based temporary file and
`Path.replace`. The CLI correctly imports `_fd_cache.materialize_cache_at` and
`write_report_atomic_at`, so the tested CLI path is descriptor-relative, but
the package still exposes production path fallbacks contrary to the requested
no-backdoor gate.

Evidence pointers: `src/psi_tool/cache.py:83-125`,
`src/psi_tool/report.py:119-136`.

## Passing evidence

- Focused lifecycle/signal/pin/manifest suite: **15 passed in 175.01s**.
- This includes real new-session/process-group SIGINT and SIGTERM with exact
  exits 130/143, sanitized `inspect cancelled`, no cold final root, and zero
  `.run-*.tmp`; second signal during cleanup is ignored.
- Adversarial destination-appears, lexical symlink, renamed stage plus planted
  symlink, and warm final-name swap tests pass. External sentinels remain
  byte-identical and no cache/report escapes through the tested names.
- Fresh real CLI cold then warm: exit 0/0, stable semantic SHA
  `8a3437cd8392c9d56c01113f0ee693376a54512a86d1f092880a819595ca9955`,
  exact tree of seven Parquets plus `inspect-report.json`, 7 relations, 7 warm
  hits, and all actual relation hashes equal manifest pins.
- Unsupported-runtime probe raises `OSError(ENOTSUP)` before rename; Darwin
  production publication calls `renameatx_np` with `RENAME_EXCL` and never
  falls back to precheck plus plain rename.
- `basedpyright src/psi_tool tests/psi_tool`: 0 errors, 0 warnings, 0 notes.
- No-excuse scan on ten remediation source/test files: no violations.
- All production/test Python files are below 250 pure LOC.
- Static scan found no `Any`, `cast`, type-ignore, blanket exception handler,
  pandas, DuckDB, database, web client, `/dev/fd`, or `chdir` in the verified
  CLI path.

## Documentation review

The residuals are accurately stated: manifest/source immutability during one
invocation, caller manifest is not authenticity, local resource exhaustion,
missing directory fsync/power-loss durability, and SIGKILL/native delayed
delivery. No documentation overclaim was found for those residuals.

## Test/slop review

The focused tests are behavior-oriented and relevant; no deletion-only,
requested-removal, tautological, or implementation-mirroring blocker was
found. The principal gap is that the existing symlink test covers a static
lexical symlink, not the validate-to-open ancestor swap reproduced above.

## Cleanup

All verifier-created CLI roots and ancestor-race directories were removed.
No process/session created by this verifier remains.
