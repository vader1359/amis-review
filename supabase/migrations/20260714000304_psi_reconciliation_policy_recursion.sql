create or replace function public.can_insert_reconciliation_run_source(p_run_id uuid, p_snapshot_id uuid)
returns boolean
language sql
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.reconciliation_runs run
        join public.source_snapshots snapshot on snapshot.reporting_period_id = run.reporting_period_id
        where run.id = p_run_id
          and snapshot.id = p_snapshot_id
          and public.is_team_member(snapshot.team_id, array['contributor', 'reviewer', 'admin'])
    );
$$;

revoke all on function public.can_insert_reconciliation_run_source(uuid, uuid) from public, anon;
grant execute on function public.can_insert_reconciliation_run_source(uuid, uuid) to authenticated;

drop policy if exists run_sources_contributor_create on public.reconciliation_run_sources;
create policy run_sources_contributor_create on public.reconciliation_run_sources for insert to authenticated with check (
    public.can_insert_reconciliation_run_source(reconciliation_run_id, source_snapshot_id)
);
