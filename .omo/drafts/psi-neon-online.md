---
slug: psi-neon-online
status: approved
intent: clear
classification: architecture
review_required: true
phase: ready_for_execution
plan_path: .omo/plans/psi-neon-online.md
plan_sha256: 69bea04330d97dc00b6261fa6dcbec76570ffae6663d2ec90e8d3c4da5bc2194
review_round_id: 39A34AC6-F005-47B1-A0E4-EC4BC4867D2A
round_status: approved
pending-action: run $start-work psi-neon-online
approach: Finish the verified Polars/Parquet PSI core, bootstrap an isolated preview foundation with a checksum-pinned cloud toolchain, then build and deploy immutable-digest FastAPI/worker/dispatcher/recovery-broker compute plus a separately privileged backup Job in Singapore. Neon Postgres/Auth provides governance and analytics; Google Cloud Storage holds files; the recovery broker alone holds the project-scoped Neon API key. A production-disabled-until-authorized two-task Cloud Run cutover guardian, private Power BI session and routing brokers, and two zone-disjoint private GCE Chromium session executors are live-proved in preview, then started and kept armed before the production consumer grant. Immutable Neon/GCS operation transfer and one fenced Neon-server clock prove the 900-second compensation-start bound after operator-host loss; automatic compensation is deliberately limited to Viewer removal, public-route disablement, per-member denial/sign-out, and a retained private deployment, while full restoration remains a separately authorized incident path. Users upload the weekly source set in the web app; FastAPI is the only browser control/database/Auth boundary, with one Origin-bearing browser-to-GCS XML-API resumable-upload data-plane exception whose application TTL, encrypted server-side cancellation capability, exact-URI cancellation, and orphan reconciliation are governed by FastAPI and proved live only after compute deployment. FastAPI starts PSI work, implements Draft-review-publish, and persists deterministic post-Final refresh/backup delivery intents. No Neon Data API, OneDrive, Graph, Cloudflare, Supabase runtime, Scheduler, or .codex-tmp authority.
review_history:
  - round_id: A5D59766-F573-48B2-9CDA-53E3321A27F1
    plan_sha256: 4976ed24e65a0ff2cf8a01927e737ad0f62e7989b1ad231145f16e367be75b0a
    status: reviewing
    momus_session: /root/psi_plan_momus_r1
    independent_session: 01a05960-4169-74a1-99e0-ea837a5726d7
    closure: "Resolved owner-gate semantics and executable QA; moved F1-F4 before production; rebuilt dependencies; added staged local-SQL BI promotion, durable Cloud Tasks delivery, exact actor separation, Power BI readiness hard stop, first-period/versioned idempotency, sanitized evidence schema, and formula-injection controls. The disposable-root repository finding was review-environment-only; round 2 names the actual source repository root explicitly."
  - round_id: B1220791-A761-4F6A-8F20-1F72A862ADBD
    plan_sha256: 379c2a1739421fb28c987e7b8ea073230f6f34f4e4e635f7b7ce80f1423a07a0
    status: changes_requested
    momus_session: /root/psi_plan_momus_r2
    independent_session: 01a0596c-413b-78d1-aa9c-d8b0446a7ae6
    closure: "Momus approved. The independent lane requested seven closures: direct dependency semantics, immutable aggregate evidence plus post-join receipts, persistent Cloud Tasks intent/exhaustion/OIDC contracts, separate backup identity and full restore scope, unambiguous snapshot/run dedupe, an exact Power BI toolchain/RLS/runbook, and hash-only owner-period evidence. All are incorporated for round 3."
  - round_id: 946ECA97-F356-41BA-B684-B190294E952E
    plan_sha256: d11da97479b86f87dc996f1a105a50da2b8d768a8aa2c694dfeae3cdb1223a29
    status: changes_requested
    momus_session: /root/psi_plan_momus_r3
    independent_session: 01a05980-564b-7201-bda6-758027f58894
    closure: "Momus approved. The independent lane found six remaining execution gaps. Round 4 aligns wave prose to the direct DAG; makes Power BI deployment then owner binding explicitly two-phase; commits Todo 40 before release-candidate/index freeze; adds Cloud Tasks exhaustion detection and generation-based replay names; backs up and restores all governance state plus immutable object bytes; and supplies literal workspace/Terraform preview commands. Todo 41 is now execution-only over code already committed and reviewed before the freeze."
  - round_id: 3130E4EC-6D7A-4988-89BF-C9D170B51842
    plan_sha256: 44f730b6992420eb6838d8fb7b2b36c956ec904c3d2db4b2ba5a3bb08a61db76
    status: changes_requested
    momus_session: /root/psi_plan_momus_r4
    independent_session: 01a05993-4500-78d2-afa8-8d29dd3cc99c
    closure: "Both review lanes independently converged on the same sole blocker: Todo 12 consumes the runtime/RSS SLO contract frozen by Todo 5 but lacked a direct dependency. Round 5 adds reciprocal matrix and todo-metadata edges from Todo 5 to Todo 12; neither lane reported any other blocker."
  - round_id: 1824D9F4-4536-4F12-93BA-4DEAFFDA848A
    plan_sha256: 5d70dc51d2e836bd9afdfc85e4af8409445105509c47cea3d39fa035d3c0d5cf
    status: changes_requested
    momus_session: /root/psi_plan_momus_r5
    independent_session: 01a059a5-e372-7253-8262-9d3710ef2805
    closure: "Momus approved. The independent lane found one remaining Power BI producer/consumer edge: Todo 33 deploys the PBIP/TMDL project created by Todo 32 but could run in parallel. Round 6 makes Todo 33 directly depend on Todo 32 and aligns reciprocal blocks, todo metadata, and wave prose."
  - round_id: 7C150417-BEE3-4DDE-81D9-CFAE4394E4F8
    plan_sha256: f2af2f6ddee087a12e98ec5c3b14bd7ca83592f3071dd580950877a70208c9ee
    status: changes_requested
    momus_session: /root/psi_plan_momus_r6
    independent_session: 01a059b2-8bc5-7733-9384-8eb1e035f9d3
    closure: "Momus approved. The independent lane found three gaps: pre-model Power BI Build/RLS receipts, the incomplete final-browser certification order, and omitted Neon Auth recovery. Round 7 moves model-scoped grants/receipts into Todo 33, orders Todo 29 -> Todo 35 -> Todo 30, and adds branch-based neon_auth recovery plus session invalidation and actor-link QA."
  - round_id: C3C4DF49-D96B-475A-8D14-B90721208AC1
    plan_sha256: 5b774ddabf1893545b7f4ec1d9d4ddb5614b1134e7d4bcd746d3798b937cec6c
    status: changes_requested
    momus_session: /root/psi_plan_momus_r7
    independent_session: 01a059c9-66da-7c73-aaf3-1f4d8ed05f9f
    closure: "Both lanes rejected the preview-infrastructure ordering. The independent lane additionally found no executable immutable-image producer, no pinned Terraform bootstrap, an impossible method-scoped Neon API-key claim, and missing worker/reconciler producer edges. Round 8 makes Todo 6 the pinned-toolchain/non-compute preview bootstrap, defers live compute acceptance to Todo 36, adds build-test-SBOM-scan-push-digest deployment and post-backup rebuilds, isolates the Neon key in a private recovery broker, and adds reciprocal 23/24 -> 36, 24 -> 33/38 edges."
  - round_id: 33012173-DB0C-459B-A613-ED1C3C95A70B
    plan_sha256: 3ca6067cfdd9fc62305c5d1cc6fb52edd454b4f06d7afba4640411128f2c9cdf
    status: changes_requested
    momus_session: /root/psi_plan_momus_r8
    independent_session: 01a059e6-3ae6-74e0-a563-95b3d7a7a810
    closure: "Both lanes required a durable migrated Neon preview prerequisite. The independent lane also found missing 33 -> 36 and 38 -> 37 semantics, incomplete pinned build/provider commands, an unbound Cloud Tasks retry contract, impossible PBIP Desktop data rendering, overstated GCS manifest/generation IAM and ambiguous dump encryption, image/release-candidate drift, and prose-only external QA/final gates. Round 9 adds the durable branch/Auth/secret bootstrap, direct DAG edges, stable queue-level policy hash and four-part exhaustion predicate, Service-only data rendering, prefix IAM plus application generation checks and CMEK, commit-before-build/image-context finalization, and literal preflight/command/agent receipt protocols."
  - round_id: 300A1A74-FB1D-442D-840F-C8941243C4A0
    plan_sha256: d8483e4606e9958dd0d31737649cf922b3a691c1c2e05f7e8c6507016272ebe4
    status: changes_requested
    momus_session: /root/psi_plan_momus_r9
    independent_session: 01a05a05-11dd-7520-8335-f40c0b4e1466
    closure: "Momus found stale Todo 12 images and a prose-only Todo 35 browser gate. The independent lane additionally found stale Todo 37 telemetry deployment, precommit provider evidence, inconsistent image-context/final-gate producers, no post-mart migration/governed sanitized Final before Power BI, incomplete ordinary-consumer RLS and membership-change safety, non-provider-derived Cloud Tasks terminal evidence, missing GCS UBLA/effective-grant prerequisites, and backup ordered before production foundation. The next round uses per-task committed images, postcommit evidence, canonical allowlist/generated manifests, Todo 31 successor schema/Final receipts, consumer-group plus suspend-refresh-reinstate RLS lifecycle, provider first-dispatch/count observations, UBLA policy-v3 conditional IAM, and foundation-before-backup cutover phases."
  - round_id: 721C732F-AD9C-4766-91E1-BDB46FAB201F
    plan_sha256: 73d2287a375836cb1fe59e0ba8537186bbf7f82592460053df34798e81a0763e
    status: changes_requested
    momus_session: /root/psi_plan_momus_r10
    independent_session: 01a05a1c-7a83-71c1-8916-85fbe146f4fc
    closure: "Momus required fail-closed sanitized-preview provenance, a dedicated Cloud Tasks FULL-view reconciler, timeout-safe Neon recovery-branch creation, and clean-SHA Power BI/Windows QA. The independent lane additionally required postcommit Todo 12 benchmarks, explicit QA consumer-group membership and complete grant suspension, a fixed backup-manifest producer, a Todo 34 ZIP producer, correct CMEK metadata semantics, callable supported-field four-lane orchestration, and literal ordered production cutover commands. Round 11 incorporates all eleven closures with a separate classified preview project/parent receipt, responseView=FULL IAM allow/deny proof, durable deterministic branch-operation reconciliation, commit-bound Todo 12/32/34 evidence, QA group membership and full revocation lifecycle, fixed backup/Power BI artifacts, kmsKeyName/CryptoKeyVersion evidence, a no-overwrite orchestration wrapper, and explicit foundation -> backup-or-waiver -> migrate-deploy -> Power BI -> canary commands."
  - round_id: 06AB1AB8-D5C9-4F18-B67C-AF5D6BA2E570
    plan_sha256: 4f75699ae31f3121fbf00c58102c8fe764f55df2431ecae5c2fcd4c75ef88d8c
    status: changes_requested
    momus_session: /root/psi_plan_momus_r11
    independent_session: 01a05a2d-7571-7871-bf57-86bd84f8e8f7
    closure: "Momus approved. The independent lane found seven execution gaps: four child lanes exceeded the declared total concurrency, the FULL-view reconciler lacked a runnable surface, production traffic opened before Power BI/canary gates, actual QA security-bridge rows lacked an exact pre-refresh producer, production current-Final/empty-model state lacked an exact producer, the Todo 36 toolchain receipt was precommit, and Desktop Bridge evidence overstated its supported methods. Round 12 requires five total/four free child slots; adds a private one-task delivery-reconciler Job with narrow invokers; keeps public traffic disabled until the sole finalize switch; supplies separate preview and production QA-bridge producers plus direct production-state capture; makes the authoritative toolchain receipt postcommit and context-bound; and limits Desktop Bridge to documented open/status/reload/manifest compatibility while static validation owns topology/binding/format proof."
  - round_id: 0C9A4F0D-95B6-48F6-9DB2-B97F69F76C84
    plan_sha256: 82a893fc3efcb3b61ee3fba50e7fd415b30fe729e0ba1ac1577454796fb6b759
    status: changes_requested
    momus_session: /root/psi_plan_momus_r12
    independent_session: 01a05a40-a352-7720-98c3-3f81d9d2e46a
    closure: "Momus approved. The independent lane found eight remaining execution gaps: the four-child gate exceeded a four-slot substrate, F2 depended on unproduced OMO skills, F3 and F4 raced on one mutable pilot environment, production granted the consumer group before finalize, publication lacked an immutable Final-object producer, backup could not read/adopt a destination after uncertain create, cutover lacked an executable disable-first rollback, and retention evidence proved IAM denial rather than provider Bucket Lock. Round 13 uses coordinator-local F1 plus three children; committed review/runtime procedures; a disposable sanitized F3 sandbox with zero-remnant cleanup while F4 reads the pilot only; QA-only pre-final Power BI access; create-only verified Draft-to-Final materialization; destination-prefix create/get with timeout/412 adoption; rollback-ready plus incident-authorized terminal rollback; and exact owner-authorized GCS lock/readback receipts for preview and production."
  - round_id: 95560FFC-1A1E-40E6-9454-C3F981AD4300
    plan_sha256: e052d5cb9ebcdacc4a456a218e4ae80c3e4628748921b03c9f796445f678519d
    status: changes_requested
    momus_session: /root/psi_plan_momus_r13
    independent_session: 01a05a66-05f0-7893-8165-647d94ed5e56
    closure: "Momus approved. The independent lane raised eleven production-boundary findings. Round 14 makes F3 terminal only after cleanup; preserves the official Cloud Tasks BOTH-bound exhaustion contract with current Google documentation rather than adopting the lane's incorrect either-bound claim; creates a frozen recovery branch plus common exported snapshot and ephemeral branch-only BYPASSRLS dump role; blocks the next Final until the preceding full backup validates; adds CMEK version-lifetime/authority/rotation controls; separates finalize-only automatic compensation from incident rollback; quarantines locked bytes on empty rollback and retires the empty baseline after the first protected backup; freezes an exact two-path Todo 40 commit and all Todo 39 execution-input hashes; uses encrypted versioned locked remote Terraform state; revokes QA and grants/read-backs consumer workspace, RLS, and app audience only in finalize with an empty-audience owner publication path; and gates production on DNS ownership, active TLS, disabled routing, and a restorable prior-routing baseline."
  - round_id: 5EC26BF2-6CBA-421C-B4E5-BF3708C8A229
    plan_sha256: fe018f672d7c7cf65bd556df5e14e2a9a34b7a548a0d4aae3355c42874bc4920
    status: changes_requested
    momus_session: /root/psi_plan_momus_r14
    independent_session: 01a05a7d-8ec0-7c73-a52b-046bda7e2d8b
    closure: "Both lanes requested a six-group closure. Round 15 excludes the previously absent Todo 40 evidence-contract path from Todo 39's expanded file-hash manifest and validates it separately; keeps Todo 14 backup-export work policy/fixture-only while Todo 38 owns the live frozen-branch BYPASSRLS proof; provisions F3 with a complete frozen-digest compute/data overlay, production-forbidden disposable backup mode, persist-before-create ledger, and cleanup/seal on every outcome; adds the missing Power BI tool locks, environment mappings, operator runbook, and full execution-input set; gives Terraform state an exact 90-day version/CMEK recovery horizon with rotated-key prior-generation restore; and adds all eleven reciprocal direct producer-consumer edges requested by the independent lane."
  - round_id: E00741F1-AC2A-4010-9E02-6B01F71A1CFA
    plan_sha256: 876584e43f2e9e7c4d7c6d7658173756c2fda8a248eeaa8b6861d6ef6445e9d4
    status: changes_requested
    momus_session: /root/psi_plan_momus_r15
    independent_session: 01a05aac-88cc-7b23-8c76-6b5782df8c34
    closure: "Momus approved. The independent lane found nine remaining execution gaps. Round 16 freezes the F3 descriptor before provider creation and receipts provisioning failure through cleanup/seal; replaces unsupported app/RLS mutations with owner-portal QA-only app and RLS setup plus Groups-API-only Viewer activation/removal; makes one Terraform state-ready receipt a live-revalidated prerequisite and propagates production recovery through every phase; adds Todo 40 no-mutation target preflight and frozen inventories; restores password-free global roles before pg_restore into an independently empty target; gives the broker the child-admin lifecycle while backup receives export-only credentials denied on primary; makes live context/Auth receipts mutation gates; defines at-least-90-day recovery with day-90 deletion eligibility, soft delete, and CMEK through irrecoverability; and retains an intentional Python 3.12 fabric-cicd isolation pin. That round still cited an incorrect wider package range; Round 18 corrects the current Microsoft-documented range to 3.9-3.12."
  - round_id: 9C28AC28-0824-47AC-AB4E-D28D7912F18E
    plan_sha256: 97ec0e840d056ee4d81568bedce835da25cfd38409cf41e313a4f772e4edec59
    status: changes_requested
    momus_session: /root/psi_plan_momus_r16
    independent_session: 01a05ac8-8c16-7d72-9cfa-d0a258b54bfc
    closure: "Both lanes requested changes. Round 17 replaces Todo 3 narrative QA with literal command/exit gates; adds the missing Todo 22 -> 26 edge; pins checksummed PostgreSQL clients in the host toolchain and image, records server_version_num, and live-tests the child-only non-admin BYPASSRLS export role in preview and production; creates the immutable Todo 14 aggregate receipt; adds Power BI no-mutation target preflight, delegated workspace-admin Groups-API producer, receipt-derived IDs, and moves imported-content equality to Todo 34 delegated queries; gives preview and production restore separate owner-authorized empty-project/restore-identity receipts; freezes a complete operation-ID-bound pilot delta schema consumed by finalization/F3/F4; and splits production state into state-only A0 recovery verification before A1 creates any other resource or retention lock."
  - round_id: AC8AD3C3-40F2-40AF-8DBA-B43E24188588
    plan_sha256: c9f564a5a733faac5a9b88e3abeb99714f57a3611d428da867fd9c06eedaa28c
    status: changes_requested
    momus_session: /root/psi_plan_momus_r17
    independent_session: 01a05ade-7e07-7440-b8f8-099d2093b71d
    closure: "Both lanes requested changes. Round 18 adds the direct Todo 5 -> 6 policy edge and orders state bootstrap, secret containers, secret versions and client checks; defines FastAPI control-plane plus one origin-bound direct-GCS upload exception; handles Terraform backend fallback state and retained F3 state tombstones truthfully; creates the generic per-todo QA/receipt producers; adds production-specific Auth inventory/config/live authority; gives recovery targets remote-state-backed Neon Auth/database plus GCP/GCS authority and strict source-target-client compatibility; derives every pilot delta category and data-dependent expectation from a pre-mutation engine run; corrects fabric-cicd support to Python 3.9-3.12; budgets all eight shared-capacity refresh requests; and gates Power BI changes on effective fresh-session access rather than Groups readback."
  - round_id: 43DD6B16-F747-44B2-BCD4-04702F167F31
    plan_sha256: 0b4828fc2c1119e1834710892e5e29a6f515725943252fd60ba5c3819eca6e39
    status: changes_requested
    momus_session: /root/psi_plan_momus_r18
    independent_session: 01a05b04-4579-7702-b998-55908e7b8a63
    closure: "Both lanes requested changes. Round 19 reserves task-N-psi-neon-online.json exclusively for the aggregate builder and gives every surface producer a semantic receipt; integrates Todo 40 through a committed exactly-once precommit manifest and a postcommit hash-import phase that cannot replay provider mutations; stores the GCS resumable URI only as an envelope-encrypted cancellation capability, schedules exact-URI cancellation, and models uncertain initiation/pending cancellation truthfully; changes Todo 20 QA to allow browser-to-FastAPI while denying direct Neon/Data-API/non-upload provider calls; replaces whole-schema-empty Neon Auth restore with an empty-identity/bootstrap-allowlist/portable-data merge that preserves target config/JWKS and omits sessions; wraps preview, restore-target, and production Auth POSTs in persisted at-most-once intents plus GET reconciliation; and gives both Power BI QA identities explicit owner-delegated, isolated BrowserOS session preflight, per-user permission refresh, fresh-sign-in, and sign-out receipts."
  - round_id: 9BA8E9F5-E012-4955-9E7F-207B1414121A
    plan_sha256: db9092ef19330ca6c5bc80362baf6d0358f322c397f7bb0eee994eebb3584ad7
    status: changes_requested
    momus_session: /root/psi_plan_momus_r19
    independent_session: 01a05b23-3ac4-7f80-b12b-27748201ce7c
    closure: "Momus approved the immutable plan. The independent lane found five execution gaps. Round 20 pins browser resumable uploads to the Origin-enforcing GCS XML API and moves live cancellation proof after deployed compute; orders Power BI binding validation, first refresh, delegated Read+Build/RLS proof, then final binding; extends owner-delegated secret/session/sign-out authority through Todo 34 and every production permission propagation or revocation path; and splits production Neon Auth into ACTIVE GET-only adoption versus ABSENT_EMPTY persisted-intent at-most-once enablement."
  - round_id: CBB2AB20-005A-4238-B672-86FF5081FD15
    plan_sha256: 399b181000d06521a0fc3bc38baee6c6dd6e7651ff8cd371aa1611bc8b29ed91
    status: changes_requested
    momus_session: /root/psi_plan_momus_r20
    independent_session: 01a05b35-8414-7072-bb84-99abf83e5d29
    closure: "Both lanes requested changes. Round 21 deletes the stale Todo 33 verify-binding QA path and makes the exact five-command binding producer sequence sole authority; separates production end-user access proof from workspace-admin mutation authority; makes QA Build/workspace removal an explicit admin-mutation/readback plus per-user propagation chain; prefunds automatic compensation with hash-bound unexpired admin, user, and session-revocation authority before any grant; and provisions checksum-bound, refreshed, deterministic consumer-canary bridge rows, including a non-business control-row rule for empty deployment."
  - round_id: E7995DA1-15CA-4DCB-8F29-29718FFB751C
    plan_sha256: bc01c4b4d4914b60c6f728a2a949694aac38cc26985fa2cc9d206587a1f082b3
    status: changes_requested
    momus_session: /root/psi_plan_momus_r21
    independent_session: 01a05b44-916c-7c92-bf8d-5086ef707603
    closure: "Both lanes requested changes. Round 22 removes the final stale Todo 33 binding token and makes Todo 33 a resumable owner-handoff workflow; requires fresh workspace-Admin preflight, mutation readback, ledgers, and sign-out across Todos 33, 34, 39, and 41; separates prefrozen automatic compensation from fresh incident-triggered rollback authority; classifies preview and recovery-target Neon Auth as ACTIVE GET-only or ABSENT_EMPTY at-most-once POST; checkpoints and resumes the one-week GCS expiry canary without replay; and adds an exact Todo 41 terminal seal, canonical aggregate receipt, and separate Todo 1-41 operational index."
  - round_id: 84D617EF-50FC-415C-9C4D-173AC61E0786
    plan_sha256: 0a91575386b34439bf65bfc768f1ba9cb4debb975a94a72d13f102d483f5074a
    status: changes_requested
    momus_session: /root/psi_plan_momus_r22
    independent_session: 01a05b63-dc5a-7dc1-a48f-96656cfbcdf6
    closure: "Both lanes requested changes. Round 23 makes Todo 39 a manifest-bound setup, E2E, teardown, and one-week-resume workflow with separate Admin and delegated-user authority; forces downstream tasks to consume Todo 34's canonical aggregate plus bundle hash; gives Phase D an explicit QA effective-access producer; expands incident-triggered Power BI preflights; classifies direct production Neon Auth as ACTIVE GET-only or ABSENT_EMPTY at-most-once POST; creates a real automatic-compensation execution receipt; supports finalize-only, automatic-compensation, and finalize-then-incident-rollback terminal models; and creates Todo 41 phase journals before seal with gates/handoff-bound operational import and final index validation."
  - round_id: 8D23F2B1-01CF-47E9-816E-79F033187C20
    plan_sha256: ee222d5fa3f2831448b47455429a1b163d7b86bd36dbb056b05b265f8bea183b
    status: changes_requested
    momus_session: /root/psi_plan_momus_r23
    momus_result: OKAY
    independent_session: 01a05b7e-4fb3-7413-bf52-39b9b5602385
    independent_result: ITERATE
    closure: "Momus approved. The independent lane found one remaining authority gap: automatic compensation claimed Power BI baseline restoration while its admin preflight and frozen command authorized only Viewer removal and readback. Round 24 gives the auto-compensation lane its own pre-grant authority for binding, RLS, and QA-app restoration; freezes the reviewed Power BI baseline and exact restore operation list; requires real execution readbacks, admin sign-outs, delegated denial sessions, and terminal-seal hash validation; and rejects incident-authority reuse or any missing, reordered, or wrong-target restore."
  - round_id: 60A31418-BB26-4922-91CB-01D4B4B75115
    plan_sha256: 556baf7773828adcf2bd096ffed480c4111f9c5478664ff64a006e6c204cf199
    status: changes_requested
    momus_session: /root/psi_plan_momus_r24
    momus_result: ITERATE
    independent_session: 01a05b8a-6aa2-7fc1-bc1e-dd7a5271ec12
    independent_result: ITERATE
    closure: "Momus found that the sole exact terminal-seal argv omitted the restoration-evidence flags declared one line earlier. The independent lane found that prefrozen auto-compensation authority ended at the finalize deadline even though denial can require an hourly refresh window, a bounded retry, propagation, restoration readbacks, and sign-outs. Round 25 replaces all older auto-compensation deadline semantics, freezes a distinct 8520-second compensation horizon after a bounded grant window, validates all authorities through that deadline, refuses late grants, requires completion by the deadline, and supplies one full exact seal argv with every baseline, readback, restored-component, sign-out, and deadline flag."
  - round_id: AA1E553C-8318-4667-B29F-23465A1C477F
    plan_sha256: dce949abdcd9fd6f5044af270283b85bb6aa44df844db2d1e59e86aeecd7c9dc
    status: changes_requested
    momus_session: /root/psi_plan_momus_r25
    momus_result: OKAY
    independent_session: 01a05b96-7a0d-7c61-9f49-2683db2bd34f
    independent_result: ITERATE
    closure: "Momus approved. The independent lane found that the standalone grant-window command was contradictory because it was ordered twice with no-overwrite while the actual grant did not consume it, and that Phase F still used the obsolete finalize-deadline flag. Round 26 makes one guard internal to the manifest-owned grant-and-prove process immediately before the Groups API call, records and hash-binds its actual call-start boundary, and fully replaces rollback-ready so it consumes and hash-binds the compensation deadline plus all prefrozen compensation authorities."
  - round_id: 927D4719-CFE2-4306-81E5-29FFF42EB1A4
    plan_sha256: 0d8f8cffbf073f24b17a7cccaebad0e57311dded3ab84141fc664660360deb28
    status: changes_requested
    momus_session: /root/psi_plan_momus_r26
    momus_result: OKAY
    independent_session: 01a05b9f-d0f2-7eb0-ae86-897a80d9da57
    independent_result: ITERATE
    closure: "Momus approved. The independent lane found that the compensation deadline did not reserve bounded time for post-grant finalize failure before the 8520-second rollback horizon, and that group-wide Viewer mutation had evidence for only two canaries without proving they were the whole group. Round 27 adds a 900-second bounded partial-finalize budget plus durable pre-grant watchdog, checkpoints every post-grant step, and constrains the initial production cutover group to exactly the two direct verified human canaries under an immutable membership freeze; broader audience rollout is a separate future authorized attempt."
  - round_id: 895EA4E8-833D-4375-BD62-F690F0D3810D
    plan_sha256: e86d9c16cb7e1f559f637747ae2b7fef915ac732d346dec6e40015bac3b52e7e
    status: changes_requested
    momus_session: /root/psi_plan_momus_r27
    momus_result: OKAY
    independent_session: 01a05bac-6fea-7e13-959e-366acf1afb56
    independent_result: ITERATE
    closure: "Momus approved. The independent lane found that public enable/finalize/watchdog disarm could precede the exact terminal membership and per-member evidence readback, and that an operator-process watchdog plus Cloud Tasks could not independently execute or prove the 900-second compensation-start bound after host failure. Round 28 moves candidate-bound exact-two-member and session-child validation before public enable while the watchdog remains armed, and provisions a two-task independently running Cloud Run guardian with fenced Neon/GCS state, private Power BI session broker, scoped IAM/secrets, failover canary, and no Cloud Tasks timing claim."
  - round_id: 51E1EAEB-4E68-4202-BE4A-59B5F78B0131
    plan_sha256: afa9587d91bc3301045c757cf7fdd71221b2f6a3697f230fc4a4ed93d2f82f41
    status: changes_requested
    momus_session: /root/psi_plan_momus_r28
    momus_result: OKAY
    independent_session: 01a05bc2-5c11-7c00-b00c-ef11c175f4f5
    independent_result: ITERATE
    closure: "Momus approved. The independent lane found six execution gaps: nonexistent Todo 36 receipt inputs; guardian/broker omission from image, deploy, rebind, inventory, and F3 surfaces; automatic-restoration claims beyond guardian IAM/capability; no host-independent Power BI browser/session executor; no immutable operator-to-guardian transfer protocol; and a 900-second proof based on incomparable host clocks. Round 29 corrects the receipt producers, propagates the complete compensation-aware workload set, adds a narrowly scoped routing broker plus two private zone-disjoint GCE Chromium executors, limits automatic compensation to access revocation/private routing, publishes and registers a generation/hash-bound Neon/GCS operation bundle consumed by operation ID only, imports terminal receipts by immutable generation, and proves grant/compensation call starts from one fenced Neon server clock with transaction/LSN and wrapper-dispatch evidence."
  - round_id: CBD98E60-2637-4014-A4CF-7C76F86ECCE1
    plan_sha256: a7f5d6ed736fd76be6ee8918974920eb490a7b7f3c04f56d682be62ff724f9df
    status: changes_requested
    momus_session: /root/psi_plan_momus_r29
    momus_result: ITERATE
    independent_session: 01a05bdc-0460-74e2-a6c5-a706d643a9c3
    independent_result: ITERATE
    closure: "Momus found two conflicts: the obsolete Round 28 guardian smoke remained executable and F3 did not enforce two private zone-disjoint browser executors. The independent lane found seven more: Todo 39 expiry output collision and an incomplete terminal-validator argv, stale mandatory terminal candidates, conflicting full-restore auto-compensation/seals, incomplete two-executor provider evidence, a guardian runtime that depended on uninstalled rtk/uv tools, and an ambiguous signed-download boundary. Round 30 makes every superseded auto-compensation/seal paragraph historical and non-executable, defines one installed-Python access-only guardian command plus one safe terminal seal while reserving full restore for fresh incident authority, separates Todo 39 producer paths and binds every receipt into its terminal validator, makes terminal candidates optional, enforces two no-public-IP zone-disjoint executor instances with digest/identity/audience/mTLS/disk/endpoint readback through Todo 40 and F3, verifies direct runtime dependencies in every image, and serves authenticated downloads through FastAPI without exposing a GCS signed URL."
  - round_id: 4E57FC6B-8739-440C-9589-3F3578E3B731
    plan_sha256: 826ad63a7654441f5cc15a0d3ab2fb511a7f03dda77ea739b3af2c97b641b445
    status: changes_requested
    momus_session: /root/psi_plan_momus_r30
    momus_result: ITERATE
    independent_session: 01a05bf4-7e12-7672-ada2-a93c94315860
    independent_result: ITERATE
    closure: "Momus found three executable-flow conflicts: competing Todo 39 merge/direct-E2E paths, a local-secret-map automatic-compensation producer, and BrowserOS-local finalize despite the private GCE executor architecture. The independent lane found five more: incomplete Todo 40/F3 provider readback, orphaned F1-F4 validation receipts, deploy before production Auth-live validation, no executable operation-ID transfer into a fixed guardian Job, and a guardian-terminal output collision plus no unambiguous FINALIZE_ONLY success validator. Round 31 makes the Round 23 phased Todo 39 flow sole authority; routes production session work through the broker and two inventory-bound private executors; creates one access-only, no-local-secret compensation preparation and rollback-ready path; binds full guardian/executor readback in Todo 40/F3; feeds all four validation receipts into join, bundle, and bundle validation; splits Phase C into migrate-only, Auth configure/live, then deploy-workloads; makes the fixed guardian discover exactly one fenced ARMING operation without overrides; and separates finalize-live, auto-safe, finalize-disarm, and imported-compensation terminal receipts."
  - round_id: BEB9E2CB-F946-48C2-98BF-5F688F3D2231
    plan_sha256: b036635161763dd1f1760477f3cd619fec1a59a4c4f813f9c7275cdb5ef77dbb
    status: changes_requested
    momus_session: /root/psi_plan_momus_r31
    momus_result: OKAY
    independent_session: 01a05c36-9d3f-7af2-a5f7-2d9fca6c3470
    independent_result: ITERATE
    closure: "The independent lane found three live-path gaps after Momus approved: the pre-Auth inspection consumed the post-Auth deployment receipt and formed a Phase-C cycle; the guardian bundle required a restoration baseline produced only by historical commands although automatic compensation is access-only; and incident/group/browser session paths plus guardian slot import were not uniformly inventory-bound to the two private executors. Round 32 makes migration and prebackup state the sole pre-Auth inputs, binds both Auth branches into configure/test, removes the obsolete baseline from the live bundle, resolves opaque slots only from production inventory, and routes incident plus initial membership sessions through the broker and two inventory-bound private executors with local BrowserOS/secret maps forbidden."
  - round_id: 21824E28-77DA-4FDA-B469-539C2686F155
    plan_sha256: 943fc91a86d8aa5e450db158d7d81807e1789f1684080e0eae8cadda5bb3817c
    status: changes_requested
    momus_session: /root/psi_plan_momus_r32
    momus_result: OKAY
    independent_session: 01a05c43-31da-72c2-8cf8-2fd7e4914cd2
    independent_result: ITERATE
    closure: "The independent lane found two remaining session-topology gaps after Momus approved: pre-guardian Phase-D/group commands requested opaque slots from the guardian bundle that itself was published only after Phase E and rollback-ready, creating a cycle; and the sole literal producer of the shared Phase-D admin preflight still used a local BrowserOS/secret-map path. Round 33 creates and live-proves an immutable session-executor registry immediately after workload deployment and before any session action, makes the later guardian bundle consume that registry, routes every live production session command through it, and adds one exact brokered two-executor Phase-D admin-preflight producer while declaring the local Round 21 producer wholly Historical."
  - round_id: BDA202A3-01C9-4CB0-9E64-74D176C0F103
    plan_sha256: 1d8163fc014e00e571896d0fb287eba8206f1aaae94716eed4c561b375aeb1fc
    status: changes_requested
    momus_session: /root/psi_plan_momus_r33
    momus_result: ITERATE
    independent_session: 01a05c4b-56dd-7722-8fd5-fc789be6616b
    independent_result: ITERATE
    closure: "Momus found two stale live raw Todo-34 ZIP arguments and one access-only slot-resolution flag bypassing the new registry. The independent lane additionally required executable Todo 36/39 registry production and validation, complete executor inventory fields, broker/registry inputs on deploy-only/security-refresh/canary, removal of remaining live BrowserOS/secret-map wording, all-terminal executor cleanup, and direct F1-F4 lane-receipt inputs to the final validator. Round 34 closes all eight findings with canonical task-plus-bundle artifact resolution, mandatory preview registry receipts, complete endpoint/mTLS inventory, registry-only slot authority, brokered session inputs on every named command, one cleanup receipt for all terminal models, and direct lane plus validation receipts at join/build/validate."
