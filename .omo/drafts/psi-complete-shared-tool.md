---
slug: psi-complete-shared-tool
status: review-round-active
intent: unclear
classification: architecture
review_required: true
plan_path: .omo/plans/psi-complete-shared-tool.md
plan_sha256: 2d14a50e8543b8c3c243e88f801923234db168739d6fa21241ecd3ec19f85a8c
review_round_id: 982B4112-288F-4485-B799-BC924461150C
round_status: iterate
phase: revision_required
completion_cas: status=in_flight,workspace_root,runtime_home,target,launch_id,round_id,plan_sha256,session,receipt_identity=session,live_plan_sha256=plan_sha256,echoed_binding
pending-action: review .omo/plans/psi-complete-shared-tool.md
review:
  momus:
    status: complete
    workspace_root: /Users/iant1359/Develop/amis-review
    runtime_home: null
    target: .omo/plans/psi-complete-shared-tool.md
    round_id: 982B4112-288F-4485-B799-BC924461150C
    plan_sha256: 2d14a50e8543b8c3c243e88f801923234db168739d6fa21241ecd3ec19f85a8c
    launch_id: 054AD42D-DFC4-4CB1-B309-7D9F9AE482B4
    session: /root/momus_round_982b4112
    result: OKAY
  independent:
    status: complete
    workspace_root: /private/tmp/psi-plan-review.q8u5jk57
    runtime_home: /private/tmp/psi-codex-home.6uajlcza
    target: .omo/plans/psi-complete-shared-tool.md
    round_id: 982B4112-288F-4485-B799-BC924461150C
    plan_sha256: 2d14a50e8543b8c3c243e88f801923234db168739d6fa21241ecd3ec19f85a8c
    launch_id: B2A4FD82-B6C5-44BD-9416-249CF3EFF47F
    session: exec_command:92296
    thread: 01a04e77-b5d7-7a31-a69e-d3420d2e9d82
    result: ITERATE
approach: First lock the authoritative source and prove an offline deterministic PSI engine with fastexcel/Calamine and typed Polars against immutable golden fixtures; then add content-addressed provenance and Parquet replay artifacts, the governed Draft-review-publish workflow, RLS, a fenced durable worker, and production hardening in separately gated phases. Keep FastAPI, vanilla web, Supabase, and systemd; treat Excel as explicit ingest and final-consumer adapters; defer DuckDB unless end-to-end benchmarks show Polars alone misses the agreed SLO.
---

# Draft: psi-complete-shared-tool

