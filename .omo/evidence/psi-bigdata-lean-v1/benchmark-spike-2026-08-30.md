# PSI XLSX → Parquet benchmark spike

Date: 2026-08-30  
Verdict: **GO for the Lean V1 Parquet cache; NO database required yet.**

## Scope

This spike tested only the ingestion/cache boundary. It did not implement PSI business rules, resolve the three TBC contracts, or generate a Final workbook.

The source was the sanitized fixture `PSI_SAMPLE_INPUT/CRM_Sale_sample.xlsx`. Source workbook values were never printed, and the file was opened read-only.

## Measured results

| Sheet | Data shape | openpyxl count-only | Polars XLSX read | First-read ratio | Warm Parquet median | Replay ratio vs openpyxl | Parquet size | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `Danh sách` | 9,982 × 40 | 2.395899 s | 3.153880 s | 0.760× | 0.008840 s | 271.0× | 1,054,088 B | 266,551,296 B |
| `Bảng hàng hóa` | 49,122 × 33 | 5.645859 s | 0.920259 s | 6.135× | 0.016346 s | 345.4× | 2,143,412 B | 444,727,296 B |
| **Combined** | **59,104 rows** | **8.041758 s** | **4.074138 s** | **1.974×** | **0.025185 s** | **319.3×** | **3,197,500 B** | **424 MiB max process** |

Interpretation:

- Polars does not win every first read: the smaller/order sheet was 24% slower than the conservative openpyxl count-only pass.
- On the larger item sheet, Polars was 6.1× faster even though it materialized typed columns while the baseline only counted non-empty rows.
- The durable gain is reuse: after one XLSX conversion, lazy Parquet replay was about 319× faster across the two sheets.
- The two Parquet files total about 3.2 MB versus the 12.65 MB source workbook.
- Several ambiguous Excel columns fell back to string. Lean V1 must use explicit dtype and column projection rather than accept inference warnings.

This is an indicative feasibility run, not an SLA benchmark. XLSX first-load numbers are one observed run per sheet. Parquet used one unmeasured warm-up plus five measured runs; the order sheet had one 0.183 s outlier, so this sample must not be described as p95.

## Integrity evidence

- Source SHA-256 before materialization and after the run: `d3c7ddb0835d3ec12c52d50a34e96ca57f5a5126f2d531cc35173213e0fe3c4d`.
- Orders Parquet SHA-256: `b75190cddc869b18061a475c238a595cd6588c7766e0cb277dbd70e627f6c96c`.
- Items Parquet SHA-256: `7a43babbb97b573e7f1147c5bf2c7b9def3e274051733b66544bc3f74fc68972`.
- Every measured Parquet replay passed exact Polars frame equality against the materialized XLSX frame.
- Raw reports and Parquet artifacts are isolated under `.tmp/psi-benchmark-dTLwFW/`; no source or existing output was overwritten.

## Implementation artifact

- `scripts/benchmark_xlsx_pipeline.py`: executable PEP 723 CLI using uv, NumPy, PyArrow, Polars, fastexcel and Typer.
- `test/test_benchmark_xlsx_pipeline.py`: real subprocess E2E over the sanitized Target fixture.
- `.omo/plans/psi-bigdata-lean-v1.md`: eight-Todo implementation plan and database decision thresholds.

## Verification

```text
E2E:               1 passed
Ruff:              all checks passed; 2 files formatted
basedpyright all:  0 errors, 0 warnings, 0 notes
no-excuse audit:   no violations in 2 files
pure LOC:          CLI 158; test 39
full repo suite:    6 passed; 1 existing Manual Check fixture-drift failure
```

The unrelated full-suite failure expects 110 exceptions and 374 active preorder exclusions, while the current workbook loads 117 and 386. Neither `input/PSI_Manual_Check.xlsx` nor `test/test_manual_check.py` was changed by this spike, so the expected values were not rewritten.

## Go/no-go decision

Proceed with the Lean V1 architecture:

```text
immutable XLSX
  → explicit fastexcel schema/projection
  → content-hashed Parquet
  → Polars lazy transforms
  → independently validated XLSX
```

Do not add a database to the computation path. Add SQLite only when the tool needs durable run/approval history on one machine; add PostgreSQL/Supabase only for shared multi-user state; consider DuckDB only after a profiled cross-period analytical bottleneck.

The next implementation checkpoint is explicit schemas and multi-source golden parity, not web/auth/database work.
