# AMIS Review

CRM AMIS and MISA reconciliation audit snapshot for 2026-07-05.

## Contents

- `input/`: source exports used to rebuild the reconciliation report.
- `old_check/`: surviving output from the older audit used as reference taxonomy and prior issue state.
- `scripts/build_audit_report.py`: regeneration script for the Excel report.
- `bao_cao_doi_soat_CRM_MISA_2026-07-05.xlsx`: generated reconciliation workbook.

## Regenerate Report

The script expects `openpyxl` and the source files under `input/` and `old_check/`.

```bash
python3 scripts/build_audit_report.py
```

The output workbook is written to the project root.

## PSI Web

The working acceptance preview uses the same verified source rules as the
offline 03/09 pipeline. Start it from the repository root:

```bash
rtk proxy uv run --extra online python -m uvicorn web.preview:app --host 127.0.0.1 --port 18787
```

For the configured online Draft store, add `--env-file .env` after `uv run`.
The private `PSI_REPORT_DATABASE_URL` must use the restricted Neon runtime role.

Open `http://127.0.0.1:18787`. Select the cutoff, seven official inputs
(Product, Purchase/PO, Revenue, Inventory, CRM, Target, approved Manual Check)
and the prior approved PSI Final. Purchase and Target may be the previously
approved files. Pre-orders are derived from CRM Final less Revenue;
`Pre order feedback.xlsx` is not an official source.

The preview verifies source hashes, prior-Final chronology, independently
recomputes business balances, checks a Parquet round-trip, and validates the
saved 17-sheet Excel file before offering a **Draft** download. When Neon is
configured, validated payloads and all 17 typed sheet snapshots are committed
atomically and available in report history across restarts. Downloads reconstruct
the Draft with the recorded renderer and require the original workbook checksum.
Without that configuration, only the latest Draft remains in memory. The interface
is loopback-only; Final publication and Power BI remain separate. The old
`web/server.py` is the incomplete Supabase-era API;
it is not the preview entry point or the approved cloud architecture.

Implementation boundaries and remaining cloud acceptance are documented in
[`docs/PSI_ONLINE_ACCEPTANCE.md`](docs/PSI_ONLINE_ACCEPTANCE.md).

Validate Manual Check before generation:

```bash
/Users/iant1359/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/validate_manual_check.py
```

The current source contract, formulas, mismatch policy and approval workflow are documented in [`docs/PSI_PROCESS_UPTODATE.md`](docs/PSI_PROCESS_UPTODATE.md). `scripts/build_audit_report.py` is retained only for the older reconciliation snapshot and must not be used as the PSI Final generator.
