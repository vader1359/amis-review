create or replace function public.validate_source_object_path(p_object_path text)
returns boolean
language plpgsql
stable
security definer
set search_path = public, storage
as $$
declare
    parts text[] := string_to_array(p_object_path, '/');
begin
    return array_length(parts, 1) = 3
       and parts[1] ~ '^[0-9a-f-]{36}$'
       and parts[2] ~ '^[0-9a-f-]{36}$'
       and parts[3] ~ '^[0-9a-f-]{36}$';
end;
$$;

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
