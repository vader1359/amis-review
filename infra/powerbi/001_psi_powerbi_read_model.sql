-- Power BI read model for validated PSI snapshots.
--
-- Apply only after infra/sql/psi_preview_reports.sql, using the direct Neon
-- migration connection.  This script never selects the most recent Draft:
-- Power BI reads only an immutable report_id that an operator pinned by adding
-- a psi_powerbi.report_selections row.  A corrected local snapshot is allowed
-- only when explicitly labelled as such; it does not become an approved Final.
BEGIN;

CREATE SCHEMA IF NOT EXISTS psi_powerbi;

CREATE TABLE IF NOT EXISTS psi_powerbi.reference_snapshots (
    id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{32}$'),
    reference_kind text NOT NULL CHECK (reference_kind IN ('product', 'target')),
    reference_label text NOT NULL CHECK (length(btrim(reference_label)) > 0),
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    rows jsonb NOT NULL CHECK (jsonb_typeof(rows) = 'array'),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS psi_powerbi.report_selections (
    selection_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_key text NOT NULL CHECK (dataset_key = 'psi_2026'),
    report_id text NOT NULL REFERENCES psi_preview.reports(id) ON DELETE RESTRICT,
    product_reference_id text NOT NULL REFERENCES psi_powerbi.reference_snapshots(id)
        ON DELETE RESTRICT,
    target_reference_id text NOT NULL REFERENCES psi_powerbi.reference_snapshots(id)
        ON DELETE RESTRICT,
    selection_kind text NOT NULL CHECK (selection_kind IN (
        'operator_selected_snapshot',
        'operator_selected_corrected_local_snapshot'
    )),
    selection_note text NOT NULL CHECK (length(btrim(selection_note)) > 0),
    selected_by text NOT NULL CHECK (length(btrim(selected_by)) > 0),
    selected_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS report_selections_dataset_order_idx
    ON psi_powerbi.report_selections (dataset_key, selection_id DESC);

CREATE OR REPLACE FUNCTION psi_powerbi.reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Power BI PSI lineage records are immutable';
END;
$$;

CREATE OR REPLACE FUNCTION psi_powerbi.validate_product_reference() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.reference_kind = 'product' AND EXISTS (
        SELECT 1
        FROM jsonb_array_elements(NEW.rows) item(value)
        GROUP BY lower(btrim(item.value->>'PRODUCT ID'))
        HAVING count(*) > 1 OR bool_or(NULLIF(btrim(item.value->>'PRODUCT ID'), '') IS NULL)
    ) THEN
        RAISE EXCEPTION 'Product reference must have one nonblank case-insensitive PRODUCT ID per row';
    END IF;
    RETURN NEW;
END;
$$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'reference_snapshots_immutable'
        AND tgrelid = 'psi_powerbi.reference_snapshots'::regclass) THEN
        CREATE TRIGGER reference_snapshots_immutable BEFORE UPDATE OR DELETE
            ON psi_powerbi.reference_snapshots FOR EACH ROW
            EXECUTE FUNCTION psi_powerbi.reject_mutation();
        CREATE TRIGGER report_selections_immutable BEFORE UPDATE OR DELETE
            ON psi_powerbi.report_selections FOR EACH ROW
            EXECUTE FUNCTION psi_powerbi.reject_mutation();
    END IF;
END $$;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'product_reference_unique_sku'
        AND tgrelid = 'psi_powerbi.reference_snapshots'::regclass) THEN
        CREATE TRIGGER product_reference_unique_sku BEFORE INSERT
            ON psi_powerbi.reference_snapshots FOR EACH ROW
            EXECUTE FUNCTION psi_powerbi.validate_product_reference();
    END IF;
END $$;

-- This is deliberately the newest *operator selection event*, never the newest
-- psi_preview.reports row.  The reports table itself is immutable and its writer
-- has already required payload, Parquet and workbook PASS evidence.
CREATE OR REPLACE VIEW psi_powerbi.selected_reports AS
SELECT DISTINCT ON (s.dataset_key)
    s.dataset_key, s.report_id, s.product_reference_id, s.target_reference_id,
    s.selection_kind, s.selection_note, s.selected_by, s.selected_at,
    r.as_of, r.payload_sha256, r.workbook_sha256, r.payload