review:
  momus:
    status: approved
    workspace_root: /Users/iant1359/Develop/amis-review
    runtime_home: null
    target: .omo/plans/psi-neon-online.md
    round_id: 39A34AC6-F005-47B1-A0E4-EC4BC4867D2A
    plan_sha256: 69bea04330d97dc00b6261fa6dcbec76570ffae6663d2ec90e8d3c4da5bc2194
    launch_id: 35D6D189-B80C-4056-8B80-6C31BC6847F7
    session: /root/psi_plan_momus_r34
    result: OKAY
  independent:
    status: approved
    workspace_root: /private/tmp/psi-neon-review-r34.CVIWpy
    runtime_home: /private/tmp/psi-neon-codex-home-r34.yWEdST
    source_repo_root: /Users/iant1359/Develop/amis-review
    target: .omo/plans/psi-neon-online.md
    round_id: 39A34AC6-F005-47B1-A0E4-EC4BC4867D2A
    plan_sha256: 69bea04330d97dc00b6261fa6dcbec76570ffae6663d2ec90e8d3c4da5bc2194
    launch_id: 4FA15F1B-2FA5-4B12-89E7-71127C8A7000
    session: 01a05c57-6173-7851-9f8f-23f16cb55395
    result: OKAY
---

# Draft: psi-neon-online

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->
C1 | Canonical deterministic PSI engine produces the governed 17-sheet workbook from pinned source snapshots with Manual Check and prior-release parity | active | `src/psi_tool/`, `tests/psi_tool/`, `docs/PSI_PROCESS_UPTODATE.md`
C2 | Google Cloud Storage stores directly uploaded raw XLSX, Parquet relations, Draft, validation report, and Final by checksum without overwrite | active | `web/server.py:81-110`, `docs/PSI_SHARED_TOOL_PLAN.md:89-135`
C3 | Neon Postgres stores auth-linked profiles, periods, source selections, jobs, mismatches, approvals, releases, BI marts, cancellation intents, and audit events with versioned migrations and RLS; FastAPI is the sole browser control/database/Auth API, while upload bytes alone use an Origin-bearing GCS XML-API resumable session with a short application TTL and encrypted server-side cancellation capability | active | `.neon`, `supabase/migrations/20260722000100_psi_shared_mvp.sql:9-60`
C4 | FastAPI plus the shared browser workspace implements login, team-owned upload, dashboard, mismatch review, approval, publish, rollback pointer, and authorized download | active | `web/server.py:119-188`, `web/static/index.html`, `web/app.js`
C5 | A separately supervised durable PSI Job leases idempotent runs, survives crashes/retries, validates workbook bytes, and stages only a governed Draft; deterministic Cloud Tasks deliveries handle post-commit refresh/backup work | active | `web/server.py:69-114`, `deploy/psi-tool.service`, `docs/PSI_SHARED_TOOL_PLAN.md:78-102`
C6 | A checksum-pinned cloud toolchain, isolated non-compute preview bootstrap, immutable image pipeline, separate backup Job/identity, key-isolating recovery broker, two-task cutover guardian, private Power BI session/routing brokers, two zone-disjoint private browser executors, immutable operation transfer, one fenced Neon-server clock, durable access-only compensation state, secrets, observability, backup/restore, migration/cutover, dirty-worktree safety, and end-to-end QA prove the online service | active | `.neon`, `deploy/`, `tests/psi_tool/`, current `git status --short`
C7 | The web upload flow accepts one explicit weekly source set, validates source type/week/schema/checksum, uploads through the exact Origin-bound GCS XML resumable endpoint, and starts exactly one PSI run | active | `web/server.py:81-147`, `docs/PSI_SHARED_TOOL_PLAN.md:36-54`
C8 | A governed Neon `bi` schema and published Power BI semantic model expose approved weekly PSI facts, dimensions, KPIs, mismatch/anomaly flags, and release history; refresh occurs only after Final publish, end-user delegated sessions prove RLS, and a separately owner-authorized workspace-admin session performs every grant/removal with readback and sign-out | active | Power Query PostgreSQL connector and Power BI refresh API: `https://learn.microsoft.com/en-us/power-query/connectors/postgresql`, `https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/refresh-dataset-in-group`

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->
Plan identity | Create `.omo/plans/psi-neon-online.md`; preserve the earlier Supabase plan and its incomplete review receipts unchanged | Provider and current-state assumptions changed materially; stale approvals cannot transfer | yes
Engine authority | Extend `src/psi_tool` into the canonical engine and port only verified rule behavior from root modules; never promote `.codex-tmp` files wholesale | The tracked CLI has the strongest immutability/cache/test foundation while `psi_engine.engine` is absent and temporary copies diverge | yes
Compute boundary | Use request-billed Cloud Run service for FastAPI, one on-demand one-task Python/Polars Job, one separately privileged on-demand backup Job, a private OIDC Cloud Tasks delivery queue, a private recovery broker, a fixed two-task cutover guardian Job, private Power BI session/routing brokers, and two zone-disjoint no-public-IP GCE Chromium session executors in `asia-southeast1`; ordinary services remain zero-minimum-instance, while the guardian/executors are explicitly started and live-proved before the authorized consumer grant | Preserves the existing language and identity separation, keeps the Neon key and browser profiles behind distinct authorities, supports retryable post-commit delivery without a scheduler, and makes narrowly scoped access compensation independent of the operator host and Cloud Tasks delivery timing | yes
Blob boundary | Use Google Cloud Storage in the same GCP project/region family as Cloud Run for raw XLSX/Parquet/Draft/Final; store immutable object keys/checksums/metadata in Neon | Cloud Run local disk is ephemeral; GCS removes the separate Cloudflare provider and its credentials/egress boundary | yes
Database access | Pooled Neon URL for API traffic; direct URL for migrations and worker operations requiring session semantics | Neon PgBouncer is transaction-mode and official guidance uses direct connections for migrations | yes
Tenant model | V1 serves one company/one configured Entra tenant with departmental teams, but every governed row still carries `tenant_id` and RLS must pass negative two-tenant tests | Prevents a global-read schema while avoiding an unrequested SaaS control plane; reusable multi-company provisioning can be added later | yes
Workflow scope | Plan the complete Upload -> immutable snapshot -> reconcile -> Draft -> review gate -> Publish -> download/history workflow; no MVP reduction | Full shared-online outcome was requested and the repository plan defines this lifecycle | yes
Cutover | Import the current approved Manual Check and latest approved PSI baseline into a preview branch, pilot one reporting period, then promote by an explicit production gate | Preserves business authority and keeps rollback possible | yes
Workspace safety | Treat all existing modified/untracked workbook, input, output, `.tmp`, and `.codex-tmp` paths as immutable; execution uses a task-owned worktree or an exact allowlist | The checkout is heavily dirty and most PSI product files are currently untracked | yes
Frontend direction | Keep FastAPI plus the existing vanilla shared UI language; repair the API/client contract without an unrequested redesign or frontend-framework migration | Smallest path consistent with current product surface | yes
Source intake | User selects the reporting week and uploads the required source files directly in the PSI web page; pressing Run after validation creates one immutable source set and one job | This is the workflow the owner clarified and removes folder watchers, Graph identity/cursors, schedulers, and duplicate provider logic | yes
Power BI mode | Build one Power BI semantic model/report over curated Neon `bi` tables in Import mode and trigger refresh only after a successful Final publish | Weekly data does not need DirectQuery; Import isolates interactive dashboard load from Neon and prevents Draft data from appearing | yes
Power BI source | Store PBIP/TMDL plus a KPI dictionary, use a separate Python 3.12 pinned `fabric-cicd` deploy project, and require an owner-provided pinned Windows Power BI Desktop + Desktop Bridge runner; consumer access uses dynamic UPN/team RLS with disjoint Viewer QA identities | PBIX-only binaries are not reviewable in Git, the PBIP-specific Microsoft `fabric-cicd` guide currently supports Python 3.9-3.12 and the isolated 3.12 pin reduces deployment-tool drift, and the macOS workspace cannot prove rendered visuals/RLS | yes
Browser upload boundary | FastAPI is the only browser control/database/Auth API; it issues one origin-bound no-store resumable-session URI so upload bytes travel browser-to-GCS under narrow CORS/CSP, keeps the URI browser-memory-only, and stores only an envelope-encrypted server cancellation capability with deterministic expiry/revocation tasks | Avoids proxying large XLSX bytes through Cloud Run while making application expiry honest: finalize/Run deny immediately, exact-URI cancellation is reconciled, and uncertain initiation/pending cancellation stay explicit until provider expiry | yes
Terraform state failure | Run Terraform from encrypted permission-restricted ephemeral directories; on backend-persist failure stop mutation, quarantine fallback state under separate recovery authority, reconcile lineage/serial/remote generation without force, and require zero residue only after verified recovery | Terraform can intentionally write local fallback state when a remote backend persist fails, so an absolute no-local-state claim is unsafe | yes
Independent recovery target | Preview and production restore use separately authorized remotely state-backed Neon and GCP/GCS targets with target Auth-control/database secrets, strict source-target-client PostgreSQL major equality, and exact Auth/GCS readback; enable-Auth-before-data is allowed only by a current owner/provider capability contract plus successful preview proof, and every non-idempotent Auth enable uses a persisted at-most-once intent with GET reconciliation | Enabling Auth creates provider-owned schema/config/JWKS state, so recovery proves an empty identity/data predicate, inventories bootstrap rows, preserves target config/JWKS, maps only portable allowlisted data, omits source sessions, and never treats whole-schema emptiness or a blind POST retry as safe | yes
Power BI shared-capacity operation | Keep Pro/shared capacity only with an exact eight-request provider-day budget, coalesced security refreshes, reserved retry slots, and fail-closed PPU/Premium/Fabric upgrade gate; Groups readback is requested access only and effective access requires an owner-delegated receipt for each opaque QA identity, per-user permission refresh, wait, discarded sessions, isolated fresh sign-in, positive/negative RLS proof, and sign-out | Microsoft caps shared capacity at eight API/scheduled refresh requests per day and documents delayed permission propagation; a service principal or opaque identity list cannot prove user-effective access | yes

