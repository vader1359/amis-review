create or replace function public.can_upload_source_object(p_object_path text)
returns boolean
language sql
security definer
set search_path = public, storage
as $$
    select exists (
        select 1
        from public.source_snapshots snapshot
        join public.upload_batches batch on batch.id = snapshot.upload_batch_id
        where snapshot.object_path = p_object_path
          and snapshot.id::text = (storage.foldername(p_object_path))[3]
          and batch.id::text = (storage.foldername(p_object_path))[2]
          and snapshot.team_id::text = (storage.foldername(p_object_path))[1]
          and snapshot.uploaded_by = (select auth.uid())
          and public.is_team_member(snapshot.team_id, array['contributor', 'reviewer', 'admin'])
    );
$$;

revoke all on function public.can_upload_source_object(text) from public, anon;
grant execute on function public.can_upload_source_object(text) to authenticated;

drop policy if exists storage_objects_insert_source_own_snapshot on storage.objects;
create policy storage_objects_insert_source_own_snapshot on storage.objects
for insert to authenticated
with check (
    bucket_id = 'psi-source'
    and public.validate_source_object_path(name)
    and public.can_upload_source_object(name)
);