FROM psi_powerbi.report_selections s
JOIN psi_preview.reports r ON r.id = s.report_id
ORDER BY s.dataset_key, s.selection_id DESC;

CREATE OR REPLACE VIEW psi_powerbi.product_reference AS
WITH source_rows AS (
SELECT
    sr.dataset_key, item.ordinality,
    item.value->>'NO.' AS "NO.",
    item.value->>'PRODUCT ID' AS "PRODUCT ID",
    item.value->>'PRODUCT NAME' AS "PRODUCT NAME",
    item.value->>'CATEGORIES' AS "CATEGORIES",
    item.value->>'SUBCATEGORIES' AS "SUBCATEGORIES",
    item.value->>'BRAND NAME' AS "BRAND NAME",
    item.value->>'BRAND CODE' AS "BRAND CODE",
    item.value->>'SUPPLIER' AS "SUPPLIER",
    item.value->>'SUPPLIER BC' AS "SUPPLIER BC",
    item.value->>'SERIES' AS "SERIES",
    item.value->>'Image' AS "Image",
    NULLIF(item.value->>'GIÁ BÁN LẺ MISA', '')::numeric AS "GIÁ BÁN LẺ MISA",
    item.value->>'BRAND NAME BC' AS "BRAND NAME BC"
FROM psi_powerbi.selected_reports sr
JOIN psi_powerbi.reference_snapshots ref ON ref.id = sr.product_reference_id
CROSS JOIN LATERAL jsonb_array_elements(ref.rows) WITH ORDINALITY item(value, ordinality)
WHERE ref.reference_kind = 'product'
)
SELECT DISTINCT ON (dataset_key, lower(btrim("PRODUCT ID")))
    dataset_key, "NO.", "PRODUCT ID", "PRODUCT NAME", "CATEGORIES",
    "SUBCATEGORIES", "BRAND NAME", "BRAND CODE", "SUPPLIER", "SUPPLIER BC",
    "SERIES", "Image", "GIÁ BÁN LẺ MISA", "BRAND NAME BC"
FROM source_rows
WHERE NULLIF(btrim("PRODUCT ID"), '') IS NOT NULL
ORDER BY dataset_key, lower(btrim("PRODUCT ID")), ordinality DESC;

CREATE OR REPLACE VIEW psi_powerbi.target_reference AS
SELECT
    sr.dataset_key,
    item.value->>'SUPPLIER BC' AS "SUPPLIER BC",
    NULLIF(item.value->>'TARGET 2026', '')::numeric AS "TARGET 2026",
    item.value->>'Supplier Image' AS "Supplier Image",
    NULLIF(item.value->>'Supplier Target', '')::numeric AS "Supplier Target"
FROM psi_powerbi.selected_reports sr
JOIN psi_powerbi.reference_snapshots ref ON ref.id = sr.target_reference_id
CROSS JOIN LATERAL jsonb_array_elements(ref.rows) item(value)
WHERE ref.reference_kind = 'target';

CREATE OR REPLACE VIEW psi_powerbi.inventory AS
SELECT
    NULLIF(row.value->>1, '')::date AS "Date",
    row.value->>2 AS "PRODUCT ID",
    NULLIF(row.value->>8, '')::numeric AS "QUANTITY",
    NULLIF(row.value->>9, '')::numeric AS "VALUE",
    row.value->>10 AS "WAREHOUSE",
    NULLIF(row.value->>9, '')::numeric / NULLIF(NULLIF(row.value->>8, '')::numeric, 0) AS "VALUE/unit",
    row.value->>3 AS "PRODUCT NAME", row.value->>6 AS "SUPPLIER", p."BRAND NAME",
    row.value->>4 AS "CATEGORIES", row.value->>5 AS "SUBCATEGORIES"
