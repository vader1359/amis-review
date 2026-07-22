grant select, insert, update, delete on all tables in schema public to authenticated;
grant usage, select on all sequences in schema public to authenticated;

grant select on public.team_memberships to authenticated;
grant select, insert on public.upload_batches to authenticated;
grant select, insert on public.source_snapshots to authenticated;
