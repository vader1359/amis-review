create or replace function public.insert_activity_log(
    p_team_id uuid,
    p_actor_id uuid,
    p_action text,
    p_entity_type text,
    p_entity_id uuid,
    p_metadata jsonb default '{}'::jsonb
)
returns public.activity_logs
language plpgsql
security definer
set search_path = public
as $$
declare
    result public.activity_logs;
begin
    if p_actor_id is distinct from (select auth.uid()) then
        raise exception 'activity actor mismatch';
    end if;
    if not public.is_team_member(p_team_id, array['contributor', 'reviewer', 'admin']) then
        raise exception 'activity team access denied';
    end if;
    if p_entity_type = 'source_snapshot' and not exists (
        select 1 from public.source_snapshots snapshot
        where snapshot.id = p_entity_id and snapshot.team_id = p_team_id
    ) then
        raise exception 'activity entity access denied';
    end if;
    insert into public.activity_logs(team_id, actor_id, action, entity_type, entity_id, metadata)
    values (p_team_id, p_actor_id, p_action, p_entity_type, p_entity_id, p_metadata)
    returning * into result;
    return result;
end;
$$;

revoke all on function public.insert_activity_log(uuid, uuid, text, text, uuid, jsonb) from public, anon;
grant execute on function public.insert_activity_log(uuid, uuid, text, text, uuid, jsonb) to authenticated;
