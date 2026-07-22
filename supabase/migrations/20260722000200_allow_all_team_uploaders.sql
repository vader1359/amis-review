-- MVP policy: any authenticated member of the selected team may upload and
-- select any PSI source.  Keep the ownership tables for audit/backward
-- compatibility, but do not use them as an upload gate.

drop policy if exists snapshots_source_owner_create on public.source_snapshots;
create policy snapshots_team_member_create on public.source_snapshots
for insert to authenticated
with check (
    uploaded_by = (select auth.uid())
    and public.is_team_member(team_id, array['contributor', 'reviewer', 'admin'])
);

drop policy if exists selections_source_owner_manage on public.source_selections;
create policy selections_team_member_manage on public.source_selections
for insert to authenticated
with check (
    selected_by = (select auth.uid())
    and exists (
        select 1
        from public.source_snapshots snapshot
        where snapshot.id = source_snapshot_id
          and snapshot.reporting_period_id = source_selections.reporting_period_id
          and snapshot.source_type = source_selections.source_type
          and public.is_team_member(snapshot.team_id, array['contributor', 'reviewer', 'admin'])
    )
);

create or replace function public.can_upload_source_object(p_object_path text)
returns boolean
language sql
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.source_snapshots snapshot
        join public.upload_batches batch on batch.id = snapshot.upload_batch_id
        where snapshot.object_path = p_object_path
          and snapshot.id::text = (string_to_array(p_object_path, '/'))[3]
          and batch.id::text = (string_to_array(p_object_path, '/'))[2]
          and snapshot.team_id::text = (string_to_array(p_object_path, '/'))[1]
          and snapshot.uploaded_by = (select auth.uid())
          and public.is_team_member(snapshot.team_id, array['contributor', 'reviewer', 'admin'])
    );
$$;
