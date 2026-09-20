# PSI online persistence code review

**Status:** CLEAR  
**Recommendation:** APPROVE

Reviewed final persistence delta, including `web/online_report_store.py`,
`infra/sql/psi_preview_reports.sql`, preview API, online history UI, dependency
lock, and scoped documentation. The review was read-only except for this report.

## Findings

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

None.

## Assessment

- The Draft write is one database transaction. It validates pipeline evidence and
  workbook bytes, records the 17 typed sheet snapshots, then reads back payload,
  ordered payload JSON, evidence, and rows before returning `storage: neon`.
- Immutable identity conflict handling compares evidence, renderer and snapshot
  digests rather than overwriting an existing report.
- Download regenerates from the recorded ordered payload and refuses a changed
  renderer, checksum, snapshot, or failed independent workbook validation.
- Report, sheet and row history uses bounded pagination. A missing parent report
  now returns an explicit 404 for both sheet routes; invalid pages/sheet ordinals
  return 422.
- The Ant Design history only appears when the server reports configured Neon
  storage and labels a result online only after `storage: neon` is returned.
- Docs accurately retain the preview-only boundary: no Final approval, Power BI
  publication, or GCS artifact claim. They document the intentional reconstructed
  Draft limitation until GCS is available.

## Verification

- `uv run --extra online python -m pytest tests/test_online_report_store.py tests/psi_tool/test_online_report_api.py -q` — 16 passed.
- `uv run --extra online python -m ruff check --select E4,E7,E9,F,I web/online_report_store.py web/preview.py tests/test_online_report_store.py tests/psi_tool/test_online_report_api.py` — passed.
- `git diff --check` — passed.
- Coordinator independently verified the live Neon migration/restricted runtime
  role and an accepted real Draft: 17 sheets, 381,305 cells, 8,565 formulas;
  restart download was 2,396,862 bytes and matched the accepted SHA-256.

## Skill perspective

`remove-ai-slops` and `programming` were not available in the configured skill
roots. Their review criteria were applied manually. The direct store tests cover
transactions, idempotence, tampering, typed formula/cache/text preservation,
pagination, and sanitized driver errors; they are not deletion-only or
implementation-constant tests. The production code has no untyped escape hatch
or needless abstraction for this feature.