## Review history
- Round `AAE40C6B-A771-4198-B115-AF63CE29C56A` bound descriptor-chain SHA-256 `50f5a126fb71e330a1644abbdc983fffb2f3cecc85e8f4c997e19df590d9e325`.
- Native Momus receipt `/root/momus_round_aae40c6b`, launch `03BE211D-098E-4E1E-8355-90D3BCD7E85D`: `ITERATE` for explicit UI-output dependency references and concrete happy/failure QA invocations.
- Independent receipt `exec_command:50870`, Codex thread `01a04e3b-3117-74e3-b727-fce6affa3539`, launch `D3A967D5-9848-42F5-8B48-8F89F40DEEE3`: `ITERATE` for git-index/protected-path safety, dependency consistency, exact state machines, least-privileged worker authentication, complete governance APIs/ownership, authenticated attestations, Excel precision bounds, killable native parsing, and final-SHA evidence order.
- Independent command: isolated `CODEX_HOME=/private/tmp/psi-codex-home.EXiidr`, workspace `/private/tmp/psi-plan-review.EVigVx`, `codex exec --model gpt-5.6-sol -c model_reasoning_effort="xhigh" --sandbox read-only`; no approval/sandbox bypass flag.
- Fix/retry summary: revised the plan to serialize all index/commit work and no-follow hash every protected path; reconciled all dependency edges; added authoritative Snapshot/Job/Draft transitions and one global slot; replaced runtime service role with non-bypass `psi_worker`; completed ownership/governance/activity APIs; bound Manual Check and baseline import to actor-authenticated hash/nonce attestations; added Excel precision bounds; moved native parsing to a killable resource-limited subprocess; moved final evidence after the final commit; made Todo-34 outputs explicit to Todo 38; and gave all 43 Todos literal happy/failure commands with observable verdicts. Structural/dependency validation passes; fresh two-lane retry is pending.
- Round `6D67783A-D307-4B87-B751-DAAFA63CA7FB` bound descriptor-chain SHA-256 `0312bb8eea40f13cab51a9b0f6cebec8a4182abbe6f569495f66c94d32046c36`.
- Native Momus receipt `/root/momus_round_6d67783a`, launch `671019FB-5191-40B7-9771-3FD299861E41`: `ITERATE` because F1 lacked a literal reviewer spawn plus bound-report assertion and F4 lacked a specific reviewer invocation plus executable status/authority assertions.
- Independent receipt `exec_command:96052`, Codex thread `01a04e4f-d2ad-7cb2-9acb-b6682c5a3d14`, launch `866508EA-B9B5-4540-9E11-A8D53947B4B0`: `ITERATE` for Todo-2/4 dependency mismatch, pre-edit staged-index handling, reviewed-plan identity drift, Todo-21 credential false-green, incomplete worker-token lifecycle, missing Admin baseline authorization surface, non-literal browser gates, evidence sealing order, and unproven retention/archive scheduling.
- Round-B fix summary: added a before-any-edit empty-index gate that preserves user staging; locked implementation to a protected dual-review receipt and rejects `PLAN_REVIEW_DRIFT`; made dependency reachability consistent; gave Todo 21 distinct complete/blocked/failure outcomes and resumable immutable evidence; implemented the worker identity contract with owned Supabase Auth issuance, Custom Access Token Hook, 300-second access tokens, password/refresh exchange, pending-to-active CAS rotation, epoch/session revocation, fenced lease fallback, and no runtime privileged key; assigned the exact Admin baseline RPC/repository/team API and exhaustive negatives; replaced browser prose with ephemeral-port Playwright/axe/CDP commands and hashed artifacts; defined backup/archive/retention timers, least-privilege roots, plan/apply revalidation, boundaries, and restore proof; and ordered final evidence as final commit -> authority -> release gate -> read-only preflight -> prereview index -> exact-bound F1-F4 -> post-review authority -> last-write approval index. Static validation passes for 43 Todos, 43 dependency rows, 43 literal happy/failure pairs, and F1-F4.
- Round `982B4112-288F-4485-B799-BC924461150C` initialized on descriptor-chain SHA-256 `2d14a50e8543b8c3c243e88f801923234db168739d6fa21241ecd3ec19f85a8c`; source and disposable copy `/private/tmp/psi-plan-review.q8u5jk57` match at 159,398 bytes. Fresh Momus and isolated independent review are pending launch.
- Round-C Momus launch `054AD42D-DFC4-4CB1-B309-7D9F9AE482B4` is in flight as `/root/momus_round_982b4112`. Independent launch `A1401810-0B80-404B-AED3-2337C1587CD1` exited before creating a thread because the disposable workspace is intentionally not a Git repository; replacement launch `B2A4FD82-B6C5-44BD-9416-249CF3EFF47F` uses only `--skip-git-repo-check` (no approval or sandbox bypass) and is in flight as `exec_command:92296`, Codex thread `01a04e77-b5d7-7a31-a69e-d3420d2e9d82`.
- Round-C Momus terminal receipt `/root/momus_round_982b4112`: `OKAY` unconditionally on the bound artifact; the independent lane remains in flight.
- Round-C independent terminal receipt `exec_command:92296`, Codex thread `01a04e77-b5d7-7a31-a69e-d3420d2e9d82`: `ITERATE` on nine executable blockers. It found invalid/over-concurrent F1-F4 orchestration and unavailable browser references; insufficient final-commit/evidence access for F1/F4; F3 launching after stack teardown; unowned late browser-driver flags; missing end-to-end browser auth/session/CSRF/XSS design; overbroad task-owned planning paths and no pre-edit ancestor collision gate; overwriteable/non-durable retry evidence; unbound reviewer invocation receipts; and a retention whole-apply atomicity promise without lock/epoch/journal plus incomplete backup lifecycle controls. Round C is invalid for approval and must be revised to a new SHA before both lanes rerun.

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->
C1 | Governed Excel ingest converts immutable source snapshots into strict typed Polars tables and, after the replay gate, content-addressed Parquet artifacts with schema/provenance metadata | active | `docs/PSI_PROCESS_UPTODATE.md:10-21`, `web/server.py:139-158`
C2 | Deterministic PSI engine implements CRM, Revenue, Inventory, Purchase, Pre-order, exclusions, mismatch, and the 17-sheet workbook contract | active | `docs/PSI_PROCESS_UPTODATE.md:23-170`, `psi_engine/manual_check.py`, `psi_engine/reconcile.py`
C3 | Supabase persistence governs reporting periods, source selection/carry-forward, jobs, mismatch history, Draft approval, and immutable Final releases | active | `docs/PSI_SHARED_TOOL_PLAN.md:65-146`, `supabase/migrations/20260722000100_psi_shared_mvp.sql:3-60`
C4 | Authenticated shared web workspace supports role/team-owned upload, progress, review, approval, provenance, and download through the canonical UI | active | `docs/PSI_SHARED_TOOL_PLAN.md:23-64`, `web/static/index.html`, `web/server.py:118-188`
C5 | A separately supervised database-backed worker executes durable, idempotent processing and workbook publication with observable stages | active | `web/server.py:69-114`, `deploy/psi-tool.service:1-11`, `scripts/run_wsl.sh:1-6`
C6 | Migration, regression, performance, browser, security, workbook, and deployment gates prove parity while preserving the dirty worktree and historical evidence | active | `test/test_manual_check.py:1-188`, `README.md:20-38`, current `git status --short`

