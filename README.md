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