FROM psi_powerbi.selected_reports sr
CROSS JOIN LATERAL jsonb_array_elements(sr.payload->'inventory_rows') row(value)
LEFT JOIN psi_powerbi.product_reference p
    ON p.dataset_key = sr.dataset_key AND lower(btrim(p."PRODUCT ID")) = lower(btrim(row.value->>2));

CREATE OR REPLACE VIEW psi_powerbi.revenue AS
SELECT
    NULLIF(row.value->>0, '')::bigint AS "NO",
    NULLIF(row.value->>1, '')::date AS "SALES DATE",
    row.value->>2 AS "PRODUCT ID",
    NULLIF(row.value->>8, '')::numeric AS "QUANTITY SOLD",
    NULLIF(row.value->>9, '')::numeric AS "NET REV SOLD",
    NULLIF(row.value->>10, '')::numeric / NULLIF(NULLIF(row.value->>8, '')::numeric, 0) AS "COST/UNIT",
    NULLIF(row.value->>10, '')::numeric AS "COGS",
    row.value->>11 AS "SALE ORDER",
    row.value->>3 AS "Product name", row.value->>6 AS "SUPPLIER", p."BRAND NAME",
    row.value->>4 AS "CATEGORIES", row.value->>5 AS "SUBCATEGORIES"
FROM psi_powerbi.selected_reports sr
CROSS JOIN LATERAL jsonb_array_elements(sr.payload->'revenue_rows') row(value)
LEFT JOIN psi_powerbi.product_reference p
    ON p.dataset_key = sr.dataset_key AND lower(btrim(p."PRODUCT ID")) = lower(btrim(row.value->>2));

CREATE OR REPLACE VIEW psi_powerbi.preorder AS
SELECT
    NULLIF(row.value->>1, '')::date AS "Date",
    row.value->>2 AS "PRODUCT ID",
    NULLIF(row.value->>8, '')::numeric AS "QUANTITY SOLD",
    NULLIF(row.value->>9, '')::numeric AS "NET REV SOLD",
    NULL::numeric AS "COST/UNIT",
    row.value->>12 AS "ĐH",
    NULLIF(row.value->>13, '')::date AS "HẠN GIAO HÀNG",
    NULL::numeric AS "COGS",
    COALESCE(p."PRODUCT NAME", row.value->>3) AS "Product name",
    COALESCE(p."SUPPLIER", row.value->>6) AS "SUPPLIER", p."BRAND NAME",
    COALESCE(p."CATEGORIES", row.value->>4) AS "CATEGORIES",
    COALESCE(p."SUBCATEGORIES", row.value->>5) AS "SUBCATEGORIES"
FROM psi_powerbi.selected_reports sr
CROSS JOIN LATERAL jsonb_array_elements(sr.payload->'preorder_rows') row(value)
LEFT JOIN psi_powerbi.product_reference p
    ON p.dataset_key = sr.dataset_key AND lower(btrim(p."PRODUCT ID")) = lower(btrim(row.value->>2));

CREATE OR REPLACE VIEW psi_powerbi.sales_crm AS
SELECT
    NULLIF(row.value->>5, '')::date AS "SALES DATE",
    row.value->>1 AS "PRODUCT ID",
    NULLIF(row.value->>3, '')::numeric AS "QUANTITY SOLD",
    NULLIF(row.value->>4, '')::numeric AS "NET REV SOLD",
    NULL::numeric AS "COST/UNIT",
    NULL::numeric AS "COGS",
    row.value->>0 AS "SALE ORDER",
    COALESCE(p."PRODUCT NAME", row.value->>2) AS "Product name",
    p."SUPPLIER", p."BRAND NAME", p."CATEGORIES", p."SUBCATEGORIES",
    NULL::text AS "CUSTOMER"
FROM psi_powerbi.selected_reports sr
CROSS JOIN LATERAL jsonb_array_elements(sr.payload->'crm_product_rows') row(value)
LEFT JOIN psi_powerbi.product_reference p
    ON p.dataset_key = sr.dataset_key AND lower(btrim(p."PRODUCT ID")) = lower(btrim(row.value->>1));

