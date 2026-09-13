-- PSI Draft online persistence v1. Apply explicitly using the direct connection.
-- This schema is isolated from published PSI and does not store original XLSX files.
BEGIN;
CREATE SCHEMA IF NOT EXISTS psi_preview;
CREATE TABLE IF NOT EXISTS psi_preview.schema_migrations (
    version integer PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS psi_preview.reports (
    id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{32}$'),
    as_of date NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    state text NOT NULL DEFAULT 'draft' CHECK (state = 'draft'),
    input_hash text NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
    workbook_sha256 text NOT NULL CHECK (workbook_sha256 ~ '^[0-9a-f]{64}$'),
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    renderer_fingerprint text NOT NULL,
    snapshot_sha256 text NOT NULL CHECK (snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    payload_json text NOT NULL,
    evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
    summary jsonb NOT NULL,
    gates jsonb NOT NULL,
    sheet_count integer NOT NULL CHECK (sheet_count = 17),
    UNIQUE (input_hash, workbook_sha256)
);
CREATE INDEX IF NOT EXISTS reports_created_at_idx
    ON psi_preview.reports (created_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS psi_preview.sheets (
    report_id text NOT NULL REFERENCES psi_preview.reports(id),
    ordinal integer NOT NULL CHECK (ordinal BETWEEN 1 AND 17),
    name text NOT NULL,
    row_count integer NOT NULL CHECK (row_count BETWEEN 1 AND 250003),
    column_count integer NOT NULL CHECK (column_count BETWEEN 1 AND 16384),
    populated_rows integer NOT NULL CHECK (populated_rows >= 0),
    cell_count integer NOT NULL CHECK (cell_count >= 0),
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (report_id, ordinal),
    UNIQUE (report_id, name)
);
CREATE TABLE IF NOT EXISTS psi_preview.sheet_rows (
    report_id text NOT NULL,
    sheet_ordinal integer NOT NULL,
    row_number integer NOT NULL CHECK (row_number BETWEEN 1 AND 250003),
    cells jsonb NOT NULL CHECK (jsonb_typeof(cells) = 'array'),
    PRIMARY KEY (report_id, sheet_ordinal, row_number),
    FOREIGN KEY (report_id, sheet_ordinal)
        REFERENCES psi_preview.sheets(report_id, ordinal)
);
CREATE OR REPLACE FUNCTION psi_preview.reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'PSI Draft snapshots are immutable';
END;
$$;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'reports_immutable'
        AND tgrelid = 'psi_preview.reports'::regclass) THEN
        CREATE TRIGGER reports_immutable BEFORE UPDATE OR DELETE
            ON psi_preview.reports FOR EACH ROW
            EXECUTE FUNCTION psi_preview.reject_mutation();
        CREATE TRIGGER sheets_immutable BEFORE UPDATE OR DELETE
            ON psi_preview.sheets FOR EACH ROW
            EXECUTE FUNCTION psi_preview.reject_mutation();
        CREATE TRIGGER sheet_rows_immutable BEFORE UPDATE OR DELETE
            ON psi_preview.sheet_rows FOR EACH ROW
            EXECUTE FUNCTION psi_preview.reject_mutation();
    END IF;
END $$;
INSERT INTO psi_preview.schema_migrations(version) VALUES (1) ON CONFLICT DO NOTHING;
COMMIT;