## Findings (cited - path:lines)
- The online server is not runnable: `web/server.py:16` imports absent `psi_engine.engine.build`; both available Python environments also lack the declared web dependency set.
- `web/static/index.html` references `/app.js`, but `web/static/app.js` is absent; the root `web/app.js` calls legacy `/api/process` and `/api/download` routes that `web/server.py` does not expose.
- The root project tracks only `README.md` and `scripts/build_audit_report.py` from the surveyed PSI code surface; the remaining engine, API, migration, tests, docs, and deployment files are untracked user work and must be adopted deliberately, not overwritten.
- Offline `tests/psi_tool/` covers manifest pinning, fastexcel/Polars ingest, Parquet cache integrity, source immutability, signals, CLI subprocess E2E, and output-path attacks, but no test exercises FastAPI, auth, Postgres, storage, worker recovery, browser flow, Draft approval, or Final publication.
- Both Supabase migrations depend on `auth.users`, `storage.*`, Supabase roles, and overlapping schema definitions; they are design references only and cannot be applied to Neon as-is.
- The live Neon project `amis-review-psi` / branch `production` is ready but has no non-system tables; Neon Auth is unconfigured, Data API is absent, Functions are unavailable, and branchable object storage is unavailable in `aws-ap-southeast-1`.
- Neon supports pooled application connections, direct migration/worker connections, Auth, and Postgres RLS; FastAPI can provide the entire browser API without enabling Neon Data API.
- Strict all-Neon compute is not compatible with the current PSI engine: Neon Functions currently support only JavaScript/TypeScript on Node.js 24, not Python/Polars, and Neon explicitly describes Functions as request/response compute rather than a queued background-job runner (`https://neon.com/docs/compute/functions/overview`).
- Neon Functions and Object Storage are beta and currently limited to `aws-us-east-2`; the current PSI project is `aws-ap-southeast-1`, and Neon says production guardrails/monitoring are still being finalized (`https://neon.com/blog/neon-backend-is-beta`).
- A strict all-Neon rewrite would therefore require a new Ohio project, a Python-to-TypeScript engine rewrite, beta storage acceptance, and still a third-party queue/scheduler; it is not the smallest or safest implementation of the requested online PSI workflow.
- The local XLSX-to-Parquet spike processed 59,104 rows with a 4.074-second typed Polars/fastexcel first read versus an 8.042-second openpyxl count-only pass; on the 49,122-row sheet Polars was 6.135x faster, and warm Parquet replay was 0.025 seconds (about 319x the openpyxl baseline) at 424 MiB peak RSS (`.omo/evidence/psi-bigdata-lean-v1/benchmark-spike-2026-08-30.md`).
- That spike proves only the ingest/cache boundary, not the complete rules plus 17-sheet workbook path; the plan must measure end-to-end runtime/RSS before making a final engine-performance claim.
- Polars documents fastexcel/Calamine as its fastest Excel reader and transfers into Arrow/Polars without a data copy; its Parquet path supports lazy scans and columnar pushdown (`https://docs.pola.rs/user-guide/io/excel/`, `https://docs.pola.rs/user-guide/io/parquet/`).
- DuckDB is intentionally excluded from this plan: no PSI-specific benchmark proves it faster than the verified Polars path, its Excel extension is secondary/best-effort, and a second execution engine would add dependency, type, and semantic-parity risk. Any future evaluation requires a separate owner-approved ADR after production profiling.
- Current generation uses FastAPI `BackgroundTasks`, auto-selects latest snapshots, writes `PSI Final.xlsx` before review, and has no durable lease/retry, Draft approval, release immutability, rollback pointer, or atomic DB/blob finalize.
- Repository business docs require immutable source versions, explicit provenance, stable mismatch fingerprints, blocking quality gates, and Draft-before-Final; the implementation currently stops short of those controls.
- The existing `.omo/plans/psi-complete-shared-tool.md` is Supabase-specific and its latest dual-review round is not approved; it remains useful as risk research but is not executable authority for the Neon plan.
- Power Query includes an official PostgreSQL connector for Power BI Desktop, semantic models, and dataflows, so Power BI can read Neon as standard PostgreSQL (`https://learn.microsoft.com/en-us/power-query/connectors/postgresql`).
- Power BI exposes a REST operation to refresh a semantic model/dataset in a workspace, allowing a successful PSI publish to trigger a report refresh rather than rebuilding the PBIX each week (`https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/refresh-dataset-in-group`).
- Power BI Desktop can author the report, but online publishing/sharing/automated service operation depends on the tenant's Power BI/Fabric licensing and workspace capacity; Free is not assumed to provide the full shared-online outcome (`https://learn.microsoft.com/en-us/power-bi/fundamentals/service-features-license-type`).

