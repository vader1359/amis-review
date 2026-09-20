# PSI online persistence — independent manual QA

Run date: 2026-09-06 (Asia/Ho_Chi_Minh)  
Surface: local FastAPI preview at `http://127.0.0.1:18787/`, BrowserOS neo page `122`, after the report was saved and the server was restarted by the implementer.  
Scope: read-only verification; no source, database, or application mutation was performed. Workbook row values were not opened or recorded; only report/sheet metadata and hashes were used.

## manualQa

### surfaceEvidence

| scenario id | criterion reference | surface | exact invocation | verdict | artifactRefs |
|---|---|---|---|---|---|
| PERSIST-UI-01 | Persisted report appears automatically after restart | BrowserOS neo UI | Fresh page 124; waited for **Báo cáo đã lưu online** and `03/09/2026`; the row appeared without clicking **Làm mới** | PASS | `browser-history-log`, `live-report-metadata` |
| PERSIST-UI-02 | A persisted report can be opened and remains a Draft | BrowserOS neo UI | On page 122: `act(click, ref=e24)` **Mở báo cáo**; `read(format=text)`; `act(click, ref=e39)` **Xem kết quả kiểm định** | PASS | `browser-history-log`, `live-report-metadata` |
| PERSIST-UI-03 | Online badge and 17-sheet validation are honest | BrowserOS neo UI | `evaluate(page=122, () => ({hasOnlineBadge, hasSheetValidation, hasHistoryRow}))`; returned `{hasOnlineBadge:true, hasSheetValidation:true, hasHistoryRow:true}` | PASS | `browser-dom-assertions`, `live-report-metadata` |
| PERSIST-UI-04 | Incremental upload and retained approved-file wording remains visible | BrowserOS neo UI | `read(page=122, format=text, viewportOnly=false)` after opening report; observed “Tải từng file hoặc nhiều file mỗi đợt…”, four retained approved-file rows, and “Draft mới không tự thay PSI Final” | PASS | `browser-history-log` |
| PERSIST-API-01 | Neon report detail and all sheets are rehydratable | HTTP API | `rtk curl -sS --max-time 10 http://127.0.0.1:18787/api/reports/7676496e89804e12b4e7896aec8192c1`; then `/api/reports/7676496e89804e12b4e7896aec8192c1/sheets` | PASS | `api-read-log`, `live-report-metadata` |
| PERSIST-API-02 | API reports stored source metadata without exposing connection credentials | HTTP API | `rtk curl -sS -o /tmp/psiqa-config.json -w 'config_status=%{http_code}\\n' --max-time 10 http://127.0.0.1:18787/api/config`; `rtk python3 -c` parsed only top-level keys, `report_storage`, and saved role/filename metadata | PASS | `api-guard-log` |
| PERSIST-UI-05 | Persisted Excel Draft download is available from history | BrowserOS neo UI | `snapshot(page=122)`; `download(page=122, ref=e25)` history link; BrowserOS saved `PSI_Draft.xlsx` to its tool-output path | PASS | `browser-download-log`, `live-report-metadata` |

### adversarialCases

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| ADV-SEC-01 | Non-GET mutation guard | missing preview token | Invocation: `rtk curl -sS -i -X POST --max-time 10 http://127.0.0.1:18787/api/sources/classify`; expected reject before processing or persistence | PASS — HTTP 403 `PREVIEW_TOKEN_REQUIRED` | `api-guard-log` |
| ADV-BOUND-01 | History pagination bound | out-of-range query | Invocation: `rtk curl -sS -i --max-time 10 'http://127.0.0.1:18787/api/reports?limit=101'`; expected HTTP 422 and no mutation | PASS | `api-guard-log` |
| ADV-BOUND-02 | Sheet row access bound | invalid sheet ordinal | Invocation: `rtk curl -sS -i --max-time 10 http://127.0.0.1:18787/api/reports/7676496e89804e12b4e7896aec8192c1/sheets/0/rows`; expected HTTP 422 and no row data | PASS — `REPORT_SHEET_INVALID` | `api-guard-log` |
| ADV-SEC-02 | Browser secret exposure | credential/token leakage in rendered UI | Invocation: BrowserOS `evaluate(page=122, ...)`; expected no database URL, `DATABASE_URL`, Neon connection string, or `preview_token` label in body text | PASS — returned `hasDatabaseUrl:false`, `hasPreviewTokenLabel:false` | `browser-dom-assertions` |
| ADV-DRAFT-01 | Approval-state integrity | persisted Draft mistaken for Final | Invocation: API report detail GET plus BrowserOS `read(page=122, format=text)` after `Mở báo cáo`; expected state `draft` and approval guidance before PSI Final | PASS — API `state:"draft"`, UI “Draft mới không tự thay PSI Final” and approval guidance | `browser-history-log`, `api-read-log` |

## Artifact references

| id | kind | description | path |
|---|---|---|---|
| browser-history-log | browser action log | BrowserOS page 122 reload/refresh, history row, open action, visible online badge, 17-sheet validation, incremental-upload and retained-source wording | `/Users/iant1359/Develop/amis-review/.agents/psi-online-persistence-qa.md` |
| browser-dom-assertions | browser DOM assertion log | BrowserOS `evaluate` returned no DB URL or token label and confirmed online badge/history/17-sheet validation | `/Users/iant1359/Develop/amis-review/.agents/psi-online-persistence-qa.md` |
| browser-download-log | browser download action log | BrowserOS history Excel link downloaded `PSI_Draft.xlsx` after restart | `/Users/iant1359/Develop/amis-review/.agents/psi-online-persistence-qa.md` |
| api-read-log | HTTP read evidence | `/api/reports/{id}` returned `storage:"neon"`, `state:"draft"`, `sheet_count:17`; `/sheets` returned ordinals 1–17 with metadata only | `/Users/iant1359/Develop/amis-review/.agents/psi-online-persistence-qa.md` |
| api-guard-log | HTTP guard/bound evidence | `/api/config` status 200 with `report_storage={enabled:true,provider:"neon"}`; mutation without token 403; invalid bounds 422 | `/Users/iant1359/Develop/amis-review/.agents/psi-online-persistence-qa.md` |
| live-report-metadata | JSON metadata artifact | Implementer-provided live report metadata, sheet counts/hashes, database counts, restart download checksum and idempotence | `/Users/iant1359/Develop/amis-review/.agents/psi-online-persistence-live.json` |

## Evidence notes

- The report id exercised was `7676496e89804e12b4e7896aec8192c1`, with cutoff `2026-09-03`, `state=draft`, `storage=neon`, and `sheet_count=17`.
- The `/sheets` response exposed only ordinal/name/shape/hash metadata in this QA record; no sheet row endpoint was called with a valid ordinal, so customer/business row values were not printed.
- The API returned one history report after the implementer’s restart. A fresh BrowserOS page 124 automatically rendered the `03/09/2026` row without clicking **Làm mới**. The earlier empty observation was captured before the asynchronous history request settled.