## Open assumptions (announced defaults)
<!-- Intent is UNCLEAR: research resolves ambiguity, defaults are adopted (not asked), and each is surfaced in the plan's human TL;DR for veto. -->
<!-- assumption | adopted default | rationale | reversible? -->
Product boundary | The canonical product is the shared web dashboard; the legacy `/api/process` UI is retired or redirected, not maintained as a second product | `docs/PSI_SHARED_TOOL_PLAN.md` and current FastAPI routes define shared ownership; dual surfaces already diverge | yes
Data engine | Start with `fastexcel/calamine -> typed Polars`; Arrow is internal interchange, Parquet becomes a Phase-B replay/provenance artifact, and DuckDB is admitted only by a recorded benchmark decision if Polars misses the full-run SLO; no pandas | the 52,603-row corpus proves fast ingestion but does not justify two query engines from day one | yes
Excel boundary | Implement separate governed input and output adapters; business truth stays in typed tables, while OOXML validation plus native Microsoft Excel full-rebuild/open-save proves final compatibility | Excel and Manual Check are both input contracts, and LibreOffice/openpyxl alone cannot prove native Excel behavior | yes
Application stack | Keep Python/FastAPI, vanilla HTML/CSS/JS, Supabase, and Linux/systemd; do not migrate frameworks or add a frontend build chain | smallest change consistent with repository conventions | yes
Brownfield isolation | Phase 0 creates a reviewed code/fixture allowlist and immutable hashes before any build; development uses an isolated local/pilot v2 lane, while the production migration path is chosen only after read-only remote history/policy/bucket inventory | current migrations conflict, most product code is untracked, and a table prefix alone does not isolate Auth/Storage/service-role blast radius | yes
UI direction | Preserve the existing visual language, extract it into `DESIGN.md` plus reusable vanilla primitives, and expand functionality without aesthetic redesign | avoids an unrequested redesign while meeting the design-system and accessibility gates | yes
Reporting periods | Use cumulative inclusive `[2024-01-01, cutoff_date]` periods in `Asia/Ho_Chi_Minh`, with a display label, lifecycle state, and explicit `baseline_release_id`; do not invent week/month cadence | root code is weekly while older material is monthly; the approved plan locks the only proven boundary and selects the latest published smaller cutoff as baseline | yes
Source freshness | Require fresh CRM, Product, Revenue, Inventory; allow explicit reviewer-selected carry-forward Purchase/Target; require an approved Manual Check snapshot | matches `docs/PSI_PROCESS_UPTODATE.md:10-21` and removes the current seven-fresh-upload contradiction | yes
Job durability | Before Phase-C Draft workflows, use one serial stateless worker with `queued -> running -> succeeded|retry_wait|dead`, `FOR UPDATE SKIP LOCKED`, an incrementing bigint fence, a 300-second lease, 30-second heartbeat, three attempts, 5/30-second retry delays, content-addressed outputs, conditional finalize, and orphan recovery | a job table alone is not durable without exact stale-worker fencing and crash-window tests | yes
Rule authority | Manual Check remains the sole source for mappings, mismatch suppression, and exclusions; the UI reviews a frozen Draft but does not create a competing business-rule store | preserves the authoritative SOP boundary and prevents two divergent approval systems | yes
Workbook publication | Render a candidate, script native Excel CalculateFullRebuild/save-as/reopen to a new object, independently validate that object, freeze its checksum as the Draft, then review and publish those identical bytes without regeneration | business truth stays columnar while the reviewed object is already the native-Excel-accepted artifact | yes
Security boundary | User-facing reads/writes use actor-scoped JWT/RLS; secret/service credentials are worker/admin-only and never returned or logged | current service-role default bypasses RLS; official Supabase guidance reserves secret keys for trusted backend components | yes
Workspace safety | Treat existing workbooks, `input/`, `old_check/`, `outputs/`, `.tmp/`, `.codex-tmp/`, and unrelated tracked changes as immutable; product edits use an explicit allowlist and new evidence/output paths | current checkout is heavily dirty and untracked does not mean disposable | yes
AI boundary | AI may suggest classifications or draft evidence only; it cannot approve, exclude, mutate source truth, or publish | `docs/PSI_PROCESS_UPTODATE.md:168-170` | yes

