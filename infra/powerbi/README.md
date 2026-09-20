# PSI Power BI read model

`001_psi_powerbi_read_model.sql` is an operator migration for the PSI online
preview database.  It exposes typed PostgreSQL views for the current Power BI
business tables and has no refresh job, gateway credential, or Power BI write.

It must be applied to the actual preview project `amis-psi-preview`, branch
`psi-online`, only after `infra/sql/psi_preview_reports.sql`.  The currently
connected read-only Neon MCP project is a different, empty project and must not
be used for this migration.

Before a Power BI refresh, an operator must insert immutable reference snapshots
for Product and Target, then add one `psi_powerbi.report_selections` row.  That
row pins an existing immutable `psi_preview.reports.id`; the views never choose
the newest Draft.  Use `operator_selected_corrected_local_snapshot` only when
the corrected source snapshot was intentionally reviewed.  It records the
selection without claiming the Draft is an approved Final.

Product and Target are separate reference snapshots because the PSI Draft
payload does not contain the complete Product catalog or a typed Target schema.
Their original reference labels are retained in `psi_powerbi.lineage`.

The views deliberately return `NULL` for fields not supported by the validated
PSI payload: F.O.C, order prices, stock-in history, payment/logistics fields and
actual preorder cost.  They do not create replacement values.  Preorder delivery
uses the payload's recorded ETA proxy and remains labelled for business review.

Use an SSL PostgreSQL Import connection with the dedicated `powerbi_reader`
role.  The role receives only `SELECT` on views; it cannot read raw snapshots or
change the pinned selection.  Power BI table mapping is:

| Existing model table | PostgreSQL view |
| --- | --- |
| `1. Product` | `psi_powerbi.product_reference` |
| `2. Inventory` | `psi_powerbi.inventory` |
| `3. Purchase` | `psi_powerbi.purchase` |
| `4. Sales_CRM` | `psi_powerbi.sales_crm` |
| `5. Revenue` | `psi_powerbi.revenue` |
| `6. Preorder` | `psi_powerbi.preorder` |
| `7. Stock_In` | `psi_powerbi.stock_in` |
| `Target` | `psi_powerbi.target_reference` |

`psi_powerbi.lineage` must be loaded or checked alongside each refresh so the
report always reveals the exact `report_id`, payload hash, selection kind, and
reference labels used.

Use the eight typed M queries in `infra/powerbi/partitions/` to replace the
matching model partitions.  They preserve the existing source-column names and
types; `powerbi-postgresql-source.m` is an illustrative navigation template,
not an automatic model replacement.

Do not insert a new selection while an eight-table Import refresh is running:
each query resolves the current selection independently, so a mid-refresh change
could mix two pinned snapshots.  Pin the selection first, wait for refresh
completion, then change it only for the next refresh.  A later integration may
pass and verify one `selection_id` per refresh to make that guard automatic.
