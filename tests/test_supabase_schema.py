from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase" / "migrations"


def migration_sql() -> str:
    """Return the combined local migration source for schema assertions."""
    paths = sorted(MIGRATIONS.glob("*.sql"))
    return "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()


def test_mvp_schema_declares_required_tables() -> None:
    # Given: the local Supabase migration source.
    sql = migration_sql()
    required_tables = {
        "teams",
        "profiles",
        "team_memberships",
        "reporting_periods",
        "upload_batches",
        "source_snapshots",
        "source_selections",
        "reconciliation_runs",
        "reconciliation_run_sources",
        "normalized_records",
        "rules",
        "rule_versions",
        "mismatches",
        "mismatch_history",
        "known_issues",
        "psi_drafts",
        "draft_sources",
        "psi_releases",
        "release_sources",
        "activity_logs",
    }

    # When: migration DDL is inspected without a configured database.
    declared_tables = set(re.findall(r"create table if not exists public\.(\w+)", sql))

    # Then: every MVP persistence boundary is present.
    assert required_tables <= declared_tables


def test_mvp_schema_declares_immutable_source_and_release_provenance() -> None:
    # Given: the local Supabase migration source.
    sql = migration_sql()

    # When: source and release definitions are inspected.
    source_definition = re.search(
        r"create table if not exists public\.source_snapshots\s*\((.*?)\n\);",
        sql,
        re.DOTALL,
    )
    release_definition = re.search(
        r"create table if not exists public\.psi_releases\s*\((.*?)\n\);",
        sql,
        re.DOTALL,
    )

    # Then: both retain the fields needed to trace exact artifacts and versions.
    assert source_definition is not None
    assert release_definition is not None
    for column in ("checksum_sha256", "object_path", "version", "uploaded_at", "uploaded_by"):
        assert re.search(rf"\b{column}\b", source_definition.group(1))
    for column in ("checksum_sha256", "object_path", "reporting_period_id", "rule_version_id"):
        assert re.search(rf"\b{column}\b", release_definition.group(1))


def test_mvp_schema_has_period_selection_and_fingerprint_constraints() -> None:
    # Given: the local Supabase migration source.
    sql = migration_sql()

    # When: uniqueness and boundary checks are inspected.
    # Then: malformed periods/versions and duplicate selections are rejected by DDL.
    assert "period_key text not null" in sql
    assert "check (period_key ~ '^[0-9]{4}-(0[1-9]|1[0-2])$')" in sql
    assert "check (version > 0)" in sql
    assert "unique (team_id, reporting_period_id, source_type, version)" in sql
    assert "unique (reporting_period_id, source_type)" in sql
    assert "fingerprint text not null" in sql
    assert "unique (reconciliation_run_id, fingerprint)" in sql


def test_checkbox_four_database_features_enforce_security_contracts() -> None:
    # Given: local migrations including the checkbox-four hardening migration.
    sql = migration_sql()

    # When: schema hardening is inspected without a configured database.
    # Then: every application table is deny-by-default protected.
    assert "foreach table_name in array array[" in sql
    for table in (
        "teams", "profiles", "team_memberships", "reporting_periods",
        "upload_batches", "source_snapshots", "source_selections",
        "reconciliation_runs", "reconciliation_run_sources", "normalized_records",
        "rules", "rule_versions", "mismatches", "mismatch_history", "known_issues",
        "psi_drafts", "draft_sources", "psi_releases", "release_sources", "activity_logs",
    ):
        assert f"'{table}'" in sql
    assert "create or replace function public.transition_mismatch" in sql
    assert "reopened" in sql and "recurrence" in sql
    assert "security definer" in sql
    assert "set search_path = public" in sql
    assert "storage.buckets" in sql
    assert "values ('psi-source', 'psi-source', false)" in sql


def test_checkbox_four_immutable_and_audit_boundaries_are_explicit() -> None:
    # Given: local hardening SQL.
    sql = migration_sql()

    # When: mutation and audit policies are inspected.
    # Then: provenance fields are trigger-protected and browser audit writes are absent.
    assert "protect_source_snapshot_provenance" in sql
    assert "protect_release_provenance" in sql
    assert "raise exception 'source snapshot provenance is immutable'" in sql
    assert "raise exception 'psi release provenance is immutable'" in sql
    assert "create policy activity_logs_insert" not in sql
    assert "create policy mismatch_history_insert" not in sql
    assert "insert_activity_log" in sql
    assert "known_issues_contributor_create" in sql
    assert "mismatches_contributor_create" in sql
    assert "storage_objects_no_direct_read" in sql
    assert "storage_objects_read_source_reviewer" in sql
    assert "storage_objects_no_update" in sql
    assert "storage_objects_no_delete" in sql
    assert "storage_objects_no_insert_releases" not in sql
    assert "validate_source_snapshot_scope" in sql
    assert "protect_mismatch_updates" in sql
    assert "transition_mismatch may only change status" in sql
    assert "validate_source_object_path" in sql
    assert "array_length(parts, 1) = 3" in sql
    assert "string_to_array(p_object_path, '/')" in sql
    assert "storage.foldername(name))[1]" in sql
    assert "storage.foldername(name))[2]" in sql
    assert "storage.foldername(name))[3]" in sql
    assert "storage_objects_insert_source_own_snapshot" in sql
    assert "can_upload_source_object" in sql
    assert "bucket_id = 'psi-draft'" not in sql
    assert "bucket_id = 'psi-release'" not in sql