## Findings (cited - path:lines)
- The shared FastAPI app is not runnable from the root checkout: `web/server.py:16` imports absent `psi_engine/engine.py`, and the documented direct `python web/server.py` command has no `__main__` server runner (`README.md:20-25`).
- The SOP requires four fresh official exports, carry-forward Purchase/Target when no new version is supplied, and a refreshed Manual Check; code requires all six sources plus Manual Check on every run (`docs/PSI_PROCESS_UPTODATE.md:10-21`, `psi_engine/config.py:3-5`, `web/server.py:69-72`).
- Pre-orders must be derived by stable `Order ID + canonical SKU`, and Manual Check is the only exclusion authority; Quantity/Net Value cannot enter permanent identity (`docs/PSI_PROCESS_UPTODATE.md:65-126`).
- The current SQL/API does not provide governed production security: most backend calls default to service-role access, authenticated actors can update arbitrary mismatch IDs, download is authenticated-only rather than object-scoped, and the migration has read-only RLS policies that the API bypasses (`web/server.py:24-41`, `web/server.py:167-185`, `supabase/migrations/20260722000100_psi_shared_mvp.sql:49-60`).
- Automatic latest-snapshot selection and in-process `BackgroundTasks` cannot implement explicit provenance, review, durable retries, or crash recovery (`web/server.py:66-79`, `web/server.py:139-178`; FastAPI background-task caveat: https://fastapi.tiangolo.com/tutorial/background-tasks/).
- The documented output is a 17-sheet workbook and the prior verified artifact is `outputs/01a0463d-f941-7740-a5b5-284cf85e0960/PSI_Final_27.08.2026.xlsx`; the provisional builder has a different reduced schema and the real engine is absent (`docs/PSI_PROCESS_UPTODATE.md:148-170`, `build_psi_workbook.mjs:3-8`).
- Only Manual Check has current root tests; engine, API, Supabase/RLS/Storage, worker, workbook, browser, and deployment acceptance are uncovered (`test/test_manual_check.py:1-188`, `requirements.txt:1-7`).
- Polars documents its Calamine/fastexcel reader as the fastest Excel ingestion route and recommends Parquet/CSV for processing; the local benchmark loaded all 17 sheets and 52,603 rows in 1.019 seconds (https://docs.pola.rs/user-guide/io/excel/).
- `openpyxl` never evaluates formulas, so formula correctness needs deterministic Python assertions plus a real calculation engine before release (https://openpyxl.readthedocs.io/en/3.1.2/simple_formulae.html).
- Fresh byte-level verification of `PSI_Final_27.08.2026.xlsx` found 17 sheets, 8,557 formula cells, valid ZIP/CRC, cached values for every formula, and zero independent formula/cache mismatches; however, the package has neither `calcPr` nor `calcChain`, so it does not prove that Excel performed a full recalculation.
- `input/PSI_Manual_Check.xlsx` is a mutable symlink into `outputs/`; it currently validates `PASS` with 117 exceptions, 104 active approved exceptions, 12 open cases, 397 active preorder exclusions, 4 order exclusions, and 16 mappings, but it cannot serve as immutable release provenance until copied and hashed as an exact snapshot.
- The checkout contains modified tracked files and many untracked user-data/product/evidence paths; a clean worktree would omit essential untracked source while in-place broad rewrites could destroy evidence.

## Decisions (with rationale)
- Split source locking into 0L and 0R. Gate 0L classifies authoritative product code, sanitized fixtures, immutable evidence, and scratch and hashes the approved allowlist before the offline engine. Gate 0R inventories remote Supabase state read-only and blocks only migration/product work.
- Delivery is staged with hard stop gates: A) offline engine and row-level golden parity, B) immutable ingest/provenance and explicit source resolution, C) shared Draft/review/publish plus RLS/UI, D) fenced durable worker and production hardening. No later phase begins while the prior gate is red.
- Build one governed shared tool, not an offline script plus a separate web prototype.
- Make canonical typed datasets and run metadata the source of computation; Excel remains a generated delivery format.
- Start with one compute engine: fastexcel/Calamine reads cell values, Polars performs typed normalization, filtering, joins, aggregation, windows, and stable sorting, and XlsxWriter owns only the output workbook. Use exact decimals, complete sort keys, and logical table hashes. Arrow stays an interchange detail; content-addressed normalized/result Parquet is mandatory from Phase B; DuckDB needs an explicit ADR backed by a reproduced Polars SLO or RSS failure before adoption.
- Use a durable database-backed worker rather than FastAPI process-local background tasks.
- Use explicit source selections and immutable Draft/Final provenance rather than silently selecting whichever upload is newest.
- Keep Purchase/Target carry-forward deterministic: use a valid current-period upload, otherwise the exact snapshot from the latest earlier published release, require explicit confirmation, and freeze the origin in the manifest.
- Separate team membership from workflow role; enforce both at the API and RLS boundary.
- Keep normalized analytical rows in private Parquet artifacts rather than duplicating them into Postgres; Supabase stores governance metadata, immutable object references, jobs, mismatch cases/occurrences, Drafts, Releases, and audit events.
- Publish points to the already recalculated, independently validated, reviewed Draft workbook checksum; it never reruns computation or rewrites the file.
- Preserve historical PSI files and derive regression fixtures/canonical contracts from them without editing them.
- Require TDD for each behavior boundary and agent-executed happy/failure QA; no human-only release criterion.

