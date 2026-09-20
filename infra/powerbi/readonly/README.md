# Read-only PSI payload queries

These Power Query files read one immutable payload from the existing
`psi_preview.reports` table. They require only `USAGE` on `psi_preview` and
`SELECT (id, payload)` on that table. They do not create views, roles, schemas,
selection records, refresh jobs or database writes.

Create text parameters `NeonHost`, `NeonDatabase`, and `ReportId`; paste
`GetPSIPayload.m` as a function query, then paste each of the six fact queries
into the matching existing model query:

| Existing model table | File | Payload relation |
| --- | --- | --- |
| `2. Inventory` | `inventory.m` | `inventory_rows` |
| `3. Purchase` | `purchase.m` | `purchase_rows` |
| `4. Sales_CRM` | `sales_crm.m` | `crm_product_rows` |
| `5. Revenue` | `revenue.m` | `revenue_rows` |
| `6. Preorder` | `preorder.m` | `preorder_rows` |
| `7. Stock_In` | `stock_in.m` | always empty; validated PSI payload has no stock-in history |

`ReportId` must be entered as the reviewed snapshot id. The helper uses a
parameterized `WHERE id = @report_id` and rejects zero or multiple rows; it
never chooses a latest Draft. Product and Target remain the current embedded
references in the model. The fact queries preserve the existing columns/types;
fields unavailable from the PSI payload remain `null`.

The validated payload does not contain a separate display Brand for these fact
tables. Their `BRAND NAME` remains `null`; the embedded Product reference stays
the source for brand display/filtering. No Brand Code is relabelled as a Brand.