## Decisions (with rationale)
- Build a new Neon-native plan rather than patching or overwriting the Supabase plan.
- Use versioned pure-Postgres migrations and a canonical schema contract; never run either current Supabase migration on Neon.
- Keep analytical/business rows in content-addressed Parquet and governance/query state in Neon Postgres.
- Replace process-local background tasks with a fenced one-task PSI Job plus persistent deterministic publication intents delivered by one versioned queue-level Cloud Tasks policy. Each delivery persists its name/policy hash while nullable first-dispatch/count/deadline fields come only from monotonic `GetTask` observations; handler headers are supplemental. Only the reconciler may mark `EXHAUSTED`, and only with matching policy, provider-observed attempts, first-dispatch-derived elapsed duration, no success, and repeated `NOT_FOUND`. A vanished never-observed/deleted task is `WAITING_FOR_OPERATOR`; runtime identities cannot delete/purge/run. Authorized replay increments generation. Cloud Tasks has no native DLQ.
- Publish exactly the validated and approved Draft bytes; publish never regenerates a workbook.
- Require explicit source selections and carry-forward provenance; never silently compute from whichever upload is newest.
- Treat the old `.codex-tmp` engine variants as non-authoritative evidence only.
- Require agent-executed API, DB/RLS, worker-crash, browser, object-integrity, workbook-parity, migration, rollback, and restore QA before production cutover.
- Reporting-period identity is ISO week (`YYYY-Www`); `data_as_of`/cutoff remains explicit metadata and all carry-forward selections retain their origin week and snapshot checksum.
- Test strategy is boundary-first TDD for engine parity, schema/RLS, job state machine, publish gate, integrity and authorization; UI/browser coverage is tests-after plus real browser QA.
- Owner stack selection is Neon Postgres/Auth + one Cloud Run FastAPI service + separate on-demand PSI and backup Jobs + private Cloud Tasks delivery + an internal recovery broker + Google Cloud Storage + Power BI. The broker is an implementation of least privilege inside the selected providers, not a new external provider. No Supabase or Neon Data API in v1.
- Cost guardrail is zero-minimum-instance/on-demand execution, bounded upload/job resources, lifecycle for disposable objects, and usage alerts; no claim that production remains free after quotas, build/image, egress, or storage limits are exceeded.
- Engine baseline is Python 3.13 orchestration around native fastexcel/Calamine -> Arrow -> typed/lazy Polars -> content-addressed Parquet, with XlsxWriter/native-Excel validation at the output boundary. Business transforms must not use Python row loops.
- Engine escalation is outside this plan: complete and benchmark the approved corpus on Polars first. If later production profiling misses an agreed runtime/RSS SLO, open a separate owner-approved ADR/task. This plan must not install, import, or benchmark DuckDB, an authored Rust/TypeScript PSI rewrite, pandas, or Spark; prebuilt native wheels used by fastexcel/Calamine, PyArrow, Polars, and other approved dependencies are allowed.
- The Polars-only rule applies to business transforms. Pydantic, NumPy/PyArrow, FastAPI, psycopg, the Google Cloud Storage client, XlsxWriter, and narrowly test-only openpyxl/LibreOffice validation are allowed at typed contract, infrastructure, I/O, and independent-verification boundaries.
- Every web-uploaded file must pass source-type, week, schema, size, checksum, and duplicate/idempotency checks before immutable GCS registration and job creation. Exact `(tenant, team, week, slot, verified hash, normalized data_as_of, source schema version)` tuples reuse a snapshot; corrected bytes/metadata/version create a new snapshot. The user explicitly selects versions; arrival time never selects data.
- Materialize deterministic analytical facts/dimensions in run-scoped hidden Neon `bi` staging before approval. The Final transaction verifies the frozen staging manifest and performs local SQL promotion/current-pointer/audit/outbox writes only, with no GCS or provider I/O. A least-privilege Power BI database role receives `SELECT` only on Final views through the direct/unpooled Neon endpoint with SSL.
- Use Power BI Import mode and one versioned PBIP/TMDL model/report, pinned Python 3.12 `fabric-cicd`, an explicit portal connection-binding receipt, pinned Windows Desktop Bridge QA, and mandatory dynamic UPN/team RLS for consumer Viewers. After Final publish, deliver the persisted refresh intent through Cloud Tasks, record request/status/attempt/sanitized error, and never roll back Final merely because dashboard refresh fails.
- "Automatic analysis" means governed KPI calculations, exception/mismatch flags, trend/comparison marts, and versioned DAX measures. LLM-generated conclusions and any AI-driven approval remain out of scope.
- FastAPI is the only browser control/database/Auth boundary and owns reads, upload authorization/finalization, source selection, review, publish, rollback, and Power BI refresh requests. The sole data-plane exception is browser-to-GCS upload bytes over an origin-bound resumable URI held only in volatile browser memory; FastAPI retains only an envelope-encrypted exact-URI cancellation capability, schedules deterministic expiry/revocation tasks, and treats uncertain initiation or cancellation as explicit fail-closed states. Neon Data API is deliberately omitted.