## Phase gates
- Phase 0L — local authority/fixture lock: emit a manifest with `path`, `sha256`, `role`, `authority`, and `allowed_use`; treat current SOP plus explicit plan amendments as normative business rules, the verified Final as layout/formula/style authority only, sanitized fixtures as executable evidence, root code as candidate, and provisional builders/scratch/output as non-authoritative evidence; inventory the operational WSL source read-only and reconstruct from contract plus expectations if it is unavailable.
- Phase 0R — remote boundary inventory: inspect migration history, tables, policies, buckets, Auth, retained data, secrets boundary, backup state, and capabilities read-only; it blocks only Phase C migration/product work, never the offline engine.
- Phase A — offline deterministic engine: build both Excel adapters and the typed Polars core; prove row-level normalized parity, business-grain totals, exclusion/mismatch invariants, 17-sheet semantics, repeat-run hashes, peak RSS, and full-run latency before any shared workflow work.
- Phase B — provenance: content-address raw copies and mandatory normalized/result Parquet, freeze exact manifests and baseline release IDs, add explicit Purchase/Target carry-forward, and reject unresolved symlinks.
- Phase C — governed product: provision a separately configured v2 Supabase pilot from the Phase-0R decision; add actor-JWT RLS, the minimal fenced serial worker and crash-window gates, native-Excel-before-Draft freezing, immutable Draft/review/publish, mismatch occurrence workflow, Manual Check proposal/upload handoff, durable in-app notifications, the preserved-style vanilla dashboard, and role/team/browser matrices.
- Phase D — operations: add API/worker systemd supervision, monitoring, staging migration/rollback, backup/restore, production read-only/canary smoke, and immutable release evidence. Any production mutation remains blocked on explicit external authorization.

## Hard acceptance
- Correctness: immutable sanitized fixtures across multiple periods; row-level normalized parity; totals by sheet/SKU/order; exclude disallowed warehouses then aggregate signed inventory by canonical SKU and retain net `> 0`; Revenue/CRM grain; `Order ID + canonical SKU`; whole-order exclusion across every affected sheet; carry-forward lineage; baseline-Final set-difference `NEW`; unresolved mismatches visible; Manual Check authority and PASS. Approved permanent exclusions require blank `Effective To`.
- Performance: on the pinned 52,603-row runner, Calamine ingest p95 <= 5 seconds, deterministic engine plus workbook write <= 60 seconds, peak RSS <= 2 GiB, native Excel gate <= 180 seconds, and repeated logical hashes identical. Phase A may tighten but not relax these values without an ADR.
- Workbook: exact 17-sheet schema/order/formula/style contract, byte/package checks, cached-value reconciliation to independent typed truth, error-token scan, rendered sheet inspection, and automated native Microsoft Excel full rebuild/save to a new file.
- Security/runtime: separate pilot Auth users, buckets, secrets and service role; local Supabase fresh-install and upgrade tests; Viewer/Contributor/Reviewer/Admin plus membership RLS and Storage negatives; concurrent upload/version races; exact fenced-worker transitions/timings; conditional approval/publish; durable notification dedup/read state; daily Postgres backup plus object manifest with 30-day operational retention and monthly immutable archive; staging restore, rollback, and production read-only/canary smoke.

