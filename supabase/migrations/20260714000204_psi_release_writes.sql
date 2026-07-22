create policy storage_objects_insert_draft_release on storage.objects for insert to authenticated with check (
    bucket_id in ('psi-draft', 'psi-release')
    and (storage.foldername(name))[1] in (
        select team_id::text from public.team_memberships
        where profile_id = (select auth.uid()) and role in ('reviewer', 'admin')
    )
);

create policy releases_reviewer_create on public.psi_releases for insert to authenticated with check (
    approved_by = (select auth.uid()) and published_by = (select auth.uid())
    and exists (
        select 1 from public.psi_drafts d
        join public.reconciliation_run_sources rs on rs.reconciliation_run_id = d.reconciliation_run_id
        join public.source_snapshots s on s.id = rs.source_snapshot_id
        where d.id = psi_releases.psi_draft_id
        and public.is_team_member(s.team_id, array['reviewer', 'admin'])
    )
);

create policy release_sources_reviewer_create on public.release_sources for insert to authenticated with check (
    exists (
        select 1 from public.psi_releases r
        join public.psi_drafts d on d.id = r.psi_draft_id
        join public.reconciliation_run_sources rs on rs.reconciliation_run_id = d.reconciliation_run_id
        join public.source_snapshots s on s.id = rs.source_snapshot_id
        where r.id = release_sources.release_id
        and public.is_team_member(s.team_id, array['reviewer', 'admin'])
    )
);
