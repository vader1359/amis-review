# Final QA — frozen snapshot rejection

## Verdict

FAIL / ABORTED before execution. The requested frozen snapshot no longer matches
the current product bytes, so no gate or runtime scenario was run against the
wrong snapshot.

## Binding evidence

Exact command:

```text
shasum -a 256 pyproject.toml uv.lock src/psi_tool/*.py tests/psi_tool/*.py tests/psi_tool/fixtures/golden_manifest.toml docs/psi_tool_v1/contract.md | shasum -a 256
```

- Expected frozen snapshot: `a46b1c8c48d6c22e699a4cfe71d7cb910c9bf5649b087c4eb5f23f7dc8bf0083`
- Observed current snapshot: `5be980fe954a00632675a355f8bd861eacfc55f03ba487c715699e2bcd6089ab`
- Result: mismatch; frozen-snapshot prerequisite is not satisfied.

## Manual QA matrix

### surfaceEvidence

| scenario id | criterion reference | surface | exact invocation | verdict | artifactRefs |
|---|---|---|---|---|---|
| FINAL-SNAPSHOT | frozen product binding | local repository | exact ordered `shasum` command above | FAIL | A1 |

### adversarialCases

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| FINAL-BINDING-01 | frozen product binding | changed product bytes | abort before tests/runtime QA; request a new approved snapshot | FAIL | A1 |

## Artifact refs

| id | kind | description | path |
|---|---|---|---|
| A1 | text | Exact frozen-snapshot mismatch and abort record | `.omo/evidence/psi-bigdata-ingest-golden/c5/final/qa/snapshot-mismatch.md` |

QA-owned processes from the interrupted attempt were cleaned; no matching
`pytest tests/psi_tool` or `basedpyright` process remained at final check.
