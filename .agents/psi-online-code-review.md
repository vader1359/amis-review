# PSI online parity preview — independent code review (re-review)

**Scope reviewed.** Integrated portable engine, workbook renderer, pipeline,
baseline verifier, loopback HTTP preview, documentation, and online tests. The
assessment remains limited to the declared loopback-only acceptance preview;
cloud identity, durable storage, publication, and Power BI are scope
limitations rather than code defects.

**Skill-perspective check.** Did not run: `remove-ai-slops` and `programming`
are not in this session's available skill catalog and their requested local
paths do not exist. I applied their stated criteria directly. The diff does
not add deletion-only or tautological tests, prompt tests,
implementation-constant tests, untyped escape hatches for core integrity
behavior, or needless data parsing/normalization. The baseline and HTTP tests
exercise genuine fail-closed behavior.

## Findings

### CRITICAL

None.

### HIGH

None. The previous baseline-integrity blocker is fixed: a baseline is required
to have the established 17-sheet schema, exact Mismatch headers, passing
Checks, a content date strictly earlier than the cutoff, and consistent title,
Summary `As of`, and filename dates where present
([online_baseline.py:41](/Users/iant1359/Develop/amis-review/src/psi_tool/online_baseline.py:41)). The pipeline verifies this before the engine receives
the baseline and pins its date/identity into input material
([online_pipeline.py:130](/Users/iant1359/Develop/amis-review/src/psi_tool/online_pipeline.py:130)).

### MEDIUM

1. **Full Ruff `ALL` is not clean for this integration.** Focused correctness
   lint (`E4,E7,E9,F,I`) passes, but the configured `ALL` run reports
   annotation/style/complexity findings in the procedural port and preview
   adapter. These do not demonstrate a correctness failure and have not been
   elevated to HIGH, but they are maintenance debt. Either make the affected
   code compliant or document narrowly justified per-file exclusions and run
   that selected project gate.

### LOW

1. **A complete root `pytest -q` collection still includes an unrelated legacy
   `psi_engine` test with private-input count drift.** The affected legacy test
   expects Manual Check counts 110/374 while the untracked input now contains
   117/386. The integrated `tests/psi_tool` suite is the relevant gate and is
   reported as 121/121 with the private golden directory; preserve the source
   input and legacy test until its fixture policy is decided.

## Verification

- Ran `uv run --extra online python -m pytest` for baseline, pipeline, preview,
  and Manual Check engine tests: **48 passed**. The final Manual Check guard
  rejects expiry dates on approved permanent preorder/order exclusions and
  requires evidence plus a reason field for approved preorder exclusions.
- Earlier re-review targeted suite (baseline/pipeline/preview/engine/workbook):
  **59 passed, 1 private-golden skip**.
- Ran focused correctness/import lint: **passed**.
- Static inspection confirms input upload bounds, ZIP limits, same-origin
  loopback restriction, token check, serialized build, independent payload
  validation, Parquet equality, formula-safe workbook writing and independent
  OOXML validation.

## Scope limitation (not a finding)

This preview intentionally uses an ephemeral token and retains only one Draft
in process memory. It is not the requested eventual Neon + Google Cloud +
Power BI production architecture, as stated in
[PSI_ONLINE_ACCEPTANCE.md](/Users/iant1359/Develop/amis-review/docs/PSI_ONLINE_ACCEPTANCE.md).

## Verdict

- `codeQualityStatus`: **CLEAR**
- `recommendation`: **APPROVE**
- `blockers`: None for the local acceptance preview. QA now records a clean
  body-only HTTP XLSX SHA-256 equal to the independent direct build, exact
  17-sheet/formula parity, no scratch-path leakage, and tolerated floating-point
  serialization deltas in
  [golden-compare.txt](/Users/iant1359/Develop/amis-review/outputs/psi-online-qa-20260905/golden-compare.txt).
