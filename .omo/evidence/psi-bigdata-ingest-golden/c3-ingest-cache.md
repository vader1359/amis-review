# C3 ingest and cache evidence

## Outcome

Seven exact XLSX relations now decode through fastexcel/Polars into ordered canonical `String` projections and materialize as one content-addressed Parquet file per relation. Every invocation reloads the manifest and validates all six current source hashes plus all seven sheet/header contracts before it inspects or mutates the cache. A complete warm cache is read-only and rejected on key, schema, shape, null-count, content-hash, path, or file-integrity mismatch. Cold writes stage the complete seven-file set in a sibling temporary directory and publish it with one directory replacement; an exception removes staging and emits no final cache.

## Success criteria

| Scenario | Invocation | Binary observable | Artifact |
|---|---|---|---|
| Real cold then warm | redacted manual driver plus C3 tests | 7 misses, then 7 hits; stable metadata and no rewrites | `c3/manual-cold-warm.txt`, `c3/pytest-c3.txt` |
| All checkpoint tests | `uv run pytest tests/psi_tool -q` | 27/27 pass | `c3/pytest-package.txt` |
| Warm source drift | focused copied-source regression | fails before hit; seven cache bytes/mtimes unchanged; no temp | `c3/pytest-c3.txt` |
| Independent PyArrow readback | reproducible PEP 723 PyArrow driver | all 7 ordered schemas, shapes, String types, null counts, and `psi.*` metadata match | `c3/manual_pyarrow_check.py`, `c3/manual-pyarrow.json` |
| Driver fail closed | same driver against metadata-tampered copy | nonzero exit with redacted CheckError | `c3/manual-pyarrow-negative.txt` |
| No cache rewrites | manual cold/warm driver | all seven `st_mtime_ns` values unchanged after warm run | `c3/manual-cold-warm.txt` |
| Source immutability | SHA-256 before/after same manual run | all six source hashes unchanged and equal manifest | `c3/manual-cold-warm.txt` |
| Cleanup | simulated interruption plus manual cleanup | final interrupted cache absent, staging absent, zero C3 temp leaks | `c3/pytest-c3.txt`, `c3/cleanup.txt` |
| Strict quality | Ruff project checks, basedpyright-all, no-excuse per owned file | all green; 0 type errors; pure-LOC gate green | `c3/quality.txt` |

## Adversarial matrix

- Source SHA drift on a warm invocation: rejected before any cache hit/read-as-hit or rewrite; all seven existing cache byte hashes and mtimes remain unchanged.
- Actual renamed projected header in a copied XLSX: rejected exactly; originals untouched.
- Truncated Parquet: rejected as corrupt/unreadable.
- Valid Parquet with changed content and old integrity metadata: rejected.
- Embedded cache-key mismatch: rejected.
- Symlink output root and foreign/incomplete cache state: rejected before writes.
- Simulated interruption after one staged relation: staging recursively removed; no final cache.
- Semantic boundary probes: null differs from empty; comma, quote, and newline values do not collide; identical frames hash identically in a second process.

## Cache identity and semantic hash

The filename key hashes cache format, contract/schema versions, semantic-hash version, source SHA-256, relation role, exact sheet/header strategy, physical/logical extraction shapes, ordered source-to-canonical projection, and dtype contract. `psi-semantic-string-v1` hashes explicit length-prefixed version/schema/column segments, row count, a vectorized null bitmap, and fixed always-quoted UTF-8 CSV bytes for each ordered String column. It is independent of Parquet encoding and chunk layout; it does not iterate workbook rows in Python. Parquet metadata embeds the key, semantic version/hash, relation ID, schema, shape, and aggregate null counts. The file-byte SHA-256 is returned separately.

## Cleanup receipt and scope

Manual cache directory removed; zero matching temp directories remained. No source workbook, contract, manifest, CLI, database, web code, business transform, legacy test, or dependency file was changed. No row values or absolute source paths were recorded in evidence.

## Residual risk

`load_manifest` validates relative source paths against the process working directory, so the cache seam temporarily changes cwd while calling it and restores cwd in `finally`; callers should serialize this synchronous boundary if they introduce threads. The cache is process-atomic under tested exceptions and same-filesystem directory replacement. A machine/power loss between filesystem write and durable storage is not simulated; this checkpoint does not claim crash-durable `fsync` semantics.