## Metis gap closures
- **Workspace authority:** execution begins with a hash manifest and exact adoption/edit allowlist for modified/untracked PSI assets. A task-owned worktree receives only owner-approved files; overlap, symlink alias, or protected-hash drift returns `NO_START`; broad staging is forbidden. Todo 40 pilot evidence must pass before its commit; only after all Todo 1-40 commits exist is the Git release-candidate SHA and immutable base evidence index frozen. F1-F4 consume that same post-commit SHA/index, and any later source commit invalidates every receipt.
- **Engine-first gate:** online/schema/UI/BI feature work cannot claim runnable completion until a sanitized six-workbook plus Manual Check corpus deterministically produces all 17 sheets in the documented order, passes business-rule parity, repeated logical hash, Parquet round-trip, formula/package/error-token, Linux Python 3.13, and runtime/RSS gates.
- **Upload contract:** one form names `YYYY-Www` and assigns files to `crm_sales`, `product_master`, `sales_detail_misa`, `inventory`, optional new `purchase_po`, optional new `target`, and `manual_check`. The four fresh sources plus an explicit Manual Check version are required; Purchase/Target use an explicitly approved carry-forward snapshot when absent. Exact snapshot-identity tuples reuse immutable snapshot IDs with duplicate-audit events; the canonical run key then covers selected snapshot IDs/hashes/metadata, approvals, baseline/waiver, and engine/rule/config/schema/template versions.
- **Job state:** the API starts a one-task Cloud Run Job after a source set is complete. The worker claims a fenced lease with heartbeat, bounded retry/timeout/concurrency, stale-completion rejection, cancellation semantics, and capped database pools. No Cloud Scheduler or watcher is needed for v1.
- **Auth/RLS:** invitation-only Neon Auth for v1; trusted-domain, verified-email, reset, session-cookie, CSRF, deactivation, and role provisioning are explicit. Grants default-deny; governed tables have tenant/team RLS; migration, API, worker, backup, broker, dispatcher, and BI reader roles are distinct without `BYPASSRLS`. Creator/uploader cannot approve and approver cannot publish. One approved Entra consumer group is assigned `PSIViewer` by the owner; workspace Viewer is the separate supported activation grant, and the group is never in an app audience. Membership/team/deactivation changes first deny app access and inventory and suspend workspace/RLS/Build/effective QA-app access, then refresh/verify the imported membership checksum before active-user reinstatement; deactivated users remain removed.
- **Distributed publish:** upload and verify the content-addressed Draft and preloaded hidden BI staging first. Reserve a deterministic publication intent/event in Postgres, persist generation 0 refresh/backup delivery records, create private OIDC Cloud Tasks from their intent/channel/generation names, then one local-only Postgres Final transaction verifies Draft/staging hashes, promotes staging, advances the immutable pointer, records audit/outbox, and marks the intent committed. Uncertain creation retries the same generation name; last-attempt or post-deadline absent-task reconciliation records `EXHAUSTED`; authorized replay increments the persisted generation and uses a new name. A later rollback creates a distinct event. Dashboard refresh failure never rolls back Final.
- **Power BI contract:** version-control PBIP/TMDL and a KPI dictionary before report implementation. V1 pages are Overview/Release Health, Revenue vs Target, Inventory, Pre-orders/Purchase, and Mismatch/Data Quality; every measure must trace to a documented field/formula from the governed 17-sheet relations. No executor may invent an undocumented business metric.
- **Power BI readiness:** use Pro licenses for every publisher/viewer in one dedicated Pro workspace, explicit PBIP/Desktop Bridge preview acceptance, pinned sources, isolated Python 3.12 `fabric-cicd`, Contributor service principal, named binding/Entra lifecycle owner, `bi_reader`, pinned Windows runner, approved consumer group, two disjoint QA Viewers, and one admin. Todo 31 applies the KPI mart successor migration to durable preview and publishes a governed sanitized Final before Todo 33 deploys. Todo 33 emits IDs/`BINDING_REQUIRED`; the admin portal binds the connection, assigns RLS, and publishes a QA-only app, while the supported Groups API controls workspace Viewer and the consumer group never enters an app audience. It then refreshes and verifies Todo 31 checksums. Todo 34 compares/render-checks and removes Build. Production assigns consumer `PSIViewer` and publishes the QA-only app during gated QA with no consumer Read, then finalize adds only Groups-API workspace Viewer; lifecycle inventory includes app access and no-Build proof; service-principal RLS queries and UPN/token evidence are forbidden.
- **Preview bootstrap and image provenance:** Todo 6 installs pinned Terraform/gcloud/Neon/Syft/Trivy/Buildx, creates durable preview/secrets and non-compute GCP foundation. Todo 12 creates one tracked `deploy/image-context.yaml` allowlist plus generated commit-bound JSON manifests; later tasks never reuse its stale image. Todos 23/25-30/35 use task-local committed images; Todos 36/38/37/39 each commit before clean build/SBOM/scan/push/rebind. Todo 40 freezes only when release-candidate and Todo 39 deployed context hashes match.
- **Retention/DR default:** failed/temp uploads 7 days; logs 30 days; raw/Parquet/Draft/validation/run telemetry 24 months; Final/release manifest/audit 7 years. Every GCS bucket uses UBLA before policy-v3 conditional prefix IAM; effective inherited grants are audited. Backup get/create custom roles remain no-list/no-overwrite/no-delete, while the app enforces exact manifest key/generation/SHA. Dumps stream over TLS to CMEK GCS with no persistent plaintext. Backup has no Neon key/direct KMS use; only the broker holds the project key. Backup includes application schemas, full Neon Auth recovery branch, and generation-guarded object copies; fresh-preview restore validates all state and revokes sessions. Production cutover first provisions a non-migrating foundation/backup facility, then requires an existing-data backup+restore or signed empty-deployment waiver before migration. RPO is one finalized cycle and RTO 8h.
- **Capacity/cost gate:** measure pilot bytes, CU-hours, requests, compute, and egress; project 52 weeks; warn at 70% and fail closed for new Run actions at 90% until capacity is approved. Active runs complete safely; no claim of indefinite free operation.
- **Power BI authoring prerequisite:** the core pipeline may be built on macOS, but C8 is not complete until the owner supplies the pinned Windows Power BI Desktop + Desktop Bridge runner, accepts preview tooling, the exact static/round-trip/deploy/comparison commands pass, the portal datasource-binding receipt exists, preview refresh succeeds, both Viewer RLS identities deny cross-team data, and five sanitized report pages are visually checked in authenticated Power BI Service sessions. PBIP excludes `cache.abf`; Desktop Bridge proves source structure only and is never treated as a data-render producer.

