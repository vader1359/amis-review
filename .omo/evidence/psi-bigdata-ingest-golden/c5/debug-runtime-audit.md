# C5 PSI inspect CLI runtime audit

<verdict>FAIL</verdict>

## Scope and snapshot

- Scope: `<REPO>`, product HEAD `3e686be94834e343e3018bce1ddc69d20fa5957d`.
- Expected product digest supplied by caller: `f2c1a3257c2d3c61205ae213d9f26a40b7a111daeb77667a5fe28eab5497e6af`.
- Runtime: Python `3.14.6` at `<PYTHON3>`; uv `0.12.5`; project requires Python `>=3.13`.
- Surface: public `psi inspect` CLI, invoked through tmux using `uv run --project <REPO> psi inspect ...`.
- Worktree: pre-existing dirty state was preserved; no product source, test, plan, ledger, or coordinator file was edited. The required shared Multi 2 status file was updated separately per workspace instructions.
- All source fixtures were copied to an external temporary workspace. The six manifest sources matched their manifest SHA before the audit and were unchanged after it: `CRM_Sale_sample.xlsx` `d3c7ddb0835d3ec12c52d50a34e96ca57f5a5126f2d531cc35173213e0fe3c4d`; `Product_master_sample.xlsx` `d665711e28e588375c57e1d2088ad89857bb472e8a6b03529591ddc81d3ab156`; `Sales_detail_MISA_sample.xlsx` `1ec89484a30fa5caae2217444daf601ba68ed944afa693666285315b414e53b8`; `Inventory_sample.xlsx` `0d79817a63b60b228881672728207b680158fff55f633b83c3322de06eb47417`; `Purchase_PO_sample.xlsx` `768081ce81192e00d80c47081ea1e697aba5dcb6cb4c45587ab1172ed0d63137`; `Target_sample.xlsx` `d55f701d64adba55ed9f057b110574b184d2d1a2e1353042c1313c99e8c60e3e`.

## Hypothesis results and runtime evidence

| ID | Claim | Distinguishing runtime evidence | Verdict |
|---|---|---|---|
| H1 | Warm cache can silently return stale content after a source changes. | Not executed: the audit stopped immediately after the confirmed H3 defect, as required. A source mutation was therefore not made. | FAIL / unrun blocker |
| H2 | Error paths can exit 0 or emit PASS/traceback/absolute paths. | Missing manifest and foreign-output runs emitted `FAIL`, `inspect failed: validation_failed`, and exit `1`; no traceback or absolute path appeared. | REFUTED for tested paths |
| H3 | Interruption/foreign output can leave partial cache/temp or stale PASS. | Ctrl-C during cold materialization produced only `^C`, no report, no final `cache/`, and a hidden `.cache-<random>.tmp/` containing one 293588-byte parquet. | CONFIRMED defect |
| H4 | Cold/warm/cross-process semantic identity can drift. | Cold and a fresh-process run both returned `PASS`, semantic SHA `c7a7f8c4878b0ae96fb8b1cf5a28151d097902b9cdd4b42d45da455881424fd2`; relation hashes, cache keys, and parquet SHAs were equal. | REFUTED for tested state |

### Confirmed root cause

`cache.py:107-128` creates a staging directory and relies on Python cleanup in `finally`; `cli.py:98-126` catches selected `Exception` subclasses but not `KeyboardInterrupt`. In the real tmux Ctrl-C scenario, the foreground `uv`/Python process terminated during materialization, leaving the staging directory and first parquet behind. The user receives no controlled report or exit transcript. This is an exact runtime failure, not an inference from source alone.

## Manual QA matrix

### `manualQa.surfaceEvidence`

