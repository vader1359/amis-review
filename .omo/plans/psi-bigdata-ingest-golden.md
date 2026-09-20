---
slug: psi-bigdata-ingest-golden
status: active
parent_plan: psi-bigdata-lean-v1
delivery: direct
task_count: 5
---

# PSI explicit schema + multi-source golden parity

## Outcome

Deliver the first production checkpoint of Lean V1: a strict local Python package that parses an explicit manifest, reads the six sanitized PSI sample workbooks into seven projected/typed relations through Calamine/fastexcel + Polars, materializes content-addressed Parquet, and exposes `psi inspect` with a deterministic parity report.

This slice does not implement PSI business transforms, Manual Check actions, 17-sheet workbook generation, Final release, web/auth/database/DuckDB, deployment, commit, push, or writes to source workbooks.

The user's `làm đi` approves the parent plan's recommended contract defaults for later rule work: aggregate signed inventory before availability filtering; carry-forward requires a flag, hash, and reason; permanent exclusions do not auto-expire without an explicit replacement. This slice records but does not execute those business rules.

## Source set

- `PSI_SAMPLE_INPUT/CRM_Sale_sample.xlsx`: `Danh sách` and `Bảng hàng hóa`.
- `PSI_SAMPLE_INPUT/Product_master_sample.xlsx`: `Danh sách`.
- `PSI_SAMPLE_INPUT/Sales_detail_MISA_sample.xlsx`: `SỔ CHI TIẾT BÁN HÀNG`.
- `PSI_SAMPLE_INPUT/Inventory_sample.xlsx`: `TỔNG HỢP TỒN KHO`.
- `PSI_SAMPLE_INPUT/Purchase_PO_sample.xlsx`: `LDL` only.
- `PSI_SAMPLE_INPUT/Target_sample.xlsx`: `Target`.

No row values or PII may be written to the ledger/evidence. Exact file hashes, schema names, row counts, aggregate null counts, and timings are permitted.

## TODOs

### Wave 1 — Contract and foundation

- [x] **C1 — Explicit source contract and golden manifest**
  - Own: `docs/psi_tool_v1/contract.md`, `src/psi_tool/contracts.py`, `tests/psi_tool/fixtures/golden_manifest.toml`, `tests/psi_tool/test_contracts.py`.
  - Parse manifest at the trust boundary into frozen Pydantic models.
  - Lock seven relation roles, exact paths, sheets, zero-based header rows, explicit projected columns/dtypes, expected source hashes, expected data shapes, schema version, `as_of`, and carry-forward metadata.
  - Fail closed on missing file, hash drift, missing/duplicate header, invalid header row, absent carry-forward reason/hash, or unknown relation role.
  - Acceptance: characterization test passes before production change; new contract tests are observed red then green; no source read writes.

- [x] **C2 — Strict uv package foundation**
  - Own: `pyproject.toml`, `uv.lock`, `src/psi_tool/__init__.py`, `src/psi_tool/__main__.py`, package/test configuration only.
  - Preserve existing `test/` suite while adding `tests/psi_tool/`; Python 3.13+, uv, NumPy, PyArrow, Polars, fastexcel, Pydantic v2, Typer, Rich, pytest, Ruff, basedpyright-all.
  - Expose a package entrypoint named `psi`; no web/database dependencies.
  - Acceptance: `uv sync --locked`, import smoke, Ruff configuration, and basedpyright-all configuration pass without changing existing requirements or legacy tests.

### Wave 2 — Typed ingest and cache

- [x] **C3 — Seven explicit XLSX adapters and content-addressed Parquet cache**
  - Depends on C1 and C2.
  - Own: `src/psi_tool/ingest.py`, `src/psi_tool/cache.py`, `tests/psi_tool/test_ingest.py`.
  - Use Calamine/fastexcel with explicit header row, projection and dtype contract; never pandas, fuzzy headers, auto-latest discovery, Python bulk row loops, or JSON row handoff.
  - Cache identity includes source SHA-256, relation role, contract version, projection, and schema version.
  - Emit one Parquet per relation plus typed metadata: relation hash, schema, rows, columns, null counts, cache hit/miss.
  - Acceptance: all seven relations materialize from sanitized sources; second run is a cache hit with identical hashes; malformed/hash-drift cases fail closed; source hashes remain unchanged.

### Wave 3 — Real CLI and parity surface

- [x] **C4 — `psi inspect` deterministic golden-parity report**
  - Depends on C3.
  - Own: `src/psi_tool/cli.py`, `src/psi_tool/report.py`, the C2-to-C4 wiring seam in `src/psi_tool/__main__.py`, `tests/psi_tool/test_cli.py`, `tests/psi_tool/test_e2e.py`.
  - `psi inspect --manifest PATH --output-dir NEW_DIR` creates only cache Parquet plus `inspect-report.json` in a new run directory.
  - Report contains manifest/contract/source/relation hashes, expected-versus-actual shapes and schemas, cache status, phase timings, and overall PASS/FAIL; exclude raw rows, absolute source paths, and timestamps from semantic hash.
  - Invalid input exits non-zero and never emits a PASS report. A repeated invocation against the same cache proves stable semantic hashes.
  - Acceptance: one real CLI happy path and one malformed/hash-drift error path are captured through a subprocess E2E.

## Final Verification Wave

- [x] **C5 — Independent adversarial QA, evidence, and checkpoint handoff**
  - Depends on C4.
  - Run targeted/full relevant tests, Ruff, formatting, basedpyright-all, no-excuse, pure-LOC checks, source-hash readback, and real CLI twice (cold + cache hit).
  - Probe malformed input, stale cache, dirty worktree isolation, misleading success output, long-command handling, test determinism, and interrupted run cleanup; mark unrelated classes explicitly not applicable.
  - Independent verifier must confirm the worker DoneClaim before completion.
  - Write redacted evidence under `.omo/evidence/psi-bigdata-ingest-golden/` and append ledger entries under `.omo/start-work/ledger.jsonl`.

## Completion gate

```bash
rtk proxy uv sync --locked
rtk proxy uv run ruff check src tests
rtk proxy uv run ruff format --check src tests
rtk proxy uv run basedpyright
rtk proxy uv run pytest tests/psi_tool -q
rtk proxy uv run psi inspect --manifest tests/psi_tool/fixtures/golden_manifest.toml --output-dir <new-run-dir>
```

Checkpoint completion requires seven relations, deterministic hashes, cache-hit proof, no source mutation, independent verification, cleanup receipt, and a concise record of the unrelated legacy Manual Check fixture drift if the full repository suite is also run.
