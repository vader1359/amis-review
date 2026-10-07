# IANS-90 findings on Ian

Compared candidate `7406a8a84d8f7e4a99ce00230481b3719f603333` with base
`57b73cea3494ce2f323547249de6af48dfa4d56b`, using the private workbook on Ian.
No workbook, credentials, or shared `.env` were changed.

## Manual Check: historical assertion, not a loader regression

At `AS_OF=2026-08-07`, both loaders return the same summary for the workbook
used by QA (`outputs/019fb0bf-3af9-7813-aa46-33b6a4620a7d/PSI_Manual_Check.xlsx`
in the local PSI release archive):

| Metric | Old test assertion | Current workbook, base and candidate |
| --- | ---: | ---: |
| exceptions | 110 | 117 |
| approved_active_exceptions | 97 | 97 |
| open_exceptions | 12 | 12 |
| approved_active_preorder_exclusions | 374 | 386 |
| approved_active_order_exclusions | 4 | 4 |
| approved_active_sku_mappings | 16 | 16 |

The source and output workbooks are byte-identical. Their SHA-256 is
`fe78ab207f85b6af8e6af94c484e01048bf7eb08d9bca81861d668de788c6d2f`.
The archived `.tmp/preorder-exclusions-20260814/PSI_Manual_Check.before_3_orders.xlsx`
has SHA-256
`21b0fae9a8ca06b1a89076a31ebd1fd5737ce8bb7b2742d0f1ffcd449002014a`
and matches all six original assertions exactly.

Compared with that archived snapshot, the current workbook adds 7 exception
records effective on 2026-08-14: none is active at the test's AS_OF. The
`exceptions` metric counts all records, including future-effective records.
It also adds 23 preorder records: 12 have historical effective dates
(10 on 2024-05-15, 1 on 2026-05-20, 1 on 2026-05-12), and 11 are effective on
2026-08-27. Exactly 12 additions are active at the test's AS_OF. The workbook
records approval dates of 2026-08-14 for the 12 historical additions.

The test and assertions are deliberately unchanged. A mutable private workbook
cannot serve as the fixed migration snapshot. Use the archived snapshot for
that assertion; the current workbook's 117/386 result is consistent with its
records. Do not replace the expected counts merely to make the test green.

## Duplicate preorder identities: valid data warning

At the same AS_OF, 386 active registry rows represent 382 unique
`Order ID + canonical SKU` identities. Two groups have three rows each; all
duplicate rows have `APPROVED / EXCLUDE FROM PREORDER`.
The pipeline deliberately uses a set of permanent identities, exposes duplicate
groups in Data gaps, and checks excluded output uniqueness and authorization.
The WARN does not mean duplicate business output. No registry data was edited.

## Frontend findings

The favicon now uses an explicit inline SVG matching the existing blue P mark,
so the browser no longer requests a nonexistent default favicon.

The empty missing-source message occurred with four assigned roles plus an
unassigned extra file: `missing=[]`, `duplicate=[]`, `ready=false`.
The UI now explains that the extra unassigned file must be removed.
Source and checked-in production assets were updated together.

The CSP warning is pre-existing: base and candidate have identical UI,
preview policy, and dependency lockfile. Uploading a file mounts Table and
produces `style-src-elem`. The installed
`@rc-component/util/es/getScrollBarSize.js` calls `updateCSS` for a temporary
`rc-scrollbar-measure-*` rule without passing a CSP nonce.
The temporary rule is removed after measurement, explaining why inspecting
remaining style tags finds only correctly nonced styles.

This LOW dependency issue remains open. Fixing it requires a nonce-aware
dependency change or replacing the measurement mechanism; no policy weakening,
global DOM monkeypatch, dependency upgrade, or unrelated Table refactor was
introduced in this small findings patch.

## Ian CA configuration

QA's evidence identifies an obsolete macOS `sslrootcert` path inside
`PSI_REPORT_DATABASE_URL`. `/etc/ssl/certs/ca-certificates.crt` is readable on Ian.
For an Ian process, replace only the connection URL's `sslrootcert` parameter
with that absolute path, preserving `sslmode=verify-full`, host, role, and all
other connection parameters. The configuration owner can persist the same
change in their private Ian configuration. Do not log the URL or commit `.env`.
QA already proved read-only `SELECT 1` and the API succeeded with this
process-only CA override. This fix run did not access or modify shared `.env`.

## Author verification

- `uv run --extra online pytest -q`, with the current private workbook linked
  at the test's required input path: exit 1, **303 passed, 2 skipped, 1 failed**
  in 258.03 seconds. The sole failure is the unchanged historical
  `test_canonical_workbook_loads_and_has_expected_migrated_counts` assertion
  explained above. This is not a clean pytest PASS.
- `npm test`: exit 0, **16 passed, 0 failed**.
- `npm run build`: exit 0. The existing bundle-size warning remains
  (app.js about 1.25 MB before gzip); no dependency or build policy changed.
- Browser: Chromium through Bun WebView. BrowserOS Neo had no available CDP
  endpoint; the staged omowright runtime was unavailable.
  Real file input classification reproduced the CSP warning. A second,
  deterministic classification-response fixture exercised four assigned rows
  followed by one unassigned row, without persisting source data.
  The corrected alert was visible at 1440x1000 and 390x844. At mobile width,
  document width equals viewport width (390 px); the table scrolls internally.
  The explicit SVG favicon is present after the production build.
- Runtime instrumentation confirmed the temporary scrollbar rule is inserted
  with an empty nonce. Instrumentation and the local browser were closed
  after verification.
- `git diff --check`: exit 0. Production bundle word diff contains only the
  changed missing-source branch and new extra-file message.
- JSX LSP diagnostics could not initialize because the workspace has no
  TypeScript installation. Vite successfully compiled the JSX; no additional
  tooling dependency was introduced for this findings patch.
