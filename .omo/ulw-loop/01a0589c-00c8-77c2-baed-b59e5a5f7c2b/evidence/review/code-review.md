# Neon MCP Code/Config Review

## Verdict: APPROVE

- **codeQualityStatus:** CLEAR
- **recommendation:** APPROVE
- **blockers:** None
- **Reviewed commit:** `3e686be94834e343e3018bce1ddc69d20fa5957d`
- **Reviewed tree:** `15263c5db8f75f260b1d267f2d753a0512f3c6e0`

## Scope and evidence examined

- Working-tree configuration: `.neon`, `.agents/skills/neon/SKILL.md`, `.agents/skills/neon-postgres/SKILL.md`, and `skills-lock.json`.
- C001: `evidence/C001-neon-link/action-log.txt`, `cli-readback.json`, `red.txt`, and `browser.png`.
- C002: `evidence/C002-neon-mcp/codex-mcp-list.txt`, `live-tool.json`, `auth-cleanup.json`, `org-projects-sanitized.json`, and `red.txt`.
- C003: `evidence/C003-security-regression/config-audit.txt`, `parser-transcript.txt`, `git-status-before.txt`, and `git-status-after.txt`.
- Fresh read-only checks: `git show`, `git rev-parse`, `git status --porcelain`, `git check-ignore`, `jq` structural checks, credential-pattern scan, `codex mcp list`, and `codex mcp get Neon`.

## Findings

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

1. **Commit anchoring is informational, not a configuration snapshot.** The reviewed commit contains only the pre-existing reconciliation workbook; the Neon link and skill files are intentionally ignored/untracked working-tree state. This is consistent with C003 (`.neon` is ignored and `--no-env-pull` was used), but a future audit must use this evidence directory plus the live masked MCP readback rather than the commit alone.

## Verification summary

- `.neon` has exactly the expected `orgId`, `projectId` (`withered-fog-14675525`), and `production` branch. C001 and C002 identify the same project as `amis-review-psi`, `aws-ap-southeast-1` (Singapore), PostgreSQL 18.
- Current Codex MCP state reports Neon **enabled**, `streamable_http`, project-scoped `readonly=true` URL, OAuth authentication, and no bearer-token environment variable or HTTP headers. C002 records a completed fresh `describe_project` call with the same project attributes and no mutation.
- C003 records no `.env`, no repository credential matches, unchanged pre-existing tracked dirt, task-owned untracked additions only, revoked temporary key `3299882`, closed task BrowserOS tabs, and deleted temporary PDF receipt.
- No production source or tests changed. The configuration-only change needs no deletion-only, prompt-text, tautological, or implementation-mirroring test; the fresh end-to-end MCP `describe_project` receipt is the relevant behavioral evidence.

## Skill-perspective check

Ran both required perspectives: `omo:programming` and `omo:remove-ai-slops`.

- **Programming:** no typed production code, parser, validation boundary, untyped escape hatch, or needless abstraction was introduced. The configuration is minimal and uses the platform OAuth boundary instead of adding custom authentication logic.
- **Remove-AI-Slops:** no production code or tests were added. No deletion-only test, removal-only test, tautological assertion, constant-mirroring test, or needless parsing/normalization was found. The real MCP call validates an observable integration outcome.

No skill-perspective violations found.
