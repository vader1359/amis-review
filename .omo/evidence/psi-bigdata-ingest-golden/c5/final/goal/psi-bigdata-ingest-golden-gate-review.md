# Goal and constraints gate review

## recommendation

APPROVE

Frozen product snapshot: `5be980fe954a00632675a355f8bd861eacfc55f03ba487c715699e2bcd6089ab`

Snapshot command reproduced:

```text
shasum -a 256 pyproject.toml uv.lock src/psi_tool/*.py tests/psi_tool/*.py tests/psi_tool/fixtures/golden_manifest.toml docs/psi_tool_v1/contract.md | shasum -a 256
```

## blockers

None.

## originalIntent

Replace slow spreadsheet-style processing for this checkpoint with a local,
typed big-data ingest path: six sanitized XLSX sources projected into seven
explicit relations, content-addressed Parquet caching, and a real `psi inspect`
parity surface. This checkpoint expressly excludes PSI business transforms,
final workbook generation, database/web work, deployment, commit, and push.

## desiredOutcome

A strict, reproducible CLI checkpoint that reads the exact six-source contract,
materializes or verifies seven pinned relations, rejects source/cache/output
drift, and emits a redacted parity report whose semantic identity is stable
across cold and warm runs.

## userOutcomeReview

The shipped artifact satisfies the checkpoint outcome. The manifest contains
exactly six required source identities and seven closed relation roles. Each
relation has a literal external semantic hash pin under
`psi-semantic-string-v1`; cold and warm cache paths compare decoded content to
that pin. `load_verified_manifest` reads and hashes one manifest byte snapshot,
returns a frozen `VerifiedManifest`, captures an explicit canonical workspace
root, and resolves sources without changing process CWD. The public CLI passes
that object through ingest, cache, and report generation without rereading the
manifest.

Output handling is descriptor-anchored. It retains and rechecks lexical parent
identities, creates a private mode-0700 sibling for cold runs, publishes with
Darwin exclusive rename, invalidates stale warm PASS reports, and maps SIGINT
and SIGTERM to controlled exits 130 and 143 while protecting cleanup. The
post-fix cancellation change only defers the first signal across output-session
construction so the newly owned descriptor and staging inode become visible to
the existing cleanup path; it adds no data-processing or product capability.
The added regression observes exit status, staging removal, descriptor balance,
and second-signal cleanup protection at that boundary.

The
report includes expected and actual relation hashes, schema/shape parity,
source and manifest identities, cache status, and a semantic digest that omits
timing/cache-hit variability.

No PSI business transformation, final workbook generation, database, web,
deployment, commit, or push behavior is present in the reviewed checkpoint.
Documentation does not claim completion of the broader Final PSI workflow.

## checkedArtifactPaths

- `.omo/plans/psi-bigdata-ingest-golden.md`
- `docs/psi_tool_v1/contract.md`
- `pyproject.toml`
- `src/psi_tool/contracts.py`
- `src/psi_tool/_contract_models.py`
- `src/psi_tool/cli.py`
- `src/psi_tool/_output_lifecycle.py`
- `src/psi_tool/_fd_walk.py`
- `src/psi_tool/_exclusive_rename.py`
- `src/psi_tool/_signals.py`
- `src/psi_tool/_fd_cache.py`
- `src/psi_tool/report.py`
- `tests/psi_tool/fixtures/golden_manifest.toml`
- `tests/psi_tool/test_contracts.py`
- `tests/psi_tool/test_verified_manifest.py`
- `tests/psi_tool/test_relation_pin_enforcement.py`
- `tests/psi_tool/test_cli.py`
- `tests/psi_tool/test_e2e.py`
- `tests/psi_tool/test_output_lifecycle.py`
- `tests/psi_tool/test_ancestor_swap.py`
- `tests/psi_tool/test_cli_signals.py`
- `.omo/evidence/psi-bigdata-ingest-golden/c5/remediation/verified-manifest-verifier/reverification.md`
- `.omo/evidence/psi-bigdata-ingest-golden/c5/remediation/relation-pin-cold-fix/evidence.md`
- `.omo/evidence/psi-bigdata-ingest-golden/c5/remediation/output-signals-verifier/reverification.md`

## remove-ai-slops and programming review

Direct review found no criterion-blocking slop or overfit. The lifecycle,
manifest snapshot, relation pins, and signal handling correspond to reproduced
adversarial failures and observable CLI boundaries; they are not speculative
frameworks. Tests exercise public behavior and external effects (process exit,
tree publication/cleanup, immutable source bytes, cold/warm parity, independent
tamper rejection), rather than merely asserting requested deletions or mirroring
implementation internals. The implementation uses frozen typed models, typed
errors, explicit relation literals, descriptor-bound I/O, strict Pydantic v2,
and modules within the 250 pure-LOC ceiling. No `Any`, type suppression,
blanket exception catch, pandas, DuckDB, database driver, or web framework is
introduced in the production scope.

The independent remediation reports explicitly cover the same perspectives:
no-excuse/type/lint/LOC checks, no CWD mutation, no forbidden data/web/database
dependency, behavioral adversarial tests, and a slop review rejecting
tautological, deletion-only, and implementation-mirroring coverage.

## exactEvidenceGaps

None that violate a stated criterion. The documented residual limits are
resource exhaustion (no workbook/Parquet quotas), source/manifest mutation
during one invocation, SIGKILL or delayed native signal delivery, and sudden
power loss because parent directories are not fsynced. These are explicit
notes, not failures of this checkpoint's success criteria.

The full suite was intentionally not rerun in this lane; the independent QA
lane owns that evidence. This review inspected its referenced remediation
artifacts and ran only the exact snapshot reproduction and bounded read-only
searches.

## postFixRefresh

PASS on snapshot `5be980fe954a00632675a355f8bd861eacfc55f03ba487c715699e2bcd6089ab`.
The narrow deferred-cancellation fix changes lifecycle safety only. The six
sources, seven relations, trusted pins, `VerifiedManifest`, report contract,
and explicit exclusions remain unchanged. No broader Final PSI claim or scope
expansion was introduced.
