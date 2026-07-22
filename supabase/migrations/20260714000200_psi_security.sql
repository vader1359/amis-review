create or replace function public.is_team_member(p_team_id uuid, p_roles text[] default null)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.team_memberships membership
        where membership.team_id = p_team_id
          and membership.profile_id = (select auth.uid())
          and (p_roles is null or membership.role = any (p_roles))
    );
$$;

revoke all on function public.is_team_member(uuid, text[]) from public, anon;
grant execute on function public.is_team_member(uuid, text[]) to authenticated;

create or replace function public.protect_source_snapshot_provenance()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    if tg_op = 'DELETE' then
        raise exception 'source snapshot provenance is immutable';
    elsif (
        new.object_path is distinct from old.object_path
        or new.checksum_sha256 is distinct from old.checksum_sha256
        or new.upload_batch_id is distinct from old.upload_batch_id
        or new.team_id is distinct from old.team_id
        or new.reporting_period_id is distinct from old.reporting_period_id
        or new.source_type is distinct from old.source_type
        or new.version is distinct from old.version
        or new.original_filename is distinct from old.original_filename
        or new.byte_size is distinct from old.byte_size
        or new.data_as_of is distinct from old.data_as_of
        or new.schema_status is distinct from old.schema_status
        or new.row_count is distinct from old.row_count
        or new.uploaded_by is distinct from old.uploaded_by
        or new.uploaded_at is distinct from old.uploaded_at
    ) then
        raise exception 'source snapshot provenance is immutable';
    end if;
    return new;
end;
$$;

create trigger source_snapshots_provenance_guard
before update or delete on public.source_snapshots
for each row execute function public.protect_source_snapshot_provenance();

create or replace function public.validate_source_snapshot_scope()
returns trigger
language plpgsql
set search_path = public
as $$
declare
    batch public.upload_batches;
begin
    select * into batch from public.upload_batches where id = new.upload_batch_id;
    if batch.id is null
       or batch.team_id is distinct from new.team_id
       or batch.reporting_period_id is distinct from new.reporting_period_id then
        raise exception 'source snapshot scope does not match upload batch';
    end if;
    return new;
end;
$$;

create trigger source_snapshots_scope_guard
before insert or update on public.source_snapshots
for each row execute function public.validate_source_snapshot_scope();

create or replace function public.protect_release_provenance()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    if tg_op = 'DELETE' then
        raise exception 'psi release provenance is immutable';
    elsif (
        new.psi_draft_id is distinct from old.psi_draft_id
        or new.reporting_period_id is distinct from old.reporting_period_id
        or new.rule_version_id is distinct from old.rule_version_id
        or new.object_path is distinct from old.object_path
        or new.checksum_sha256 is distinct from old.checksum_sha256
        or new.row_count is distinct from old.row_count
        or new.kpis is distinct from old.kpis
        or new.approved_by is distinct from old.approved_by
        or new.published_by is distinct from old.published_by
        or new.published_at is distinct from old.published_at
    ) then
        raise exception 'psi release provenance is immutable';
    end if;
    return new;
end;
$$;

create trigger psi_releases_provenance_guard
before update or delete on public.psi_releases
for each row execute function public.protect_release_provenance();

create or replace function public.transition_mismatch(
    p_mismatch_id uuid,
    p_to_status text,
    p_comment text default null,
    p_evidence jsonb default '{}'::jsonb
)
returns public.mismatches
language plpgsql
security definer
set search_path = public
as $$
declare
    mismatch public.mismatches;
    from_status text;
    allowed text[];
    actor uuid := (select auth.uid());
