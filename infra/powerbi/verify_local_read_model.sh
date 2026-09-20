#!/usr/bin/env bash
# Run only against an isolated local PostgreSQL test database.  It recreates the
# two PSI schemas, loads the corrected local payload/reference fixture, then
# prints the eight table row counts for comparison with refresh-data.json.
set -euo pipefail

: "${PSI_POWERBI_TEST_DATABASE_URL:?set an isolated local PostgreSQL URL}"
: "${PSI_POWERBI_PAYLOAD_PATH:?set corrected-payload.json path visible to the local server}"
: "${PSI_POWERBI_REFRESH_DATA_PATH:?set refresh-data.json path visible to the local server}"

root=$(cd "$(dirname "$0")/../.." && pwd)
psql "$PSI_POWERBI_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -c 'DROP SCHEMA IF EXISTS psi_powerbi CASCADE; DROP SCHEMA IF EXISTS psi_preview CASCADE;'
psql "$PSI_POWERBI_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'powerbi_reader') THEN CREATE ROLE powerbi_reader; END IF; END \$\$;"
psql "$PSI_POWERBI_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$root/infra/sql/psi_preview_reports.sql"
psql "$PSI_POWERBI_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$root/infra/powerbi/001_psi_powerbi_read_model.sql"
psql "$PSI_POWERBI_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -v payload="$PSI_POWERBI_PAYLOAD_PATH" -v fixture="$PSI_POWERBI_REFRESH_DATA_PATH" <<'SQL'
INSERT INTO psi_preview.reports (id,as_of,input_hash,workbook_sha256,payload_sha256,renderer_fingerprint,snapshot_sha256,payload,payload_json,evidence,summary,gates,sheet_count)
SELECT repeat('c',32),'2026-09-03',repeat('a',64),repeat('b',64),repeat('d',64),'local-test',repeat('e',64),pg_read_file(:'payload')::jsonb,pg_read_file(:'payload'),'{}','{}','[]',17;
INSERT INTO psi_powerbi.reference_snapshots (id,reference_kind,reference_label,source_sha256,rows)
SELECT repeat('a',32),'product','local Product reference fixture',repeat('f',64),(pg_read_file(:'fixture')::jsonb)->'1. Product';
INSERT INTO psi_powerbi.reference_snapshots (id,reference_kind,reference_label,source_sha256,rows)
SELECT repeat('b',32),'target','local Target reference fixture',repeat('1',64),(pg_read_file(:'fixture')::jsonb)->'Target';
INSERT INTO psi_powerbi.report_selections (dataset_key,report_id,product_reference_id,target_reference_id,selection_kind,selection_note,selected_by)
VALUES ('psi_2026',repeat('c',32),repeat('a',32),repeat('b',32),'operator_selected_corrected_local_snapshot','local parity fixture only','local-test');
SELECT (SELECT count(*) FROM psi_powerbi.inventory) AS inventory,
       (SELECT count(*) FROM psi_powerbi.revenue) AS revenue,
       (SELECT count(*) FROM psi_powerbi.preorder) AS preorder,
       (SELECT count(*) FROM psi_powerbi.sales_crm) AS sales_crm,
       (SELECT count(*) FROM psi_powerbi.purchase) AS purchase,
       (SELECT count(*) FROM psi_powerbi.product_reference) AS product,
       (SELECT count(*) FROM psi_powerbi.target_reference) AS target,
       (SELECT count(*) FROM psi_powerbi.stock_in) AS stock_in;
SQL
