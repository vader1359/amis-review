create policy selections_contributor_manage on public.source_selections
for insert to authenticated
with check (
    selected_by = (select auth.uid())
    and exists (
        select 1
        from public.source_snapshots snapshot
        where snapshot.id = source_snapshot_id
          and snapshot.reporting_period_id = source_selections.reporting_period_id
          and public.is_team_member(snapshot.team_id, array['contributor', 'reviewer', 'admin'])
    )
);
