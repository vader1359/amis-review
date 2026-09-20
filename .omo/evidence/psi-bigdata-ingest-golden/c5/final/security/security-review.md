# C5 final security and trust-boundary review

## Scope and identity

- Frozen product snapshot method: `shasum -a 256 pyproject.toml uv.lock src/psi_tool/*.py tests/psi_tool/*.py tests/psi_tool/fixtures/golden_manifest.toml docs/psi_tool_v1/contract.md | shasum -a 256`
- Initial verified snapshot: `a46b1c8c48d6c22e699a4cfe71d7cb910c9bf5649b087c4eb5f23f7dc8bf0083`.
- Read-only review. Full-suite execution was intentionally left to the QA lane.

## Decision

**PASS.** No CRITICAL, HIGH, or MEDIUM finding remains in the reviewed trust boundary.

## Findings

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

1. `ManifestLoadError.__str__` includes the caller-supplied manifest path for direct Python API consumers ([`src/psi_tool/_contract_errors.py`](/Users/iant1359/Develop/amis-review/src/psi_tool/_contract_errors.py:49)). The public CLI catches it and emits only `inspect failed: validation_failed`, and reports contain no paths or source rows, so this is not an output-channel leak in the supported CLI. Library callers should avoid logging raw exceptions if local path privacy is a requirement.

## Verified controls

- Each relation has a literal trusted digest in the committed manifest. Cold and warm cache materialization recomputes the semantic digest and compares it to that pin before PASS; the self-consistent Parquet-metadata forgery case is covered by `test_warm_cache_rejects_self_consistent_metadata_tamper`.
- `load_verified_manifest` reads manifest bytes once, derives the manifest SHA from those bytes, parses that same snapshot, resolves sources under its explicit workspace root, and passes the frozen `VerifiedManifest` into cache/ingest/report. No production `chdir` or manifest reload path remains.
- Cache and report I/O use held directory descriptors with `O_NOFOLLOW`; cache files are constrained to exact expected regular-file names. The output lifecycle walks lexical ancestors without following symlinks, retains inode identities, rechecks the chain, stages cold output in a private mode-0700 sibling, and uses exclusive Darwin publication.
- Swapped staging names, warm-root swaps, and ancestor-name changes are rejected without following the substituted symlink. Cleanup targets the held staging inode and does not recursively remove the caller-selected final root.
- SIGINT and SIGTERM are converted into controlled 130/143 exits. Later signals are ignored while cleanup/publication is protected. The real process-group cancellation tests cover partial-Parquet cleanup; warm cancellation replaces a prior PASS with sanitized FAIL.
- CLI failure output is generic; report serialization is structural/redacted. No source row values are retained in the manifest or evidence reviewed. The dependency set remains bounded to the stated local Python/data stack; no database or network dependency was introduced.

## Documented residuals accepted by scope

The contract correctly states that caller-supplied manifests are not authenticity signatures; coordinated replacement of manifest and source can PASS. Source/manifest bytes must remain immutable during an invocation. There are no XLSX/Parquet resource quotas, directory fsync is absent after rename, and SIGKILL or delayed signal delivery inside native code cannot guarantee cleanup.

## Skill-perspective check

Consulted `omo:remove-ai-slops` and `omo:programming` before judging maintainability and tests. No violation requiring a finding: relation-pin and lifecycle tests exercise observable adversarial boundaries rather than merely mirror constants; production validation is at actual untrusted filesystem/workbook boundaries; frozen typed models and descriptor abstractions have concrete security seams. No deletion-only or tautological test was found in the reviewed control set.

## Recommendation

`PASS` / `APPROVE` for the final local security and trust-boundary lane at the exact snapshot above. The LOW direct-library exception-path observation is non-blocking.

## Post-fix refresh

- Current snapshot, recomputed with the same ordered product-snapshot command: `5be980fe954a00632675a355f8bd861eacfc55f03ba487c715699e2bcd6089ab`.
- Narrow change reviewed: `controlled_signals()` now yields a handler whose `deferred()` context records SIGINT/SIGTERM while `open_output_session()` acquires its owned descriptors and staging inode. Once assignment to `session` has completed, deferred exit raises the recorded typed cancellation, so the existing protected cleanup path owns and removes that exact staging inode.
- Static conclusion: **PASS**. The change closes the previously unowned acquisition interval and does not weaken descriptor/no-follow, relation-pin, manifest-snapshot, exclusive-publication, or redaction controls. It introduces no MEDIUM-or-higher security finding. The existing test explicitly exercises a signal after staging/before session binding, a second signal during cleanup, zero staging residue, and no descriptor leak.
