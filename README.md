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

## PSI preview

Run the local acceptance preview on loopback:

```bash
uv run --extra online python -m uvicorn web.preview:app --host 127.0.0.1 --port 18787
```

Open `http://127.0.0.1:18787`. This preview builds validated Drafts; it does not provide shared login or Final publication. See [`docs/PSI_ONLINE_ACCEPTANCE.md`](docs/PSI_ONLINE_ACCEPTANCE.md) for its source contract and limits. The former Supabase shared MVP server and launchers were retired because their engine was absent from this checkout. They are not deployment instructions.

`scripts/build_audit_report.py` is retained only for the older reconciliation snapshot and must not be used as the PSI Final generator.
