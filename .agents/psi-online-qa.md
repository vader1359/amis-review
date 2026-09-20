# PSI online manual QA

Run scope: loopback acceptance preview at `http://127.0.0.1:18787/`, 2026-09-05. This report is independent read-only QA; it does not certify cloud publication or Power BI.

## manualQa

### surfaceEvidence

| scenario id | criterion reference | surface | exact invocation | verdict | artifactRefs |
|---|---|---|---|---|---|
| HTTP-001 | health/local unpublished mode | HTTP | `curl -i http://127.0.0.1:18787/health` | PASS | `A1` |
| HTTP-002 | static assets and security headers | HTTP | `curl -i http://127.0.0.1:18787/`; asset requests observed in BrowserOS | PASS | `A1`, `A2` |
| HTTP-003 | cross-origin and host boundary | HTTP | `curl -i -H 'Origin: https://evil.test' .../api/config`; `curl -i -H 'Host: evil.test' .../api/config` | PASS | `A1` |
| HTTP-004 | preview token required | HTTP | `curl -i -X POST http://127.0.0.1:18787/api/drafts` | PASS | `A1` |
| HTTP-005 | required source set | HTTP | `curl -i -X POST .../api/drafts` with seven source fields, no `prior_psi`, and preview token | PASS | `A1` |
| HTTP-006 | malformed package rejected before engine | HTTP | `curl -i -X POST .../api/drafts` with `main-B1osgIPb.js` uploaded for all eight file fields | PASS | `A1` |
| HTTP-007 | cutoff lower bound | HTTP | `curl -i -X POST .../api/drafts` with valid XLSX packages, `as_of=2020-01-01`, and preview token | PASS | `A1` |
| HTTP-008 | request body limit | HTTP | `curl -i --max-time 30 -X POST .../api/drafts` with sparse 402 MiB multipart member | PASS | `A1` |
| UI-001 | initial browser render and controls | BrowserOS Neo tab 1 | `createBrowserTab('iab','http://127.0.0.1:18787/',{visible:false})`, DOM snapshot, viewport screenshot | PASS | `A2` |
| UI-002 | required form validation | BrowserOS Neo tab 1 | click `Kiểm định và tạo Draft` with empty date/files | PASS | `A2` |
| UI-003 | browser console clean | BrowserOS Neo tab 1 | `tab.dev.logs({levels:['error','warn'],limit:100})` | PASS | `A2` |
| E2E-001 | real 03/09 upload and golden workbook semantic parity | BrowserOS/HTTP | set `as_of=2026-09-03`, upload all eight real source files, click `Kiểm định và tạo Draft`, download returned draft, compare against golden with documented provenance normalization and numeric tolerance | PASS | `A5` |
| E2E-002 | deterministic HTTP/direct build output | HTTP plus local pipeline | compare clean HTTP download body against independent direct build output | PASS | `A5` |

### adversarialCases

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| ADV-001 | local-only boundary | hostile Origin | reject with `ORIGIN_FORBIDDEN` | PASS | `A1` |
| ADV-002 | local-only boundary | hostile Host | reject with `LOCAL_PREVIEW_ONLY` | PASS | `A1` |
| ADV-003 | request authentication | missing token | reject with `PREVIEW_TOKEN_REQUIRED` | PASS | `A1` |
| ADV-004 | source package safety | malformed/non-ZIP upload | reject with `SOURCE_PACKAGE_INVALID`; engine not reached | PASS | `A1` |
| ADV-005 | source completeness | omitted baseline | reject with `SOURCE_SET_INVALID` | PASS | `A1` |
| ADV-006 | date validity | pre-2024 cutoff | reject with `CUTOFF_INVALID` | PASS | `A1` |
| ADV-007 | resource safety | body above configured limit | reject with HTTP 413 `REQUEST_TOO_LARGE` | PASS | `A1` |
| ADV-008 | output parity | stale/alternate 03/09 source selection | compare downloaded workbook against golden | PASS | `A5` |
| ADV-009 | output path privacy/provenance | private scratch path in rendered gate note | no `/var/folders/.../prior.xlsx` path should escape into Draft | PASS | `A5` |

### artifactRefs

| id | kind | description | path |
|---|---|---|---|
| A1 | HTTP transcript | curl -i boundary, auth, malformed-package, cutoff, and body-limit evidence | `outputs/psi-online-qa-20260905/http-boundary.txt` |
| A2 | browser action log | BrowserOS DOM/control/validation/console evidence | `outputs/psi-online-qa-20260905/browser-baseline.md` |
| A3 | provenance/blocker record | golden workbook and offline wrapper hashes; full upload pending integration | `outputs/psi-online-qa-20260905/provenance.txt` |
| A4 | browser E2E blocker | real 03/09 upload reached baseline gate; approved 19/08 Final rejected because date is in A4 rather than A1 | `outputs/psi-online-qa-20260905/e2e-baseline-blocker.txt` |
| A5 | golden comparison | browser build/download succeeded; 17-sheet/formula parity exact, one nested baseline path mismatch and float serialization deltas remain | `outputs/psi-online-qa-20260905/golden-compare.txt` |

PASS verdicts point to non-empty artifacts. The historical baseline incompatibility is retained as a failed first attempt in A4; the corrected final E2E run is recorded in A5.
