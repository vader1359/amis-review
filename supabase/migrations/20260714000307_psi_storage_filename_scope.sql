create or replace function public.validate_source_object_path(p_object_path text)
returns boolean
language plpgsql
stable
security definer
set search_path = public, storage
as $$
declare
    parts text[] := storage.foldername(p_object_path);
begin
    return array_length(parts, 1) = 4
       and parts[1] ~ '^[0-9a-f-]{36}$'
       and parts[2] ~ '^[0-9a-f-]{36}$'
       and parts[3] ~ '^[0-9a-f-]{36}$'
       and length(trim(parts[4])) > 0;
end;
$$;
