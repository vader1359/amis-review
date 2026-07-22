create or replace function public.validate_source_object_path(p_object_path text)
returns boolean
language plpgsql
stable
security definer
set search_path = public, storage
as $$
declare
    parts text[] := storage.foldername(p_object_path);
begin
    return array_length(parts, 1) = 3
       and parts[1] ~ '^[0-9a-f-]{36}$'
       and parts[2] ~ '^[0-9a-f-]{36}$'
       and parts[3] ~ '^[0-9a-f-]{36}$';
end;
$$;

revoke all on function public.validate_source_object_path(text) from public, anon;
grant execute on function public.validate_source_object_path(text) to authenticated;

drop policy if exists storage_objects_insert_source_own_team on storage.objects;
create policy storage_objects_insert_source_own_snapshot on storage.objects
for insert to authenticated
with check (
    bucket_id = 'psi-source'
    and public.validate_source_object_path(name)
    and (storage.foldername(name))[1] in (
        select membership.team_id::text
        from public.team_memberships membership
        where membership.profile_id = (select auth.uid())
          and membership.role in ('contributor', 'reviewer', 'admin')
    )
    and exists (
        select 1
        from public.source_snapshots snapshot
        join public.upload_batches batch on batch.id = snapshot.upload_batch_id
        where snapshot.object_path = name
          and snapshot.id::text = (storage.foldername(name))[3]
          and batch.id::text = (storage.foldername(name))[2]
          and snapshot.team_id::text = (storage.foldername(name))[1]
          and snapshot.uploaded_by = (select auth.uid())
    )
);

create or replace function public.run_owner_team(p_run_id uuid)
returns uuid
language sql
stable
security definer
set search_path = public
as $$
    select membership.team_id
    from public.reconciliation_runs run
    join public.team_memberships membership on membership.profile_id = run.started_by
    where run.id = p_run_id
    order by membership.team_id
    limit 1;
$$;

revoke all on function public.run_owner_team(uuid) from public, anon;
grant execute on function public.run_owner_team(uuid) to authenticated;

create or replace function public.validate_reconciliation_run_source_team()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    snapshot_team uuid;
begin
    select team_id into snapshot_team
    from public.source_snapshots
    where id = new.source_snapshot_id;
    if snapshot_team is null or public.run_owner_team(new.reconciliation_run_id) is distinct from snapshot_team
       or exists (
           select 1
           from public.reconciliation_run_sources existing
           join public.source_snapshots existing_snapshot
             on existing_snapshot.id = existing.source_snapshot_id
           where existing.reconciliation_run_id = new.reconciliation_run_id
             and existing_snapshot.team_id is distinct from snapshot_team
       ) then
        raise exception 'reconciliation run source teams must match';
    end if;
    return new;
end;
$$;

drop trigger if exists reconciliation_run_sources_team_guard on public.reconciliation_run_sources;
create trigger reconciliation_run_sources_team_guard
before insert or update on public.reconciliation_run_sources
for each row execute function public.validate_reconciliation_run_source_team();

create or replace function public.require_transition_function()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    if pg_trigger_depth() > 1 and current_user <> 'postgres' then
        raise exception 'nested mismatch updates require transition_mismatch';
    end if;
    if new.status is distinct from old.status
       and not (
           current_user = 'postgres'
           and pg_trigger_depth() = 1
           and current_setting('psi.transition', true) = 'true'
       ) then
        raise exception 'direct status changes require transition_mismatch';
    end if;
    return new;
end;
$$;

create or replace function public.protect_mismatch_updates()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    if current_user = 'postgres'
       and pg_trigger_depth() = 1
       and current_setting('psi.transition', true) = 'true' then
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
