insert into storage.buckets (id, name, public)
values ('psi-source', 'psi-source', false), ('psi-draft', 'psi-draft', false), ('psi-release', 'psi-release', false)
on conflict (id) do update set public = excluded.public;

create policy storage_objects_insert_source_own_team on storage.objects for insert to authenticated with check (
    bucket_id = 'psi-source'
    and (storage.foldername(name))[1] in (select team_id::text from public.team_memberships where profile_id = (select auth.uid()) and role in ('contributor', 'reviewer', 'admin'))
);
create policy storage_objects_no_direct_read on storage.objects for select to authenticated using (false);
create policy storage_objects_no_update on storage.objects for update to authenticated using (false) with check (false);
create policy storage_objects_no_delete on storage.objects for delete to authenticated using (false);