| scenario id | criterion reference | surface | exact invocation | verdict | artifactRefs |
|---|---|---|---|---|---|
| C5-S1 | C5 nominal cold inspect | tmux terminal / public CLI | `uv run --project <REPO> psi inspect --manifest <AUDIT_TMP>/workspace/tests/psi_tool/fixtures/golden_manifest.toml --output-dir <AUDIT_TMP>/cold-output` | PASS | A1 |
| C5-S2 | C5 warm cache inspect | tmux terminal / public CLI | same invocation against existing `<AUDIT_TMP>/cold-output` | PASS | A1 |
| C5-S3 | C5 handled failure | tmux terminal / public CLI | `uv run --project <REPO> psi inspect --manifest <AUDIT_TMP>/workspace/tests/psi_tool/fixtures/no-such-manifest.toml --output-dir <AUDIT_TMP>/failure-output` | PASS | A2 |
| C5-S4 | C5 foreign output rejection | tmux terminal / public CLI | `uv run --project <REPO> psi inspect --manifest <AUDIT_TMP>/workspace/tests/psi_tool/fixtures/golden_manifest.toml --output-dir <AUDIT_TMP>/foreign-output` with a foreign marker present | PASS | A2 |
| C5-S5 | C5 cross-process identity | tmux terminal / public CLI | `uv run --project <REPO> psi inspect --manifest <AUDIT_TMP>/workspace/tests/psi_tool/fixtures/golden_manifest.toml --output-dir <AUDIT_TMP>/cross-output` in a new process | PASS | A3 |
| C5-S6 | C5 interruption cleanup | tmux terminal / public CLI | same golden invocation against fresh `<AUDIT_TMP>/interrupt-output`, then Ctrl-C during cold materialization | FAIL | A4 |

`<AUDIT_TMP>` and `<REPO>` are intentional redaction tokens for the removed absolute temporary/repository paths; the command structure and arguments are exact.

### `manualQa.adversarialCases`

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| C5-A1 | H1 | source mutation after cold | warm run must detect changed source or refuse stale cache; never emit stale PASS | FAIL: not run after stop-on-confirmed-defect; blocker is the required H3 stop rule | A1 |
| C5-A2 | H2 | missing manifest / handled validation failure | nonzero exit, safe FAIL text, no traceback/path leak | PASS | A2 |
| C5-A3 | H3 | foreign output state | reject foreign state without PASS or unsafe overwrite | PASS | A2 |
| C5-A4 | H3 | Ctrl-C during cold materialization | no partial staging/cache/temp should remain; controlled nonzero failure is preferred | FAIL: partial staging parquet remained and no report was produced | A4 |
| C5-A5 | H4 | fresh process identity | semantic/report/cache identity remains equal across processes | PASS | A3 |

## Silent-failure scan

The package scan found no subprocess calls, ignored subprocess return codes, `except Exception: pass`, or `contextlib.suppress`. It did find the relevant boundary: `run_inspect` catches a fixed tuple of exception classes and does not handle `KeyboardInterrupt`; the runtime interruption evidence demonstrates the resulting partial-state escape. No other silent-failure pattern was recorded.

## Four final evidence gates adapted for this audit

1. Runtime toggle: PASS for normal cold/warm completion versus Ctrl-C interruption; interruption changes the observable state to partial staging with no report (A1, A4).
2. Full suite: NOT RUN after the real defect was confirmed and the explicit stop rule applied; no product change was attempted.
3. Manual QA: FAIL, because the real Ctrl-C scenario leaves partial staging and no report (A4).
4. Artifact cleanliness: PASS after cleanup; tmux sessions, external roots, debug journal, and exclude entry were removed, and product snapshot/source hashes remained unchanged. Durable audit report/logs are intentionally retained under this C5 evidence directory.

## Artifact refs

| id | kind | description | path |
|---|---|---|---|
| A1 | tmux transcript | Redacted cold and warm public CLI runs, exit 0, semantic identity, cache-hit observations | `.omo/evidence/psi-bigdata-ingest-golden/c5/debug-cold-warm.log` |
| A2 | tmux transcript | Redacted missing-manifest and foreign-output failures, exit 1, safe output | `.omo/evidence/psi-bigdata-ingest-golden/c5/debug-failure.log` |
| A3 | tmux transcript | Redacted independent-process identity run and equality observations | `.omo/evidence/psi-bigdata-ingest-golden/c5/debug-cross.log` |
| A4 | tmux transcript | Redacted Ctrl-C repro and partial staging state | `.omo/evidence/psi-bigdata-ingest-golden/c5/debug-interrupt.log` |

## Cleanup and verdict

The journal was established before creating the external root, copied workspace, tmux sessions, and evidence files. Cleanup removes the exact temporary root, all named tmux sessions, `.debug-journal.md`, and the exact `.git/info/exclude` entry; no product files are reverted because none were changed. Final verdict: `<verdict>FAIL</verdict>` due to H3.
