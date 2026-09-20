# PSI C5 final code-quality review

## Snapshot

- Required product snapshot before review:
  `a46b1c8c48d6c22e699a4cfe71d7cb910c9bf5649b087c4eb5f23f7dc8bf0083`
- Product snapshot after review:
  `a46b1c8c48d6c22e699a4cfe71d7cb910c9bf5649b087c4eb5f23f7dc8bf0083`
- Git HEAD observed: `3e686be94834e343e3018bce1ddc69d20fa5957d`.
- Scope: all `src/psi_tool` and `tests/psi_tool` files included in the
  established ordered product-snapshot command, plus the PSI contract doc and
  fixture manifest. This was a read-only review; no product/test files changed.

## Skill-perspective check

Ran the required `programming` and `remove-ai-slops` review perspectives.

- `programming`: no observed `Any`, `cast`, type-ignore, broad exception,
  process-CWD mutation, pandas, or source module above 250 pure LOC. Models are
  frozen and typed APIs use explicit boundary errors. One lifecycle defect below
  violates the resource/cancellation ownership requirement.
- `remove-ai-slops`: no deletion-only, tautological, implementation-mirroring,
  or prose/prompt tests found in the PSI scope. The trusted relation-pin test is
  a meaningful behavioral boundary, not duplicated parsing/normalization.

## Findings

### CRITICAL

None.

### HIGH

1. **Cancellation during cold-session construction leaks an owned staging
   directory and descriptors.**
   [`src/psi_tool/_output_lifecycle.py:167`](/Users/iant1359/Develop/amis-review/src/psi_tool/_output_lifecycle.py:167)
   creates the random sibling stage before `OutputSession` exists at line 179.
   The signal handler raises `InspectCancelled` asynchronously. A SIGINT/SIGTERM
   after line 167 and before line 179 bypasses the `except (OSError,
   OutputLifecycleError)` cleanup at lines 180-182. In
   [`src/psi_tool/cli.py:90`](/Users/iant1359/Develop/amis-review/src/psi_tool/cli.py:90),
   `session` is still `None`, so the cancellation handler deliberately performs
   no cleanup. The result is a `.run-*.tmp` directory (and potentially open
   descriptors) surviving a command that reports a controlled 130/143 exit.

   This contradicts the stated cold-run cancellation guarantee and is a real
   lifecycle gap, not a theoretical foreign-path race. The existing process
   signal test waits until a partial Parquet exists, which is after session
   construction, so it cannot exercise this window.

   Required fix: make `open_output_session` cancellation-safe for every point
   after `open_parent_chain`, retaining and cleaning the newly-created stage
   under ignored later signals before propagating `InspectCancelled`; add a
   narrow regression test that injects cancellation immediately after private
   stage allocation and asserts no stage/final output remains.

### MEDIUM

None.

### LOW

None.

## Static review notes

- The relation pins are literal manifest values, checked for both cold and warm
  cache paths; a self-consistent embedded-metadata forgery is rejected.
- Output/cache writes are descriptor-relative with no-follow opens and the
  output parent chain is revalidated around publication.
- `VerifiedManifest` owns the exact manifest bytes/hash and explicit workspace
  root; no production `os.chdir` remains.
- No untrusted output path writer or unrelated database/web layer was found.

## Test review

Focused static inspection only, by assignment. Full-suite execution belongs to
the QA lane. Existing signal coverage proves cancellation after partial cache
materialization, but misses the construction window described above.

## Verdict

- `codeQualityStatus`: **BLOCK**
- `recommendation`: **REQUEST_CHANGES**
- `blockers`: repair and regression-test the cancellation-safe construction
  lifecycle described in HIGH-1, then rerun this review against a new frozen
  snapshot.

---

## Re-review: cancellation remediation

This section supersedes the preceding verdict. The product snapshot changed
after the lifecycle fix and is now:

`5be980fe954a00632675a355f8bd861eacfc55f03ba487c715699e2bcd6089ab`

The prior snapshot is retained above only as audit history. The product snapshot
was identical before and after this re-review.

### Result

**PASS.** `run_inspect` now enters `cancellation.deferred()` while acquiring
the output session. A first SIGINT/SIGTERM is recorded rather than raised until
the assignment at `cli.py:95` has completed; leaving the deferred context then
raises the same typed cancellation, with the caller-owned session available for
the existing signal-ignored cleanup. Later signals remain ignored while that
cleanup runs.

The acquisition routine remains locally safe for every non-signal partial
state: it closes the retained parent descriptors if no session exists, and
cleans/closes a created session for `OSError`/`OutputLifecycleError`. The
deferred handler avoids a blanket exception or a path-based cleanup fallback.

### Focused evidence

- `uv run pytest tests/psi_tool/test_cli_signals.py -q`: **7 passed in
  20.01s**.
- The two parameterized injections immediately after stage creation and before
  caller binding returned exactly **130** and **143**, emitted only
  `inspect cancelled` on stderr, left neither final output nor `.run-*.tmp`,
  and restored the `/dev/fd` count.
- The same injection sends the opposite second signal during cleanup; it is
  ignored and the first signal's exit code is retained.
- Focused Ruff, Ruff-format, basedpyright, and no-excuse checks passed. Static
  search found no `Any`, `cast`, type-ignore, broad exception, `os.chdir`, or
  recursive path-deletion escape in the touched lifecycle surface. All source
  modules remain below 250 pure LOC.

### Final verdict

- `codeQualityStatus`: **CLEAR**
- `recommendation`: **APPROVE**
- `blockers`: none from final code-quality review.
