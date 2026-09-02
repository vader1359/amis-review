create extension if not exists pgcrypto;

create type public.psi_team as enum ('purchase', 'sale', 'accounting', 'tech');
create type public.psi_source as enum ('product', 'purchase', 'preorder', 'crm', 'target', 'revenue', 'inventory');
create type public.psi_schema_status as enum ('passed', 'failed');
create type public.psi_run_status as enum ('processing', 'completed', 'failed');
create type public.psi_mismatch_status as enum ('open', 'handled', 'ignored', 'excluded');

create table public.psi_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  login_id text not null unique check (login_id in ('purchase','sale','accounting','tech')),
  team public.psi_team not null,
  display_name text not null,
  created_at timestamptz not null default now()
);
create table public.psi_source_snapshots (
  id uuid primary key default gen_random_uuid(), reporting_week text not null check (reporting_week ~ '^20[0-9]{2}-W(0[1-9]|[1-4][0-9]|5[0-3])$'),
  source_type public.psi_source not null, owner_team public.psi_team not null, version integer not null,
  original_filename text not null, storage_path text not null unique, checksum_sha256 text not null, byte_size bigint not null,
  data_as_of date, schema_status public.psi_schema_status not null, schema_details jsonb not null default '{}'::jsonb,
  uploaded_by uuid not null references auth.users(id), uploaded_at timestamptz not null default now(),
  unique (reporting_week, source_type, version)
);
create index psi_snapshot_latest on public.psi_source_snapshots(reporting_week, source_type, uploaded_at desc);
create view public.psi_latest_source_snapshots with (security_invoker=on) as
 select distinct on (reporting_week, source_type) * from public.psi_source_snapshots where schema_status='passed'
 order by reporting_week, source_type, uploaded_at desc;
create table public.psi_exclusion_rules (
 id uuid primary key default gen_random_uuid(), source_type public.psi_source, match_field text not null,
 operator text not null check (operator in ('equals','in','contains','truthy')), match_value jsonb not null,
 reason text not null, active boolean not null default true, created_from_mismatch_id uuid,
 created_by uuid references auth.users(id), created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table public.psi_runs (
 id uuid primary key default gen_random_uuid(), reporting_week text not null, status public.psi_run_status not null,
 input_hash text not null, source_snapshot_ids uuid[] not null, rule_revision_hash text not null,
 output_path text, output_checksum_sha256 text, summary jsonb not null default '{}'::jsonb, error_message text,
 created_at timestamptz not null default now(), completed_at timestamptz,
 unique(reporting_week,input_hash,rule_revision_hash)
);
create table public.psi_mismatch_cases (
 id uuid primary key default gen_random_uuid(), fingerprint text not null unique, record_key text not null, issue_type text not null,
 source_type text not null, severity text not null check(severity in ('info','warning','blocking')), values_by_source jsonb not null,
 status public.psi_mismatch_status not null default 'open', note text, first_seen_at timestamptz not null default now(), last_seen_at timestamptz not null default now(),
 handled_by uuid references auth.users(id), handled_at timestamptz, exclusion_rule_id uuid references public.psi_exclusion_rules(id)
);
create table public.psi_run_mismatches (run_id uuid references public.psi_runs(id) on delete cascade, mismatch_id uuid references public.psi_mismatch_cases(id) on delete cascade, is_new boolean not null, primary key(run_id,mismatch_id));

alter table public.psi_profiles enable row level security; alter table public.psi_source_snapshots enable row level security;
alter table public.psi_exclusion_rules enable row level security; alter table public.psi_runs enable row level security;
alter table public.psi_mismatch_cases enable row level security; alter table public.psi_run_mismatches enable row level security;
create policy "authenticated read profiles" on public.psi_profiles for select to authenticated using (true);
create policy "authenticated read snapshots" on public.psi_source_snapshots for select to authenticated using (true);
create policy "authenticated read rules" on public.psi_exclusion_rules for select to authenticated using (true);
create policy "authenticated read runs" on public.psi_runs for select to authenticated using (true);
create policy "authenticated read mismatches" on public.psi_mismatch_cases for select to authenticated using (true);
create policy "authenticated read run mismatches" on public.psi_run_mismatches for select to authenticated using (true);
insert into storage.buckets (id,name,public,file_size_limit,allowed_mime_types) values
 ('psi-raw','psi-raw',false,52428800,array['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']),
 ('psi-output','psi-output',false,52428800,array['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']) on conflict (id) do nothing;
