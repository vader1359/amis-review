# Final runtime debugging audit

Date: 2026-08-30

## Snapshot

- Requested frozen snapshot: `a46b1c8c48d6c22e699a4cfe71d7cb910c9bf5649b087c4eb5f23f7dc8bf0083`.
- Snapshot actually present before and after this audit: `5be980fe954a00632675a355f8bd861eacfc55f03ba487c715699e2bcd6089ab`.
- Ordered command: `shasum -a 256 pyproject.toml uv.lock src/psi_tool/*.py tests/psi_tool/*.py tests/psi_tool/fixtures/golden_manifest.toml docs/psi_tool_v1/contract.md | shasum -a 256`.
- The audit therefore covers the current post-fix tree (`5be...`), not the earlier requested `a46...` identity.

## H1 - real CLI cold/warm and cross-process semantic identity: PASS

Surface: real `psi` CLI, `uv run psi inspect`.

Exact invocations:

```text
uv run psi inspect --manifest tests/psi_tool/fixtures/golden_manifest.toml --output-dir /private/tmp/psi-final-debug.j8t2Uf/cold-warm
PASS report=inspect-report.json semantic_sha256=8a3437cd8392c9d56c01113f0ee693376a54512a86d1f092880a819595ca9955

uv run psi inspect --manifest tests/psi_tool/fixtures/golden_manifest.toml --output-dir /private/tmp/psi-final-debug.j8t2Uf/cold-warm
PASS report=inspect-report.json semantic_sha256=8a3437cd8392c9d56c01113f0ee693376a54512a86d1f092880a819595ca9955
```

Independent report readback after a cold run: `PASS 7 [False, False, False, False, False, False, False] 8a3437cd8392c9d56c01113f0ee693376a54512a86d1f092880a819595ca9955`.
Two separate cold output roots, `/private/tmp/psi-final-debug.j8t2Uf/cold-only` and `cold-only-2`, produced the same semantic hash `8a3437cd...` and seven cache misses each. The warm run produced seven hits. The published tree contained exactly seven Parquet files under `cache/` and `inspect-report.json`; no staging directory remained.

## H2 - malformed, source drift, and corrupt cache fail closed: PASS

Surface: real `psi` CLI.

```text
uv run psi inspect --manifest /dev/null --output-dir /private/tmp/psi-final-debug.j8t2Uf/malformed
FAIL report=none semantic_sha256=04dda1e3ccc6dcfb68b3d97014910337667f09ee6a75b7502a06fd16f8a3bb03
inspect failed: validation_failed

uv run psi inspect --manifest /private/tmp/psi-final-debug.j8t2Uf/drifted.toml --output-dir /private/tmp/psi-final-debug.j8t2Uf/drifted-run
inspect failed: validation_failed
FAIL report=none semantic_sha256=04dda1e3ccc6dcfb68b3d97014910337667f09ee6a75b7502a06fd16f8a3bb03

truncate -s -16 /private/tmp/psi-final-debug.j8t2Uf/cold-warm/cache/crm_sale_items-6c41cd4df74d1f8b616761f26088e110247bba5c27317f75396da4afbcb7e848.parquet
uv run psi inspect --manifest tests/psi_tool/fixtures/golden_manifest.toml --output-dir /private/tmp/psi-final-debug.j8t2Uf/cold-warm
FAIL report=inspect-report.json semantic_sha256=04dda1e3ccc6dcfb68b3d97014910337667f09ee6a75b7502a06fd16f8a3bb03
inspect failed: validation_failed
```

Corrupt warm readback was `FAIL validation_failed`; no staging directory or traceback was emitted. Malformed and drifted first runs emitted no output root.

## H3 - process-group cancellation and nested parent change: PASS

Surface: real process-group subprocess running `uv run psi inspect`, with a partial Parquet observed before signal.

SIGINT exact result: `partial True returncode 130`, stdout `FAIL report=none semantic_sha256=04dda1e3ccc6dcfb68b3d97014910337667f09ee6a75b7502a06fd16f8a3bb03`, stderr `inspect cancelled`, base tree `[]`.

SIGTERM exact result: `partial True returncode 143`, stdout `FAIL report=none semantic_sha256=04dda1e3ccc6dcfb68b3d97014910337667f09ee6a75b7502a06fd16f8a3bb03`, stderr `inspect cancelled`, base tree `[]`.

A second signal burst during a partial run produced `returncode 143`, `stderr inspect cancelled`, and base tree `[]`; the protected cleanup path left no staging or final output residue. The targeted signal regression surface also completed with two tests (`..`).

Nested directory-name-change regression surface: `uv run pytest tests/psi_tool/test_ancestor_swap.py -q` returned `2 passed in 3.54s`.

## H4 - silent failure, processes, and residuals: PASS

No run printed a traceback or a PASS report on malformed, drifted, corrupt, or cancelled input. Final process scan found no `uv run psi inspect` process. Staging scan found no `.*.tmp` directory. All temporary audit roots under `/private/tmp/psi-final-debug.j8t2Uf/` were owned by this audit and removed after capture.

## Verdict

PASS for the current snapshot `5be980fe...`. The requested `a46...` snapshot was not the tree available when this audit resumed; this identity mismatch is recorded rather than silently attributed to the current evidence.
