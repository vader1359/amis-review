create policy draft_sources_contributor_create on public.draft_sources
for insert to authenticated
with check (
    exists (
        select 1
        from public.psi_drafts draft
        join public.reconciliation_run_sources run_source
          on run_source.reconciliation_run_id = draft.reconciliation_run_id
        join public.source_snapshots snapshot
          on snapshot.id = run_source.source_snapshot_id
        where draft.id = draft_sources.draft_id
          and snapshot.id = draft_sources.source_snapshot_id
          and public.is_team_member(snapshot.team_id, array['contributor', 'reviewer', 'admin'])
    )
);
