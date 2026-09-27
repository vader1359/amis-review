-- Explicit operator migration. Never run from an HTTP request.
BEGIN;
CREATE TABLE IF NOT EXISTS psi_preview.review_events (
    id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{32}$'),
    report_id text NOT NULL REFERENCES psi_preview.reports(id),
    revision integer NOT NULL CHECK (revision > 0),
    kind text NOT NULL CHECK (kind IN ('proposed', 'applied')),
    body jsonb NOT NULL CHECK (jsonb_typeof(body) = 'object'),
    request_id text NOT NULL CHECK (length(request_id) BETWEEN 1 AND 128),
    request_sha256 text NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (report_id, revision),
    UNIQUE (report_id, request_id)
);
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'review_events_immutable'
        AND tgrelid = 'psi_preview.review_events'::regclass) THEN
        CREATE TRIGGER review_events_immutable BEFORE UPDATE OR DELETE
            ON psi_preview.review_events FOR EACH ROW
            EXECUTE FUNCTION psi_preview.reject_mutation();
    END IF;
END $$;
REVOKE ALL ON psi_preview.review_events FROM PUBLIC;
GRANT SELECT, INSERT ON psi_preview.review_events TO psi_preview_app;
INSERT INTO psi_preview.schema_migrations(version) VALUES (3) ON CONFLICT DO NOTHING;
COMMIT;
