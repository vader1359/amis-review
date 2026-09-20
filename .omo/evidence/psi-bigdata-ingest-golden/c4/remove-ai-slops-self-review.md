# C4 programming/remove-ai-slops self-review

## Scope and behavior lock

Reviewed the explicit C4 surface only: `src/psi_tool/cli.py`, `report.py`, `_report_models.py`, `_report_json.py`, `__main__.py`, `tests/psi_tool/test_cli.py`, and `tests/psi_tool/test_e2e.py`.

- Behavior lock: fresh C4 targeted subprocess suite passed 13/13 in 196.15 seconds (`pytest-c4-repair.xml`), public E2E passed 7/7 in 46.89 seconds (`pytest-e2e-repair.xml`), and the complete PSI package passed 40/40 in 430.43 seconds (`pytest-psi-tool-repair.xml`).
- New boundary regression: a regular-file `--output-dir` failed before the repair with a Rich traceback; it now observes only the public nonzero result, one sanitized stderr line, unchanged input bytes, and no temporary residue.

## Deletion ladder and category review

| Surface | Ladder result | Findings and result |
|---|---|---|
| `cli.py` | Simplify in place | The output-state guard is required at the CLI trust boundary. Cleanup is restricted to a tracked new regular directory; I/O failures are handled only at expected boundaries. No broad catch, duplicate validation, dead code, or needless wrapper remains. |
| `report.py` and report models/JSON | Keep | Atomic publication, immutable report values, and canonical serialization are required behavior. No duplicate algorithm, hidden-cost regression, or over-sized module was found. |
| CLI/report tests | Simplify in place | Removed the non-empty SHA assertion because it was tautological. The semantic SHA is instead independently re-derived in a clean subprocess from parsed report content. |
| Public E2E tests | Keep | Tests drive `python -m psi_tool` through the real interface. Assertions target output tree, exit status, sanitized stderr, source bytes, and independently parsed JSON, not private implementation calls. The writer-interruption test uses the one narrow injectable I/O seam and observes cleanup. |

## Critical review result

- Implementation mirroring: none. The regression suite observes the public subprocess CLI; report hashing is recomputed independently from the serialized JSON.
- Tautologies: none. The former truthy hash assertion was removed; semantic values must match a separately constructed canonical SHA-256.
- Deletion-only changes: none. The repair adds a stateful creation guard plus an observable regression; the deleted assertion was false-confidence coverage already replaced by independent verification.
- Overfit: none. Regular-file behavior uses arbitrary bytes and a real temporary path; cache/manifest scenarios use the public fixtures and real Parquet bytes.
- Comments: Given/When/Then BDD markers are retained; copyright notices are required by Ruff `ALL`. No explanatory noise was added.
- API and behavior: no public command or schema change. The public command remains `psi inspect --manifest PATH --output-dir DIR`.
- Remaining risk: directory fsync/power-loss behavior is not simulated; report file fsync and same-directory atomic replace are covered by the implementation and interruption regression.

## Quality gates

- Ruff project check and formatter: pass.
- C4-owned Ruff `--select ALL`: pass.
- Full basedpyright: 0 errors, 0 warnings, 0 notes.
- C4-owned no-excuse/pure-LOC audit: no violations in 7 files.
- Static/security scanner: N/A; no project scanner is configured.

Final status: CLEAN.
