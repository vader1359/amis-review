create extension if not exists pgcrypto;

create type public.psi_team as enum ('purchase', 'sale', 'accounting', 'tech');
create type public.psi_mismatch_status as enum ('open', 'handled', 'ignored');

create table public.psi_profiles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    team public.psi_team not null,
    display_name text not null,
    created_at timestamptz not null default now()
);

create table public.psi_source_snapshots (
    id uuid primary key default gen_random_uuid(),
    team public.psi_team not null,
    reporting_week text not null check (reporting_week ~ '^[0-9]{4}-W[0-9]{2}$'),
    source_type text not null check (source_type in ('product', 'purchase', 'revenue', 'inventory', 'preorder', 'crm', 'target')),
    version integer not null check (version > 0),
    original_filename text not null,
    storage_path text not null unique,
    checksum_sha256 text not null check (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint not null check (byte_size > 0),
    data_as_of date not null,
    schema_status text not null check (schema_status in ('passed', 'failed')),
    schema_details jsonb not null default '{}'::jsonb,
    uploaded_by uuid not null references auth.users(id),
    uploaded_at timestamptz not null default now(),
    check (
        (team = 'purchase' and source_type in ('product', 'purchase', 'preorder'))
        or (team = 'sale' and source_type in ('crm', 'target'))
        or (team = 'accounting' and source_type in ('revenue', 'inventory'))
        or team = 'tech'
    ),
    unique (team, reporting_week, source_type, version)
);

create index psi_source_snapshots_lookup_idx
    on public.psi_source_snapshots (reporting_week, source_type, version desc);

create view public.psi_latest_source_snapshots
with (security_invoker = true)
as
select distinct on (team, reporting_week, source_type) *
from public.psi_source_snapshots
order by team, reporting_week, source_type, version desc, uploaded_at desc;

create table public.psi_exclusion_rules (
    id uuid primary key default gen_random_uuid(),
    rule_key text not null unique,
    source_type text check (source_type is null or source_type in ('product', 'purchase', 'revenue', 'inventory', 'preorder', 'crm', 'target')),
    match_field text not null,
    match_value text not null,
    reason text not null,
    active boolean not null default true,
    created_by uuid references auth.users(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.psi_runs (
    id uuid primary key default gen_random_uuid(),
    reporting_week text not null check (reporting_week ~ '^[0-9]{4}-W[0-9]{2}$'),
    status text not null check (status in ('processing', 'completed', 'failed')),
    output_path text,
    output_checksum_sha256 text check (output_checksum_sha256 is null or output_checksum_sha256 ~ '^[0-9a-f]{64}$'),
    source_snapshot_ids uuid[] not null default '{}',
    summary jsonb not null default '{}'::jsonb,
    error_message text,
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create index psi_runs_week_idx on public.psi_runs (reporting_week, created_at desc);

create table public.psi_mismatch_cases (
    id uuid primary key default gen_random_uuid(),
    fingerprint text not null unique check (fingerprint ~ '^[0-9a-f]{64}$'),
    source_type text not null,
    record_key text not null,
    issue_type text not null,
    severity text not null default 'warning' check (severity in ('warning', 'blocking', 'info')),
    values_by_source jsonb not null default '{}'::jsonb,
    status public.psi_mismatch_status not null default 'open',
    note text,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    handled_by uuid references auth.users(id),
    handled_at timestamptz
);

create table public.psi_run_mismatches (
    run_id uuid not null references public.psi_runs(id) on delete cascade,
    mismatch_id uuid not null references public.psi_mismatch_cases(id),
    primary key (run_id, mismatch_id)
);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
    ('psi-raw', 'psi-raw', false, 52428800, array['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']),
    ('psi-output', 'psi-output', false, 52428800, array['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'])
on conflict (id) do update set
    public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

alter table public.psi_profiles enable row level security;
alter table public.psi_source_snapshots enable row level security;
alter table public.psi_exclusion_rules enable row level security;
alter table public.psi_runs enable row level security;
alter table public.psi_mismatch_cases enable row level security;
alter table public.psi_run_mismatches enable row level security;

create policy psi_profiles_read on public.psi_profiles
for select to authenticated using (true);

create policy psi_snapshots_read on public.psi_source_snapshots
for select to authenticated using (true);

create policy psi_snapshots_insert_own_team on public.psi_source_snapshots
for insert to authenticated with check (
    uploaded_by = (select auth.uid())
    and exists (
        select 1 from public.psi_profiles p
        where p.user_id = (select auth.uid())
          and (p.team = psi_source_snapshots.team or p.team = 'tech')
    )
);

create policy psi_rules_read on public.psi_exclusion_rules
for select to authenticated using (true);

create policy psi_rules_tech_manage on public.psi_exclusion_rules
for all to authenticated
using (exists (select 1 from public.psi_profiles p where p.user_id = (select auth.uid()) and p.team = 'tech'))
with check (exists (select 1 from public.psi_profiles p where p.user_id = (select auth.uid()) and p.team = 'tech'));

create policy psi_runs_read on public.psi_runs
for select to authenticated using (true);

create policy psi_mismatches_read on public.psi_mismatch_cases
for select to authenticated using (true);

create policy psi_mismatches_manual_update on public.psi_mismatch_cases
for update to authenticated using (true) with check (true);

create policy psi_run_mismatches_read on public.psi_run_mismatches
for select to authenticated using (true);

create policy psi_raw_read on storage.objects
for select to authenticated using (bucket_id = 'psi-raw');

create policy psi_raw_upload on storage.objects
for insert to authenticated with check (
    bucket_id = 'psi-raw'
    and exists (
        select 1 from public.psi_profiles p
        where p.user_id = (select auth.uid())
          and (p.team::text = (storage.foldername(name))[1] or p.team = 'tech')
    )
);

create policy psi_output_read on storage.objects
for select to authenticated using (bucket_id = 'psi-output');

grant usage on schema public to authenticated;
grant select on public.psi_profiles, public.psi_latest_source_snapshots, public.psi_exclusion_rules,
    public.psi_runs, public.psi_mismatch_cases, public.psi_run_mismatches to authenticated;
grant select, insert on public.psi_source_snapshots to authenticated;
grant insert, update, delete on public.psi_exclusion_rules to authenticated;
grant update (status, note, handled_by, handled_at) on public.psi_mismatch_cases to authenticated;
