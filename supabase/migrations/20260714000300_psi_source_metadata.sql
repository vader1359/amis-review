create table if not exists public.source_snapshot_metadata (
  source_snapshot_id uuid primary key references public.source_snapshots(id) on delete cascade,
  header_preview jsonb not null default '[]'::jsonb,
  schema_gaps jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.source_snapshot_metadata enable row level security;

create policy "team members can read source metadata"
on public.source_snapshot_metadata for select
to authenticated
using (exists (
   select 1 from public.source_snapshots snapshot
   join public.team_memberships membership on membership.team_id = snapshot.team_id
  where snapshot.id = source_snapshot_metadata.source_snapshot_id
    and membership.profile_id = auth.uid()
));

create policy "team contributors can insert source metadata"
on public.source_snapshot_metadata for insert
to authenticated
with check (exists (
   select 1 from public.source_snapshots snapshot
   join public.team_memberships membership on membership.team_id = snapshot.team_id
  where snapshot.id = source_snapshot_metadata.source_snapshot_id
    and membership.profile_id = auth.uid()
    and membership.role in ('contributor', 'reviewer', 'admin')
));

revoke update, delete on public.source_snapshot_metadata from authenticated;
