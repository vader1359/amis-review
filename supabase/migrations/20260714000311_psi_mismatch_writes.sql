create policy known_issues_contributor_create on public.known_issues
for insert to authenticated
with check (
    created_by = (select auth.uid())
    and exists (
        select 1 from public.team_memberships membership
        where membership.profile_id = (select auth.uid())
          and membership.role in ('contributor', 'reviewer', 'admin')
    )
);

create policy mismatches_contributor_create on public.mismatches
for insert to authenticated
with check (
    exists (
        select 1
        from public.reconciliation_run_sources run_source
        join public.source_snapshots snapshot on snapshot.id = run_source.source_snapshot_id
        where run_source.reconciliation_run_id = mismatches.reconciliation_run_id
          and snapshot.reporting_period_id = mismatches.reporting_period_id
          and snapshot.team_id in (
              select membership.team_id
              from public.team_memberships membership
              where membership.profile_id = (select auth.uid())
                and membership.role in ('contributor', 'reviewer', 'admin')
          )
    )
);
