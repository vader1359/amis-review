# Final QA — approved snapshot full-suite timeout

## Verdict

FAIL / BLOCKED. The single approved-snapshot full-suite invocation exceeded the
12-minute execution bound without producing a terminal result. It was
terminated as the QA-owned process. No second invocation was started.

## Binding evidence

- Ordered snapshot command: `shasum -a 256 pyproject.toml uv.lock src/psi_tool/*.py tests/psi_tool/*.py tests/psi_tool/fixtures/golden_manifest.toml docs/psi_tool_v1/contract.md | shasum -a 256`
- Observed snapshot: `5be980fe954a00632675a355f8bd861eacfc55f03ba487c715699e2bcd6089ab`
- Full-suite invocation: `rtk proxy uv run pytest tests/psi_tool -q --junitxml=.omo/evidence/psi-bigdata-ingest-golden/c5/final/qa/pytest-full.xml`
- State: running beyond the 12-minute bound; progress dots were observed; no
  failure output and no final pass count/exit code were emitted.
- JUnit artifact: not created because pytest did not terminate.
- Cleanup: no matching `pytest tests/psi_tool`, `uv run pytest`, or
  `basedpyright` process remained after termination.

Because the required full-suite gate did not complete, strict static gates and
the subsequent cold/warm and SIGINT/SIGTERM manual scenarios were not run.
They are not claimed as skipped or passed; the missing prerequisite is a
completed full-suite result within the authorized execution window.

## Manual QA matrix

### surfaceEvidence

| scenario id | criterion reference | surface | exact invocation | verdict | artifactRefs |
|---|---|---|---|---|---|
| FINAL-FULL-01 | full `tests/psi_tool` gate | local CLI/package | exact pytest command above | FAIL | A1 |
| FINAL-POST-01 | strict gates and runtime scenarios | local CLI/filesystem/process group | not invoked because FINAL-FULL-01 did not complete | FAIL | A1 |

### adversarialCases

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| FINAL-TIME-01 | execution bound | long-running command | terminate only owned run after 12 minutes and report incomplete result; never infer PASS | PASS | A1 |

## Artifact refs

| id | kind | description | path |
|---|---|---|---|
| A1 | text | Approved snapshot binding, exact invocation, timeout state, and cleanup receipt | `.omo/evidence/psi-bigdata-ingest-golden/c5/final/qa/full-suite-timeout.md` |