CREATE OR REPLACE VIEW psi_powerbi.purchase AS
SELECT
    row.value->>1 AS "Tình trạng",
    NULL::text AS "Số HĐ",
    row.value->>3 AS "Số PO",
    NULLIF(row.value->>5, '')::date AS "PO DATE",
    NULL::date AS "STOCK-IN DATE",
    row.value->>8 AS "PRODUCT ID",
    NULLIF(row.value->>10, '')::numeric AS "QUANTITY",
    NULL::numeric AS "PRICE ORDER",
    NULL::numeric AS "TOTAL AMOUNT",
    row.value->>12 AS "CURRENCY",
    NULL::text AS "F.O.C",
    NULLIF(row.value->>11, '')::numeric / NULLIF(NULLIF(row.value->>10, '')::numeric, 0) AS "WAREHOUSE VALUE/UNIT",
    NULLIF(row.value->>11, '')::numeric AS "TOTAL WAREHOUSE VALUE",
    NULL::text AS "Process Stage",
    NULL::text AS "Loading No.",
    row.value->>4 AS "SALES ORDER",
    EXTRACT(YEAR FROM NULLIF(row.value->>5, '')::date)::integer AS "YEAR",
    NULL::numeric AS "Tỷ giá",
    NULL::numeric AS "Import tax",
    NULL::text AS "Transport Mode",
    NULL::date AS "ETD",
    NULLIF(row.value->>14, '')::date AS "ETA",
    NULL::numeric AS "Deposit", NULL::date AS "Deposit Date", NULL::text AS "Deposit status",
    NULL::numeric AS "Payment", NULL::date AS "Payment date", NULL::text AS "Payment  status",
    NULL::numeric AS "Balance", NULL::numeric AS "Transport cost", NULL::text AS "Transport cost status",
    NULL::numeric AS "Serive cost", NULL::text AS "Số Lô",
    COALESCE(p."PRODUCT NAME", row.value->>9) AS "PRODUCT NAME"
FROM psi_powerbi.selected_reports sr
CROSS JOIN LATERAL jsonb_array_elements(sr.payload->'purchase_rows') row(value)
LEFT JOIN psi_powerbi.product_reference p
    ON p.dataset_key = sr.dataset_key AND lower(btrim(p."PRODUCT ID")) = lower(btrim(row.value->>8));

DROP VIEW IF EXISTS psi_powerbi.stock_in;
CREATE VIEW psi_powerbi.stock_in AS
SELECT
    NULL::text AS "PRODUCT ID", NULL::bigint AS "index", NULL::numeric AS "Cumulative",
    NULL::date AS "Stock in date", NULL::text AS "Số chứng từ", NULL::numeric AS "QUANTITY",
    NULL::bigint AS "Index", NULL::numeric AS "CumQty", NULL::numeric AS "PrevCumQty",
    NULL::numeric AS "Total stock in"
WHERE FALSE;

CREATE OR REPLACE VIEW psi_powerbi.lineage AS
SELECT
    sr.dataset_key, sr.report_id, sr.as_of, sr.payload_sha256, sr.workbook_sha256,
    sr.selection_kind, sr.selection_note, sr.selected_by, sr.selected_at,
    product.reference_label AS product_reference_label,
    target.reference_label AS target_reference_label
FROM psi_powerbi.selected_reports sr
JOIN psi_powerbi.reference_snapshots product ON product.id = sr.product_reference_id
JOIN psi_powerbi.reference_snapshots target ON target.id = sr.target_reference_id;

REVOKE ALL ON SCHEMA psi_powerbi FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA psi_powerbi FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA psi_powerbi FROM PUBLIC;
-- Replace powerbi_reader with the least-privileged role used by the gateway.
GRANT USAGE ON SCHEMA psi_powerbi TO powerbi_reader;
GRANT SELECT ON psi_powerbi.product_reference, psi_powerbi.target_reference,
    psi_powerbi.inventory, psi_powerbi.revenue, psi_powerbi.preorder,
    psi_powerbi.sales_crm, psi_powerbi.purchase, psi_powerbi.stock_in,
    psi_powerbi.lineage TO powerbi_reader;

COMMIT;