def test_checkbox_four_lifecycle_function_rejects_invalid_transitions() -> None:
    # Given: the lifecycle function body.
    sql = migration_sql()

    # When: transition guards are inspected.
    # Then: only the documented graph and recurrence reopening are accepted.
    assert "when 'new' then array['assigned']" in sql
    assert "when 'assigned' then array['in_progress']" in sql
    assert "when 'in_progress' then array['resolved', 'known', 'ignored']" in sql
    assert "when 'resolved' then array['reopened']" in sql
    assert "when 'known' then array['reopened']" in sql
    assert "when 'ignored' then array['reopened']" in sql
    assert "coalesce(p_evidence ->> 'recurrence', '') <> 'true'" in sql
    assert "insert into public.mismatch_history" in sql
    assert "insert into public.activity_logs" in sql
    assert "create policy drafts_team_read" in sql
    assert "create policy drafts_contributor_create" in sql
    assert "create policy draft_sources_contributor_create" in sql
    assert "create policy runs_contributor_create" in sql
    assert "create policy run_sources_contributor_create" in sql
    assert "create policy normalized_contributor_create" in sql


def test_checkbox_four_reconciliation_sources_are_team_consistent() -> None:
    # Given: the source-linking hardening SQL.
    sql = migration_sql()

    # When: reconciliation run source invariants and owner checks are inspected.
    # Then: one run cannot combine snapshots from different teams.
    assert "validate_reconciliation_run_source_team" in sql
    assert "reconciliation run source teams must match" in sql
    assert "reconciliation_run_sources_team_guard" in sql
    assert "run_owner_team" in sql


def test_checkbox_four_direct_status_updates_cannot_trust_client_guc() -> None:
    # Given: the mismatch transition trigger and privileged function.
    sql = migration_sql()

    # When: direct-update authorization is inspected.
    # Then: the client-settable GUC is insufficient without nested trigger context.
    assert "pg_trigger_depth() > 1" in sql
    assert "current_setting('psi.transition', true) = 'true'" in sql
    assert "direct status changes require transition_mismatch" in sql


def test_authenticated_role_has_table_privileges_for_rls_policies() -> None:
    sql = migration_sql()

    assert "grant select, insert on public.upload_batches to authenticated" in sql
    assert "grant select on public.team_memberships to authenticated" in sql
    assert "grant select, insert on public.source_snapshots to authenticated" in sql
    assert "create policy selections_contributor_manage" in sql


def test_source_ownership_binds_auth_login_to_each_required_source() -> None:
    # Given: the forward source ownership migration.
    migration = (MIGRATIONS / "20260722000100_psi_source_ownership.sql").read_text(encoding="utf-8").lower()

    # When: ownership and upload policies are inspected.
    # Then: every manual login maps to allowed source types through the authenticated email local-part.
    for login_id in ("purchase", "sale", "accounting", "tech"):
        assert f"('{login_id}')" in migration or f"('{login_id}')," in migration
    assert "split_part(lower(user_account.email), '@', 1) = lower(owner.login_id)" in migration
    assert "create policy snapshots_source_owner_create" in migration
    assert "public.is_psi_source_owner(source_type)" in migration
    assert "create policy selections_source_owner_manage" in migration


def test_local_auth_configuration_disables_all_self_signup() -> None:
    # Given: the local Supabase Auth configuration.
    config = (ROOT / "supabase" / "config.toml").read_text(encoding="utf-8")

    # When: both account-creation settings are inspected.
    # Then: manual accounts are the only supported login path.
    auth_section = config.split("[auth.email]", maxsplit=1)[0]
    email_section = config.split("[auth.email]", maxsplit=1)[1].split("[auth.sms]", maxsplit=1)[0]
    assert "enable_signup = false" in auth_section
    assert "enable_signup = false" in email_section


def test_source_snapshot_metadata_uses_public_schema_and_adapter_route() -> None:
    # Given: the metadata migration and the PostgREST adapter contract.
    sql = migration_sql()
    migration = (MIGRATIONS / "20260714000300_psi_source_metadata.sql").read_text(encoding="utf-8").lower()

    # When: the metadata DDL is compared with the established public schema.
    # Then: the child table and policies target the same public objects as the adapter route.
    assert "create table if not exists public.source_snapshot_metadata" in migration
    assert "public.source_snapshots" in migration
    assert "public.team_memberships" in migration
    assert "psi.source_snapshot_metadata" not in migration
    assert "source_snapshot_metadata" in sql
