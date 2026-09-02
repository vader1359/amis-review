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

Run the local PSI upload tool with the bundled Python runtime:

```bash
/Users/iant1359/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 web/server.py
```

Then open `http://127.0.0.1:8787`. Upload Product, Purchase/PO, Revenue, Inventory, CRM, Target and the approved `PSI_Manual_Check.xlsx`. Pre-orders are derived from CRM Final less Revenue; `Pre order feedback.xlsx` is not an official source.

Validate Manual Check before generation:

```bash
/Users/iant1359/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/validate_manual_check.py
```

The current source contract, formulas, mismatch policy and approval workflow are documented in [`docs/PSI_PROCESS_UPTODATE.md`](docs/PSI_PROCESS_UPTODATE.md). `scripts/build_audit_report.py` is retained only for the older reconciliation snapshot and must not be used as the PSI Final generator.
