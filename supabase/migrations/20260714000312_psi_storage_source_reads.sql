create policy storage_objects_read_source_reviewer on storage.objects
for select to authenticated using (
    bucket_id = 'psi-source'
    and public.validate_source_object_path(name)
    and (string_to_array(name, '/'))[1] in (
        select membership.team_id::text
        from public.team_memberships membership
        where membership.profile_id = (select auth.uid())
          and membership.role in ('reviewer', 'admin')
    )
);
