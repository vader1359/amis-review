# C2 strict uv package foundation evidence

Date: 2026-08-30

## Scope and cleanup receipt

- Owned changes: `pyproject.toml`, `uv.lock`, `src/psi_tool/__init__.py`,
  `src/psi_tool/__main__.py`, and `tests/psi_tool/test_psi_cli_foundation.py`.
- Removed only the provisional C2-owned `test/test_psi_cli_foundation.py` and
  provisional C2-owned `src/psi_tool/cli.py` after the parent clarified that
  C4 owns the latter.
- No source workbook, legacy test, requirements file, business transform,
  database, web/deploy file, or git history was modified by C2. No temporary
  files were created outside this evidence directory.
- The initial red test was captured before a `psi_tool` package existed; it
  failed for the expected boundary reason, not a test typo.
- Follow-up: a fresh C1 collection reproduction initially exited `2` with
  `ModuleNotFoundError: No module named 'psi_tool.contracts'`. C2 added
  `pythonpath = ["src"]` to pytest configuration. The initial configuration
  alone still failed because C2's prior empty `tests/psi_tool/__init__.py`
  shadowed the src-layout package, so C2 removed only that owned file and
  configured Ruff's test-only `INP001` exception instead.

## Contract result

`psi-tool` is a Python `>=3.13` src-layout package with a `psi` console
entrypoint to `psi_tool.__main__:main`. Runtime dependencies are exactly the
foundation/data set declared by the active C2 plan: fastexcel, NumPy, Polars,
Pydantic v2, PyArrow, Rich, and Typer. Development tooling is isolated in the
`dev` dependency group: pytest, Ruff, and basedpyright.

`psi --help` and `psi inspect --help` are deterministic Typer help surfaces.
`inspect` is a reserved command only; it does not invoke ingest logic. There
is deliberately no `src/psi_tool/cli.py`, which remains C4-owned.

## TDD evidence

| Scenario | Invocation | Binary observable | Result |
| --- | --- | --- | --- |
| Red: package does not yet exist | `uv run --with pytest pytest test/test_psi_cli_foundation.py -q` | exit `1`; 2 failed tests with `No module named psi_tool` | Observed before production package files |
| Green: public help surface | `uv run pytest tests/psi_tool/test_psi_cli_foundation.py -q` | exit `0`; `2 passed in 0.36s` | Fresh pass |

## Fresh verification

| Scenario | Invocation | Binary observable | Result |
| --- | --- | --- | --- |
| Lock consistency (stale-lock guard) | `uv lock --check` | exit `0`; resolver accepted lock | Fresh pass |
| Locked environment | `uv sync --locked` | exit `0`; `Checked 25 packages` | Fresh pass |
| C1 import/collection seam | `uv run pytest tests/psi_tool/test_contracts.py --collect-only -q` | exit `0`; `3 tests collected` | Fresh pass |
| C1 collection execution | `uv run pytest tests/psi_tool/test_contracts.py -q` | exit `0`; `3 passed in 0.14s` | Fresh pass |
| C2 Ruff ALL-select | `uv run ruff check src/psi_tool tests/psi_tool/test_psi_cli_foundation.py` | exit `0`; `All checks passed!` | Fresh pass |
| C2 formatting | `uv run ruff format --check src/psi_tool tests/psi_tool/test_psi_cli_foundation.py` | exit `0`; `4 files already formatted` | Fresh pass |
| C2 strict types | `uv run basedpyright src/psi_tool tests/psi_tool/test_psi_cli_foundation.py` | exit `0`; `0 errors, 0 warnings, 0 notes` | Fresh pass |
| Import smoke | `uv run python -c 'import psi_tool; from psi_tool.__main__ import app; print(...)'` | exit `0`; `import-ok version=0.1.0 commands=1` | Fresh pass |
| Root CLI manual QA | `uv run psi --help` | exit `0`; output includes `Usage: psi`, `inspect`, and no stderr | Fresh pass |
| Inspect CLI manual QA | `uv run psi inspect --help` | exit `0`; output includes `Usage: psi inspect` and no stderr | Fresh pass |
| C4 boundary | `test ! -e src/psi_tool/cli.py` | exit `0` | Fresh pass; no C4 implementation leaked into C2 |
| Runtime dependency leakage | `uv tree --no-dev` | exit `0`; only declared direct runtime roots and their transitive dependencies, no web/database package | Fresh pass |

## Global gates, freshly rerun

After the follow-up collection fix, all requested global static gates are
green: `uv sync --locked`, `uv run ruff check src test tests`, and
`uv run ruff format --check src test tests` exited `0` (`All checks passed!`;
`5 files already formatted`). `uv run basedpyright src test tests` also exited
`0` with `0 errors, 0 warnings, 0 notes`.

## Post-write review

- Each C2 source file has one responsibility: package metadata or Typer
  entrypoint. The test owns only external CLI help assertions.
- The package passes no untyped boundary values; there are no enums/variants,
  `Any`, `cast`, type-ignore comments, broad exceptions, or business ingest
  code.
- Every C2 source/test file is under the 200-line healthy band; aggregate
  nonblank/noncomment count is 49.
- The repository lacks `scripts/python/check-no-excuse-rules.py`; its absence
  was confirmed and no substitute was claimed.
