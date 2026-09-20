# Manual QA Review

Terminal verdict: PASS

Reviewed commit: `3e686be94834e343e3018bce1ddc69d20fa5957d`

Reviewed tree: `15263c5db8f75f260b1d267f2d753a0512f3c6e0`

Target: Neon organization `org-calm-tree-69287331`, project `withered-fog-14675525` (`amis-review-psi`), branch `production`.

I independently inspected all prior C001-C003 artifacts, visually inspected the BrowserOS PNG, and reran read-only CLI/config checks. No Neon resource was created, updated, deleted, linked, checked out, deployed, or otherwise mutated during this review. The bounded fresh nested-Codex MCP attempt emitted retries for an unrelated unavailable localhost MCP and did not produce a second live result; C002 is nevertheless PASS because the prior successful non-mutating `describe_project` artifact is present, internally consistent, and current `codex mcp list/get` plus Neon CLI state independently agree with it.

## manualQa

### surfaceEvidence

| scenario id | criterion reference | surface | exact invocation | verdict | artifactRefs |
|---|---|---|---|---|---|
| C001 | C001 | BrowserOS Neo screenshot and Neon CLI project/link state | Existing task-owned Console capture reviewed at `browser.png`; read-only reruns: `rtk neon projects list --org-id org-calm-tree-69287331 -o json`, `rtk neon status --project-id withered-fog-14675525 --branch production -o json`, `rtk read .neon` | PASS | A1, A2, A3 |
| C002 | C002 | Codex MCP configuration and live Neon metadata evidence | Read-only reruns: `rtk codex mcp list`, `rtk codex mcp get Neon`; prior fresh ephemeral evidence records OAuth `Neon.describe_project` with `{}` and no mutation | PASS | B1, B2, B3, B4 |
| C003 | C003 | Repository preservation, parser, and secret-scan state | Read-only reruns: `rtk git rev-parse HEAD`, `rtk git rev-parse HEAD^{tree}`, `rtk git status --porcelain=v1 --branch`, `rtk git diff --name-only`, `rtk git check-ignore -v .neon`, `rtk jq -e ...`, and credential-pattern `rtk rg` scan | PASS | C1, C2, C3, C4 |

### adversarialCases

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| ADV-001 | C001/C002 | wrong project or duplicate PSI project | One and only one PSI project in the org; CLI, MCP, and BrowserOS identify the same project id/name; pre-existing `ian-ticketfast` remains separate and unmodified | PASS | A1, B2, B3 |
| ADV-002 | C001 | stale interactive inventory or link mismatch | Deterministic org-scoped project listing and `.neon` readback identify `withered-fog-14675525` on `production` | PASS | A2, A3 |
| ADV-003 | C002 | mutation/auth regression | MCP URL is project-scoped and `readonly=true`; OAuth is used; bearer token and HTTP authorization headers are absent; metadata call reports no mutation | PASS | B1, B2, B4 |
| ADV-004 | C003 | credential leakage | No repository env file or credential-like value is present in `.neon`, `skills-lock.json`, or installed Neon skill files; `.neon` is ignored and untracked | PASS | C2, C3 |
| ADV-005 | C003 | dirty-worktree clobbering | The exact pre-existing tracked modified set and untracked work remain preserved; no unrelated tracked file was changed by the setup | PASS | C1, C4 |
| ADV-006 | C002/C003 | cleanup residue | Temporary API key is revoked, task-owned BrowserOS pages are closed, temporary PDF is trashed, and no Neon login/config-status process remains | PASS | B4, C2 |

## artifactRefs

| id | kind | description | path |
|---|---|---|---|
| A1 | screenshot | BrowserOS Neo project dashboard; visually shows `amis-review-psi`, MCP server onboarding, and `production` branch; SHA-256 `099faa05b355f37d50d31d2af0ae8b078ee082dc534db1bb616fdfad5c93f7cf` | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C001-neon-link/browser.png` |
| A2 | cli-json | Sanitized org/project/link readback with one PSI project and no secret fields | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C001-neon-link/cli-readback.json` |
| A3 | action-log | BrowserOS organization/project selection and repository-link action log | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C001-neon-link/action-log.txt` |
| B1 | cli-transcript | Current Codex MCP list/get output: Neon enabled, OAuth, project-scoped `readonly=true` URL, no bearer/header | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C002-neon-mcp/codex-mcp-list.txt` |
| B2 | live-tool-json | Successful prior fresh ephemeral read-only `describe_project` result; same project metadata and `mutation_performed=false` | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C002-neon-mcp/live-tool.json` |
| B3 | cli-json | Sanitized complete org inventory showing exactly one PSI project and untouched pre-existing project | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C002-neon-mcp/org-projects-sanitized.json` |
| B4 | cleanup-json | OAuth final state, no HTTP authorization header, and revoked temporary API key receipt | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C002-neon-mcp/auth-cleanup.json` |
| C1 | git-transcript | Before/after status snapshots showing preserved dirty set at the recorded tree | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C003-security-regression/git-status-before.txt` |
| C2 | audit-transcript | Secret-safe config audit, parser checks, ignore/tracking checks, cleanup receipts, and preservation assertions | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C003-security-regression/config-audit.txt` |
| C3 | parser-transcript | JSON parser and credential-scan transcript with clean scan result | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C003-security-regression/parser-transcript.txt` |
| C4 | git-transcript | Final status snapshot for direct comparison with the baseline | `/Users/iant1359/Develop/amis-review/.omo/ulw-loop/01a0589c-00c8-77c2-baed-b59e5a5f7c2b/evidence/C003-security-regression/git-status-after.txt` |