## Scope IN
- Canonical offline PSI engine completion and 17-sheet parity.
- Pure Neon Postgres schema, migrations, roles/RLS, and Neon Auth behind FastAPI; no direct browser database API.
- External immutable object storage and checksum-bound artifact lifecycle.
- Shared FastAPI/browser workspace, team/role governance, durable PSI Job plus private Cloud Tasks delivery, Draft/review/publish/history/rollback.
- Preview branch, pinned cloud-tool bootstrap, immutable-image deployment, key-isolating recovery broker, production migration/cutover, secrets, monitoring, backup/restore, retention, runbooks, and executable QA evidence.
- Direct weekly source upload in the web app with explicit version selection and Run action.
- Curated Neon analytical schema, Power BI semantic model/report template, publish-triggered refresh, and refresh monitoring.

## Scope OUT (Must NOT have)
- No product-code edits during this planning session.
- No direct modification of the Neon production branch, cloud bucket, auth, user data, or deployment until execution is separately authorized.
- No Supabase-specific runtime dependency or hybrid runtime path in the final architecture.
- No pandas, DuckDB, AI auto-approval, source mutation, silent latest-file selection, in-process-only jobs, or regeneration during publish.
- No wholesale copy from `.codex-tmp`, broad staging of the dirty checkout, or inclusion of raw business workbooks/secrets in Git/evidence.
- No OneDrive/SharePoint watcher, Microsoft Graph integration, Cloudflare account, Cloud Scheduler intake, weekly PBIX regeneration, Power BI query against raw XLSX/GCS objects, Draft-visible dashboard rows, or DirectQuery in v1.

