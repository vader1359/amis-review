# PSI online acceptance boundary

## Implemented local acceptance path

`web.preview` → immutable selected bytes and SHA-256 → portable preparation →
independent source recomputation → Parquet semantic equality → XlsxWriter Draft
→ independent OOXML/openpyxl validation → HTTP download of the verified bytes.

The source workbooks remain unchanged. Source kinds are explicit and never
inferred from filename. Purchase and Target can reuse a previously approved
upload; all seven chosen files and the prior Final are pinned for each run.
The offline Final is explicitly selected by the operator; its content date,
17-sheet topology, mismatch headers and passing Checks are validated. This is
not an authenticated cloud approval receipt.

## Ant Design workspace and reusable sources

The complete preview interface uses locally bundled React and Ant Design.
Select periodic exports individually or in batches of up to four files. Each
successful batch is appended to the current selection. Individual files can be
removed, and duplicate source kinds must be resolved before building. The API reads the expected
sheet names and header rows to identify CRM orders, Product Master, Revenue
and Inventory, regardless of filenames or selection order. The workspace
displays every assignment; duplicate, missing or ambiguous kinds prevent a
build until corrected. Classification does not replace full validation.

Purchase, Target, Manual Check and the selected prior Final are retained in
`~/.cache/amis-psi-preview/saved-sources` on this machine across page reloads
and server restarts. Saved files are role-bound, hash-checked snapshots with
opaque references. The UI shows filename, size and save time, with explicit
replace and clear actions. Uploading or saving a file does not approve it.
Each build still checks the baseline date and every business validation gate.
A new Draft never becomes the comparison Final automatically.

The cache holds four active selections, not release history or cloud backup.
Replacing or clearing a selection removes unused cache copies; original
workbooks are untouched. The current private QA setup was seeded from the
exact previously verified inputs, without runtime discovery of local files.

To rebuild the committed browser bundle after UI source changes:

```sh
rtk npm --prefix web/ui ci
rtk npm --prefix web/ui test
rtk npm --prefix web/ui run build
```

The generated `web/preview_static` assets are served by the existing preview
entry point. No CDN runtime is required. Ant Design styles use the server's
CSP nonce; mutation endpoints require the same-origin preview token.

Approved permanent preorder/order exclusions with `Effective To` are rejected
instead of silently expiring. Approved preorder exclusions must include evidence
and a reason in KT Note, Treatment or Notes. These guards enforce the SOP without
altering the approved source workbook or the original offline scripts.

Portable modules are installed with `psi-tool`; neither preparation nor export
loads code from `.tmp`, rewrites scripts at runtime, scans the checkout for a
baseline, or depends on a user-specific filesystem path. The governed parser
was ported with the offline rules. The original offline scripts and data are
preserved.

## Verification commands

Run from the repository root so `uv` provides the installed `psi` command to
subprocess tests:

```sh
rtk proxy uv run --extra online python -m pytest -q tests/psi_tool
```

The workbook suite supports an opt-in private golden directory through
`PSI_GOLDEN_DIR`. Golden data and generated private workbooks belong in ignored
output directories, never in fixtures or version control. Compare sheet order,
dimensions, headers, all values/formulas, merges, widths, fonts, number formats,
freeze panes and conditional formatting. Different ZIP bytes or style IDs alone
are not business or structural differences.

The UI is tested on loopback. It rejects foreign origins/hosts, requires a
same-origin preview token for generation, limits multipart requests and ZIP
expansion, and serializes builds. This is an acceptance harness for the future
worker and browser flow, not a shared service.

## Cloud acceptance still required

The approved architecture remains **Neon Postgres/Auth + Google Cloud + Power BI**.
The immutable source plan remains `.omo/plans/psi-neon-online.md`; this parity
recovery does not mark that plan's 41 Todos complete.

Remaining implementation and live verification:

- Neon schema, membership/roles, authenticated sessions, source versions, audit
  history, Draft review and immutable Final publication.
- Private GCS objects and integrity-controlled upload/download.
- Cloud Run API and worker, durable Cloud Tasks dispatch, retry/recovery and
  fencing. The preview's in-memory serialization is not a durable queue.
- Final-only analytical mart and Power BI Import/refresh with access checks.
- Preview environment deployment, backup/restore, runtime and browser gates,
  independent final reviews and the authorized production cutover.

The isolated Google Cloud project `amis-psi-preview-20260905` has been created;
Billing and the remaining bootstrap prerequisites are described in
`PSI_CLOUD_SETUP.md`. The online Draft storage extension below is separate from GCP deployment,
production cutover and Power BI publication.

The obsolete Supabase shared MVP server and its launchers were retired. Its
engine was never present in this checkout. The loopback preview is an acceptance
harness, not an authenticated shared service or a deployment target.


## Online Draft storage extension (2026-09-06)

The loopback preview now supports explicit Neon persistence. Configure the
restricted pooled connection as `PSI_REPORT_DATABASE_URL` in the ignored private
`.env`, then start:

```sh
rtk proxy uv run --env-file .env --extra online python -m uvicorn web.preview:app --host 127.0.0.1 --port 18787
```

The isolated project is `amis-psi-preview` (`calm-hall-43645294`), branch
`psi-online` (`br-curly-brook-b39hvbip`), in Singapore. The existing linked
`amis-review-psi` production project is untouched. The new preview endpoint uses
0.25 CU and suspends after 300 seconds of inactivity. Existing Neon account billing
applies; this change does not activate or upgrade Google Cloud billing.

Apply `infra/sql/psi_preview_reports.sql` explicitly with the branch's direct
migration connection. The runtime uses a separate role with only schema usage and
SELECT/INSERT on report, sheet and sheet-row tables; it cannot migrate, update or
delete snapshots. Keep migration credentials out of the application environment.

After the offline-equivalent checks pass, the API commits the payload, validation
evidence and typed cells of all 17 sheets in one transaction. Formulas and cached
results retain their positions. Read-back comparison must pass before the response
can say `storage: neon`. Retries reuse matching immutable snapshots. Connection or
integrity failures never silently become online success. Ant Design history lists
saved Drafts after a browser reload or application restart, with bounded pagination.

GCS remains the intended source and artifact file store. Until it is available,
this extension stores structured data in Neon and reconstructs Draft downloads
from the saved ordered payload using the pinned renderer. Downloads require both
independent workbook validation and the original SHA256. A renderer/runtime change
may require restoring the recorded version before an old Draft can be downloaded;
this is not permanent XLSX archival storage. Reusable uploaded source files remain
in the existing private local cache. Drafts never become approved Final reports or
Power BI inputs automatically.

Endpoints: `GET /api/reports`, `GET /api/reports/{id}`, sheet metadata at
`GET /api/reports/{id}/sheets`, bounded typed rows at
`GET /api/reports/{id}/sheets/{ordinal}/rows`, and the existing Draft download route.
Credentials remain server-only. The existing loopback/origin restrictions remain
necessary until authenticated shared access is separately implemented.