## Post-approval Metis resolutions
- Period v1 is cumulative from `2024-01-01` through an inclusive cutoff in `Asia/Ho_Chi_Minh`. Product, CRM, Revenue, Inventory, and Manual Check are fresh for the cutoff; Purchase/Target alone may carry forward. Every source-specific business date is at or before the cutoff, and Manual Check effective dates are evaluated at the cutoff.
- Stable mismatch case identity is normalized `Source + Key + Issue`; values, descriptions, cutoff, and workflow annotations live only on immutable occurrences. `NEW` is the occurrence-set difference from the selected baseline Final, never a global-database-existence check.
- UI assignment, comment, acknowledged, and handled fields are workflow metadata only. They cannot suppress, exclude, map, modify PSI, or unblock a rule. The sole business-rule handoff is proposed Manual Check delta/export, external approval, immutable upload, validator PASS, then a new Draft.
- Source schemas are machine-readable and fix field types, nullability, decimal scale, rounding, overflow behavior, locale/date parsing, primary/business keys, and complete stable sort keys. Business arithmetic never uses binary float, and rounding occurs only at an explicitly contracted workbook boundary.
- Upload preflight hashes before parse and enforces `.xlsx`/OOXML content, 50 MiB compressed size, 500 MiB uncompressed size, at most 10,000 ZIP entries, 64 sheets, Excel row/column maxima, 10 million total cells, 100:1 compression ratio, and a 120-second parser budget. It rejects encryption, macros, external links, embedded objects, unsafe paths, duplicate headers, corrupt relationships, and missing required formula caches.
- Draft lifecycle is `building -> gate_failed|ready_for_review -> approved -> published`, with `superseded` terminal from any unpublished state. Each Draft freezes exact source IDs and hashes, Manual Check hash, baseline release, rule/schema/workbook versions, logical/Parquet hashes, native-Excel workbook hash, and gate report. Conditional approval/publish rejects stale state, superseded sources, or checksum changes and never recomputes.
- RBAC separates team membership from Viewer, Contributor, Reviewer, and Admin. Viewer reads governed outputs; Contributor uploads immutable snapshots for owned sources; Reviewer annotates occurrences and approves eligible Drafts; Admin publishes and manages membership; only the worker claims jobs and writes derived artifacts. User API calls always carry actor JWTs.
- Native Excel is a distinct macOS gate component: candidate checksum in, scripted full rebuild/save-as/reopen, input/output checksums plus Excel version report out, independent validation next, then Draft checksum freeze. No human click is part of acceptance.
- Zero-human QA covers automated tests, browser scenarios, native Excel scripting, recovery drills, and evidence capture. It does not replace real business approval or authorize production mutation.

## Scope IN
- High-performance XLSX ingestion, typed Polars normalization, benchmark-gated Parquet replay artifacts, deterministic PSI rules, Manual Check governance, workbook generation, source provenance, mismatch lifecycle, Draft/review/publish, RBAC/RLS, durable jobs, shared dashboard/workspaces, audit history, tests/CI, migration, deployment, observability, backup/rollback, and operator documentation.

## Scope OUT (Must NOT have)
- No pandas, Spark, distributed cluster, Redis, Celery, Kubernetes, microservice split, React/Tailwind migration, mobile app, direct AMIS/MISA API synchronization, AI auto-approval, source-workbook mutation, spreadsheet-grid editor, or destructive cleanup of historical/scratch files. No DuckDB until a full-run benchmark ADR demonstrates a concrete Polars-only SLO or memory failure.

## Open questions
- None blocking for the approval brief. The brief will surface the progressive data-plane choice, cutoff-date period model, Phase-0 source lock, and isolated-pilot/remote-inventory migration strategy for veto before plan creation.

## Approval gate
status: approved-for-plan
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->