begin
    select * into mismatch from public.mismatches where id = p_mismatch_id for update;
    if mismatch.id is null then
        raise exception 'mismatch not found';
    end if;
    if not exists (
        select 1 from public.reconciliation_run_sources run_source
        join public.source_snapshots snapshot on snapshot.id = run_source.source_snapshot_id
        where run_source.reconciliation_run_id = mismatch.reconciliation_run_id
          and public.is_team_member(snapshot.team_id, array['reviewer', 'admin'])
    ) then
        raise exception 'mismatch access denied';
    end if;
    allowed := case mismatch.status
        when 'new' then array['assigned']
        when 'assigned' then array['in_progress']
        when 'in_progress' then array['resolved', 'known', 'ignored']
        when 'resolved' then array['reopened']
        when 'known' then array['reopened']
        when 'ignored' then array['reopened']
        when 'reopened' then array['assigned']
        else array[]::text[]
    end;
    if not (p_to_status = any (allowed)) then
        raise exception 'invalid mismatch transition from % to %', mismatch.status, p_to_status;
    end if;
    from_status := mismatch.status;
    if p_to_status = 'reopened' and coalesce(p_evidence ->> 'recurrence', '') <> 'true' then
        raise exception 'reopened is only valid on recurrence';
    end if;
    perform set_config('psi.transition', 'true', true);
    update public.mismatches
    set status = p_to_status,
        resolved_at = case when p_to_status = 'resolved' then now() else null end
    where id = p_mismatch_id
    returning * into mismatch;
    insert into public.mismatch_history (mismatch_id, changed_by, from_status, to_status, comment, evidence)
    values (mismatch.id, actor, from_status, p_to_status, p_comment, p_evidence);
    insert into public.activity_logs (team_id, actor_id, action, entity_type, entity_id, metadata)
    select snapshot.team_id, actor, 'mismatch.transitioned', 'mismatch', mismatch.id,
           jsonb_build_object('from_status', from_status, 'to_status', p_to_status)
    from public.reconciliation_run_sources run_source
    join public.source_snapshots snapshot on snapshot.id = run_source.source_snapshot_id
    where run_source.reconciliation_run_id = mismatch.reconciliation_run_id
    limit 1;
    return mismatch;
end;
$$;

revoke all on function public.transition_mismatch(uuid, text, text, jsonb) from public, anon;
grant execute on function public.transition_mismatch(uuid, text, text, jsonb) to authenticated;

create or replace function public.require_transition_function()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    if new.status is distinct from old.status
       and current_setting('psi.transition', true) is distinct from 'true' then
        raise exception 'mismatch status changes require transition_mismatch';
    end if;
    return new;
end;
$$;

create trigger mismatches_transition_guard
before update on public.mismatches
for each row execute function public.require_transition_function();

create or replace function public.protect_mismatch_updates()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    if current_setting('psi.transition', true) = 'true' then
        if new.id is distinct from old.id
           or new.reconciliation_run_id is distinct from old.reconciliation_run_id
           or new.reporting_period_id is distinct from old.reporting_period_id
           or new.rule_version_id is distinct from old.rule_version_id
           or new.source_type is distinct from old.source_type
           or new.record_key is distinct from old.record_key
           or new.fingerprint is distinct from old.fingerprint
           or new.severity is distinct from old.severity
           or new.values_by_source is distinct from old.values_by_source
           or new.assigned_to is distinct from old.assigned_to
           or new.known_issue_id is distinct from old.known_issue_id
           or new.created_at is distinct from old.created_at then
            raise exception 'transition_mismatch may only change status';
        end if;
    elsif new.status is distinct from old.status
       or new.known_issue_id is distinct from old.known_issue_id
       or new.resolved_at is distinct from old.resolved_at
       or new.values_by_source is distinct from old.values_by_source
       or new.reconciliation_run_id is distinct from old.reconciliation_run_id
       or new.reporting_period_id is distinct from old.reporting_period_id
       or new.rule_version_id is distinct from old.rule_version_id
       or new.source_type is distinct from old.source_type
       or new.record_key is distinct from old.record_key
       or new.fingerprint is distinct from old.fingerprint
       or new.severity is distinct from old.severity
       or new.created_at is distinct from old.created_at then
        raise exception 'browser mismatch updates may only assign a reviewer';
    end if;
    return new;
end;
$$;

create trigger mismatches_field_guard
before update on public.mismatches
for each row execute function public.protect_mismatch_updates();

do $$
declare
    table_name text;
begin
    foreach table_name in array array[
        'teams', 'profiles', 'team_memberships', 'reporting_periods', 'upload_batches',
        'source_snapshots', 'source_selections', 'reconciliation_runs',
        'reconciliation_run_sources', 'normalized_records', 'rules', 'rule_versions',
        'mismatches', 'mismatch_history', 'known_issues', 'psi_drafts', 'draft_sources',
        'psi_releases', 'release_sources', 'activity_logs'
    ] loop
        execute format('alter table public.%I enable row level security', table_name);
    end loop;
end;
$$;
