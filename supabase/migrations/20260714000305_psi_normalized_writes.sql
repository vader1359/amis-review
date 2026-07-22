create or replace function public.can_insert_normalized_record(p_snapshot_id uuid)
returns boolean
language sql
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.source_snapshots snapshot
        where snapshot.id = p_snapshot_id
          and public.is_team_member(snapshot.team_id, array['contributor', 'reviewer', 'admin'])
    );
$$;

revoke all on function public.can_insert_normalized_record(uuid) from public, anon;
grant execute on function public.can_insert_normalized_record(uuid) to authenticated;

create policy normalized_contributor_create on public.normalized_records for insert to authenticated with check (
    public.can_insert_normalized_record(source_snapshot_id)
);