## Open questions
1. RESOLVED: Neon-centric without Supabase; Cloud Run service/Job plus Google Cloud Storage.
2. RESOLVED: ISO week.
3. RESOLVED: boundary-first TDD plus tests-after/browser QA for UI.
4. RESOLVED DEFAULT: one company/one Entra tenant with departmental teams, but mandatory tenant keys and negative two-tenant RLS tests.
5. RESOLVED BY OWNER: direct upload of the weekly source set in the web app; no watched folder or Graph automation.
6. RESOLVED DEFAULT: Power BI Import via version-controlled PBIP/TMDL, five governed pages, refresh only after Final publish.

## Approval gate
status: approved
approach: Neon Postgres/Auth + one Cloud Run FastAPI service + separate on-demand PSI/backup Jobs + private Cloud Tasks delivery + an internal recovery broker + Google Cloud Storage + Power BI Import, using a pinned preview bootstrap, immutable image digests, direct web upload, ISO-week Draft-review-publish, and preview-first cutover.
approval: User explicitly selected `Neon + Google Cloud + Power BI` after rejecting OneDrive/Graph/Cloudflare complexity.
pending-action: Run `$start-work psi-neon-online`; Round 34 received unconditional OKAY from both high-accuracy review lanes for SHA 69bea04330d97dc00b6261fa6dcbec76570ffae6663d2ec90e8d3c4da5bc2194.
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->
