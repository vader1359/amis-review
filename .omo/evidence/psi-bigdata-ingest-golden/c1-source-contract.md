# C1 source-contract evidence

## Scope and safety boundary

Owned C1 artifacts are `src/psi_tool/contracts.py`,
`src/psi_tool/_contract_errors.py`,
`src/psi_tool/_contract_models.py`,
`src/psi_tool/_workbook_validation.py`,
`tests/psi_tool/fixtures/golden_manifest.toml`,
`tests/psi_tool/test_contracts.py`, and `docs/psi_tool_v1/contract.md`.
The fixture and all logs below contain contract metadata, diagnostics, counts,
and permitted workbook hashes only; they contain no source rows or PII.

`load_manifest` now fails closed against the actual workspace: it resolves a
normalized source below `PSI_SAMPLE_INPUT`, requires a regular file, streams
and compares SHA-256, requires the declared worksheet, reads the exact locked
fastexcel extraction window, checks physical and derived logical shapes, and
requires every projected raw header exactly once. Inventory uses its declared
two-row structural normalization; no business transformation is present.

## Red to green sequence

| Phase | Invocation | Exit | Binary observable | Artifact |
| --- | --- | ---: | --- | --- |
| Original rejection reproduction | `rtk proxy uv run pytest tests/psi_tool/test_contracts.py -q` | 1 | Six workspace-boundary mutations were accepted (`DID NOT RAISE`). | `c1/rejection-repro.log` |
| Nonblank-count red | `rtk proxy uv run pytest tests/psi_tool/test_contracts.py -k invalid_nonblank_header_count -q` | 1 | The declared-count-to-999 header-count mutant was accepted before enforcement. | `c1/nonblank-header-red.log` |
| Green targeted boundary | `rtk proxy uv run pytest tests/psi_tool/test_contracts.py -q` | 0 | `11 passed in 9.84s`; seven source-contract mutations fail closed, including nonblank header count. | `c1/targeted-green.log` |
| Green package tests | `rtk proxy uv run pytest tests/psi_tool -q` | 0 | `13 passed in 10.84s`. | `c1/tests-psi-tool-green.log` |
| Green C1 Ruff ALL | `rtk proxy uv run ruff check --select ALL` and format check on five owned Python files | 0 | `All checks passed!`; `5 files already formatted`. | `c1/ruff-c1-green.log` |
| Green project Ruff gate | `rtk proxy uv run ruff check src test tests` and format check | 0 | `All checks passed!`; `8 files already formatted`. | `c1/ruff-project-green.log` |
| Green static typing | `rtk proxy uv run basedpyright` | 0 | `0 errors, 0 warnings, 0 notes`. | `c1/basedpyright-green.log` |
| Green manual driver | `rtk proxy uv run python -c '<independent loads and streaming hashes>'` | 0 | `relations=7 independent_loads=true deterministic_json=true hash_readback=6 pre_post_equal=true`. | `c1/manual-driver-green.log` |
| LOC gate | `rtk proxy uv run python -c '<pure LOC counter>'` | 0 | Public/models/errors/workbook modules have 53/204/63/204 pure LOC, all at or below 250. | `c1/pure-loc-counts.log` |

The manual driver independently loaded the manifest twice (distinct objects),
compared deterministic serializations, and streamed all six source files both
before and after validation. It did not enumerate or print worksheet rows.

The former same-object serialization assertion was removed. Only the distinct
`first_load is not second_load` comparison remains, so deterministic output is
proved across two independently validated manifest instances.

## Header-count correction

The earlier Sales Detail value of 34 was incorrect. The bounded raw header
window has 38 nonblank cells and zero blank columns, confirmed without writing
any header or row values in `c1/sales-detail-header-count.log`. The manifest,
test expectation, and documentation now declare 38. Validation counts only
bounded raw header cells whose normalized value is neither `None` nor
whitespace-only; it does not count generated reader column names.

## Source hash readback

| Workspace-relative source | SHA-256 | Pre/post equality |
| --- | --- | --- |
| `PSI_SAMPLE_INPUT/CRM_Sale_sample.xlsx` | `d3c7ddb0835d3ec12c52d50a34e96ca57f5a5126f2d531cc35173213e0fe3c4d` | true |
| `PSI_SAMPLE_INPUT/Product_master_sample.xlsx` | `d665711e28e588375c57e1d2088ad89857bb472e8a6b03529591ddc81d3ab156` | true |
| `PSI_SAMPLE_INPUT/Sales_detail_MISA_sample.xlsx` | `1ec89484a30fa5caae2217444daf601ba68ed944afa693666285315b414e53b8` | true |
| `PSI_SAMPLE_INPUT/Inventory_sample.xlsx` | `0d79817a63b60b228881672728207b680158fff55f633b83c3322de06eb47417` | true |
| `PSI_SAMPLE_INPUT/Purchase_PO_sample.xlsx` | `768081ce81192e00d80c47081ea1e697aba5dcb6cb4c45587ab1172ed0d63137` | true |
| `PSI_SAMPLE_INPUT/Target_sample.xlsx` | `d55f701d64adba55ed9f057b110574b184d2d1a2e1353042c1313c99e8c60e3e` | true |

## Shape and header interpretation

`physical_shape` is the locked extraction window supplied to fastexcel, not a
claim about a workbook's broader formatted used range. The full source hash
freezes trailing bytes/rows; this boundary neither trims nor interprets them.
Logical rows are derived from the header strategy within that window. The
inventory reader has one leading blank physical row, so its declared source
rows 2 and 3 are accessed with the fixture's explicit structural offset of 1;
the manifest still records the locked source strategy, not a business rule.

## Cleanup receipt and residual risks

- Adversarial tests wrote only pytest-managed `tmp_path` manifest copies. They
  created no workbook copies and never mutated production workbooks.
- The temporary local diagnostic files used during repair were removed after
  the green evidence was captured. C1 created no cache, database, report, or
  transformed dataset.
- Residual scope: C1 proves only the immutable source contract boundary. The
  downstream ingest/cache/report implementation must consume this contract and
  preserve the same schema behavior; that is outside C1.
