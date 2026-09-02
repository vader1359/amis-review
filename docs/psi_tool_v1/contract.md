# PSI golden-source contract

`tests/psi_tool/fixtures/golden_manifest.toml` is the committed, sanitized
golden fixture for the seven input relations. It is read once and parsed only
through `psi_tool.contracts.load_verified_manifest` into frozen models. The fixture
contains schema metadata, file identities, header contracts, shapes, and
projected column names only; it contains no source-row values or PII.

The manifest pins `psi-semantic-string-v1` and one literal
`expected_relation_sha256` for each relation. Cache files and embedded `psi.*`
metadata are untrusted. PASS means decoded content is consistent with this
externally trusted manifest; it is not a digital signature. Coordinated
replacement of the trusted manifest and source tree can therefore PASS and is
outside the authenticity guarantee. The manifest and sources must remain
immutable for one invocation.

## Version and fixture date

- `schema_version = "1.0"`; `contract_version = "1.1"`.
- `as_of = 2026-08-30` is the sanitized golden-fixture contract date. It is
  fixed fixture metadata, never an assertion of operational source freshness.

## Workbook identities

| Source ID | Workspace-relative path | Freshness policy |
| --- | --- | --- |
| `crm_sale_workbook` | `PSI_SAMPLE_INPUT/CRM_Sale_sample.xlsx` | fresh-required, not carry-forward |
| `product_master_workbook` | `PSI_SAMPLE_INPUT/Product_master_sample.xlsx` | fresh-required, not carry-forward |
| `sales_detail_misa_workbook` | `PSI_SAMPLE_INPUT/Sales_detail_MISA_sample.xlsx` | fresh-required, not carry-forward |
| `inventory_workbook` | `PSI_SAMPLE_INPUT/Inventory_sample.xlsx` | fresh-required, not carry-forward |
| `purchase_po_workbook` | `PSI_SAMPLE_INPUT/Purchase_PO_sample.xlsx` | carry-forward with matching expected SHA-256 and approved fixture reason |
| `target_workbook` | `PSI_SAMPLE_INPUT/Target_sample.xlsx` | carry-forward with matching expected SHA-256 and approved fixture reason |

All paths are normalized workspace-relative paths rooted in
`PSI_SAMPLE_INPUT`; absolute paths and traversal are rejected. Every source
SHA-256 must be lowercase hexadecimal with 64 characters. A carry-forward
source must have a nonempty reason and an expected SHA-256 exactly matching
the declared source hash.

## Workspace verification boundary

`load_verified_manifest` hashes and parses the same manifest byte snapshot, captures
the explicit canonical workspace root, and resolves every declared source without
reading or changing the process working directory. It requires each source to be a
regular file and re-hashes it with streaming SHA-256 before opening any workbook.
It then requires the declared sheet, reads exactly the locked
physical extraction window through fastexcel as `string`, and checks its width
and height. The physical shape is therefore a frozen extraction window, not a
workbook used-range claim: formatted rows after the window are not trimmed or
interpreted, and source-byte equality freezes them.

Logical rows are derived from the declared header strategy inside that locked
window. Only structural header rows are normalized: every projected raw header
must be present exactly once, and the inventory two-row header is flattened by
its declared construction rule. No source-row values are retained, serialized,
or written to evidence.

## Relations

| Relation ID | Sheet | Header strategy | Physical shape | Logical data shape |
| --- | --- | --- | --- | --- |
| `crm_sales` | `Danh sách` | row 0 | 9983x40 | 9982x40 |
| `crm_sale_items` | `Bảng hàng hóa` | row 0 | 49123x33 | 49122x33 |
| `product_master` | `Danh sách` | row 0 | 27731x23 | 27730x23 |
| `sales_detail_misa` | `SỔ CHI TIẾT BÁN HÀNG` | row 3, 38 nonblank headers | 12053x38 | 12049x38 |
| `inventory` | `TỔNG HỢP TỒN KHO` | grouped rows 2 and 3 | 3412x15 | 3409x15 |
| `purchase_po` | `LDL` | row 2, omit raw blank columns 1/85/86 | 2627x86 | 2624x86 |
| `target` | `Target` | row 0 | 20x9 | 19x9 |

`crm_sales` and `crm_sale_items` intentionally refer to the one
`crm_sale_workbook` source identity, so their checksum cannot drift apart.
Relation IDs are a closed seven-value set. Projection canonical names must be
unique per relation, and every ingest dtype is exactly `String`.

## Exact-header rules

Source headers are preserved exactly in every projection mapping. That includes
Vietnamese accents, embedded newlines, and trailing spaces such as
`Category ` and `Sub Category ` in `product_master`.

The Sales Detail nonblank-header count is 38. It is counted from the bounded
raw header row as cells that are neither `None` nor whitespace-only; generated
reader column names are not part of this check. This corrects the prior
incorrect value of 34 after independent XML, openpyxl, and fastexcel probes
agreed on the same 38-cell mask.

The `inventory` grouped-header strategy is structural only: forward-fill a
merged parent header only across its blank child cells; join nonblank parent
and child with ` - `; otherwise retain the singleton parent header unchanged.
For example, its declared projection uses the resulting schema labels
`Cuối kỳ - Số lượng` and `Cuối kỳ - Giá trị`; no inventory business parsing is
part of this boundary.

`purchase_po` records the three blank raw column numbers and separately fixes
the distinct one-based source headers 60 (`OF | AF` plus newline) and 69
(`OF | AF` plus newline and `/mã`). The `target` projection includes `NO.` only
as a stable source-identity field after header inspection confirmed that exact
header name.

## Failure policy

The parser fails closed on unreadable or invalid TOML, unknown fields, invalid
versions, malformed paths or hashes, incomplete carry-forward evidence,
unknown/missing/duplicate source IDs or relation IDs, unknown relation-source
references, duplicate canonical or raw projection names, missing files, hash
drift, missing sheets, invalid header windows, shape drift, and missing or
duplicated projected headers. It serializes only the structural manifest
deterministically for downstream cache/report identity.

## Output and cancellation boundary

`psi inspect` requires the selected output's immediate parent to already exist
as a real directory and rejects traversal plus every lexical symlink ancestor.
A component-by-component no-follow walk starts at the filesystem root and
retains every directory descriptor and inode identity. The same chain is
walked again before and after publication; a changed component fails the run.
A cold run creates one mode-0700 random sibling, performs cache and report I/O
through retained directory and file descriptors, and publishes the complete
tree with macOS `renameatx_np(RENAME_EXCL)`. The command fails closed on a
runtime without that exclusive publication primitive. It never creates or
recursively deletes the user-selected final root during cold failure.

A warm run removes the prior report before validation, retains an open
descriptor to the validated cache tree, and writes PASS or sanitized FAIL only
through that descriptor. If the final name changes identity during the run,
the invocation fails; an interrupted invocation cannot claim the previous PASS.

The first SIGINT and SIGTERM are converted to controlled exits 130 and 143.
Cleanup and publication ignore later SIGINT/SIGTERM so a second signal cannot
interrupt removal of the owned staging inode. SIGKILL and delayed delivery
inside a native extension are outside this cleanup guarantee.

The source tree and trusted manifest must remain immutable for one invocation.
The tool has no workbook or Parquet resource quotas, so local resource
exhaustion remains possible. File contents are fsynced, but parent directories
are not fsynced; sudden power loss can therefore lose the most recent rename.
The caller-supplied manifest is not an authenticity signature.
