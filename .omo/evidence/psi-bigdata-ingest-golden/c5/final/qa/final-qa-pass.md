# Final QA — approved snapshot

## Verdict

PASS for the approved product snapshot
`5be980fe954a00632675a355f8bd861eacfc55f03ba487c715699e2bcd6089ab`.

The full `tests/psi_tool` set ran exactly once as four non-overlapping
concurrent pytest shards. All shards completed below the 12-minute limit.

## Snapshot and package gates

Exact snapshot command:

```text
shasum -a 256 pyproject.toml uv.lock src/psi_tool/*.py tests/psi_tool/*.py tests/psi_tool/fixtures/golden_manifest.toml docs/psi_tool_v1/contract.md | shasum -a 256
```

Observed before QA: `5be980fe954a00632675a355f8bd861eacfc55f03ba487c715699e2bcd6089ab`.
No product bytes changed during QA; the approved snapshot remains bound.

### Complete file-to-shard map

| shard | files | tests | pytest time | failures/errors/skips |
|---|---|---:|---:|---|
| shard-1-cache | `test_cache_failures.py`, `test_psi_cli_foundation.py` | 12 | 78.225s | 0 / 0 / 0 |
| shard-2-e2e | `test_e2e.py`, `test_relation_pin_enforcement.py` | 11 | 99.733s | 0 / 0 / 0 |
| shard-3-signals | `test_cli_signals.py`, `test_ancestor_swap.py`, `test_contracts.py` | 20 | 104.431s | 0 / 0 / 0 |
| shard-4-core | `test_cli.py`, `test_ingest.py`, `test_output_lifecycle.py`, `test_verified_manifest.py` | 18 | 125.471s | 0 / 0 / 0 |
| **aggregate** | **all 11 test files** | **61** | **407.860s sum; 125.471s max wall** | **0 / 0 / 0** |

JUnit artifacts: [shard-1-cache.xml](shard-1-cache.xml),
[shard-2-e2e.xml](shard-2-e2e.xml), [shard-3-signals.xml](shard-3-signals.xml),
[shard-4-core.xml](shard-4-core.xml).

Strict static gates, each run once after the shards:

- `uv run ruff check src tests`: PASS, all checks passed.
- `uv run ruff format --check src tests`: PASS, 36 files already formatted.
- `uv run basedpyright`: PASS, 0 errors, 0 warnings, 0 notes.
- No-excuse/forbidden-dependency scan: PASS, 35 owned Python files, zero hits
  for forbidden dependencies, `Any`, `cast`, type-ignore, broad exceptions,
  `os.chdir`, TODO/FIXME/HACK.
- Pure LOC: PASS, zero files over 250; maximum is
  `src/psi_tool/_contract_models.py` at 226 pure LOC.

## Runtime and artifact evidence

The independent current-snapshot runtime audit was reused as authorized:
[runtime-audit.md](../debug/runtime-audit.md). It records the real `psi
inspect` surface on this exact snapshot:

- cold then warm exits 0/0, stable semantic SHA
  `8a3437cd8392c9d56c01113f0ee693376a54512a86d1f092880a819595ca9955`, exact
  eight-file tree (seven Parquet files plus `inspect-report.json`), seven warm
  hits, and seven actual relation hashes equal to manifest pins;
- process-group SIGINT exits 130 and SIGTERM exits 143 with sanitized
  `inspect cancelled`, no final output, and no staging residue;
- malformed, source-drifted, and corrupt-cache cases fail closed; no traceback
  or misleading PASS output;
- nested parent swap protection and final cleanup passed.

Independent source readback during this QA found all six manifest source SHA-256
values equal to the current workbook bytes. The shard JUnit directly includes
the real cold/warm E2E case and both real process-group signal parameter cases.
The final process scan found no pytest, basedpyright, `uv run psi inspect`, or
`.run-*.tmp` residue.

## Manual QA matrix

### surfaceEvidence

| scenario id | criterion reference | surface | exact invocation | verdict | artifactRefs |
|---|---|---|---|---|---|
| FINAL-SNAPSHOT | frozen product binding | repository | ordered `shasum` command above | PASS | A1 |
| FINAL-SHARDS | full package suite | local pytest | four exact shard commands recorded in run output | PASS | A2,A3,A4,A5 |
| FINAL-STATIC | strict quality gates | local CLI/package | Ruff check, Ruff format check, basedpyright, no-excuse/LOC scan | PASS | A6 |
| FINAL-COLD-WARM | CLI parity/tree | real `uv run psi inspect` | current-snapshot independent audit, cold then warm | PASS | A7 |
| FINAL-SIGNALS | cancellation cleanup | real process-group CLI | current-snapshot independent audit, SIGINT/SIGTERM | PASS | A7 |

### adversarialCases

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| FINAL-ADV-01 | cache integrity | corrupt/self-consistent metadata | reject with FAIL, never claim PASS | PASS | A3,A7 |
| FINAL-ADV-02 | output lifecycle | ancestor/staging swap and symlink target | preserve foreign target; clean owned inode | PASS | A4,A7 |
| FINAL-ADV-03 | signal lifecycle | SIGINT/SIGTERM and second signal | 130/143, protected cleanup, zero residue | PASS | A2,A7 |
| FINAL-ADV-04 | source integrity | source hash drift | fail closed before PASS publication | PASS | A3,A7 |

## Artifact refs

| id | kind | description | path |
|---|---|---|---|
| A1 | text | Approved snapshot and final binding | `final-qa-pass.md` |
| A2 | JUnit XML | Cache/foundation shard, 12 passed | `shard-1-cache.xml` |
| A3 | JUnit XML | E2E/relation-pin shard, 11 passed | `shard-2-e2e.xml` |
| A4 | JUnit XML | Signals/ancestor/contracts shard, 20 passed | `shard-3-signals.xml` |
| A5 | JUnit XML | CLI/ingest/lifecycle/manifest shard, 18 passed | `shard-4-core.xml` |
| A6 | text | Static gate command outputs and independent scan results | `final-qa-pass.md` |
| A7 | audit | Current-snapshot independent cold/warm/signal/runtime evidence | `../debug/runtime-audit.md` |
