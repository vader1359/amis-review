create extension if not exists pgcrypto;

create table if not exists public.teams (
    id uuid primary key default gen_random_uuid(),
    name text not null check (length(trim(name)) > 0),
    slug text not null unique check (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    created_at timestamptz not null default now()
);

create table if not exists public.profiles (
    id uuid primary key references auth.users (id),
    display_name text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.team_memberships (
    id uuid primary key default gen_random_uuid(),
    team_id uuid not null references public.teams (id),
    profile_id uuid not null references public.profiles (id),
    role text not null check (role in ('viewer', 'contributor', 'reviewer', 'admin')),
    created_at timestamptz not null default now(),
    unique (team_id, profile_id)
);

create table if not exists public.reporting_periods (
    id uuid primary key default gen_random_uuid(),
    period_key text not null unique check (period_key ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
    label text,
    starts_on date not null,
    ends_on date not null,
    created_at timestamptz not null default now(),
    check (ends_on >= starts_on)
);

create table if not exists public.upload_batches (
    id uuid primary key default gen_random_uuid(),
    team_id uuid not null references public.teams (id),
    reporting_period_id uuid not null references public.reporting_periods (id),
    uploaded_by uuid not null references public.profiles (id),
    created_at timestamptz not null default now(),
    notes text
);

create table if not exists public.source_snapshots (
    id uuid primary key default gen_random_uuid(),
    upload_batch_id uuid not null references public.upload_batches (id),
    team_id uuid not null references public.teams (id),
    reporting_period_id uuid not null references public.reporting_periods (id),
    source_type text not null check (length(trim(source_type)) > 0),
    version integer not null check (version > 0),
    original_filename text not null,
    object_path text not null unique,
    checksum_sha256 text not null check (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint not null check (byte_size >= 0),
    data_as_of date not null,
    schema_status text not null default 'pending' check (schema_status in ('pending', 'passed', 'failed')),
    row_count bigint check (row_count >= 0),
    uploaded_by uuid not null references public.profiles (id),
    uploaded_at timestamptz not null default now(),
    unique (team_id, reporting_period_id, source_type, version)
);

create table if not exists public.source_selections (
    id uuid primary key default gen_random_uuid(),
    reporting_period_id uuid not null references public.reporting_periods (id),
    source_type text not null,
    source_snapshot_id uuid not null references public.source_snapshots (id),
    selected_by uuid not null references public.profiles (id),
    selected_at timestamptz not null default now(),
    unique (reporting_period_id, source_type)
);

create table if not exists public.reconciliation_runs (
    id uuid primary key default gen_random_uuid(),
    reporting_period_id uuid not null references public.reporting_periods (id),
    started_by uuid not null references public.profiles (id),
    rule_version_id uuid,
    status text not null default 'queued' check (status in ('queued', 'running', 'completed', 'failed')),
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    error_message text,
    check (completed_at is null or completed_at >= started_at)
);

create table if not exists public.reconciliation_run_sources (
    reconciliation_run_id uuid not null references public.reconciliation_runs (id),
    source_snapshot_id uuid not null references public.source_snapshots (id),
    source_type text not null,
    primary key (reconciliation_run_id, source_type),
    unique (reconciliation_run_id, source_snapshot_id)
);

create table if not exists public.normalized_records (
    id uuid primary key default gen_random_uuid(),
    reconciliation_run_id uuid not null references public.reconciliation_runs (id),
    source_snapshot_id uuid not null references public.source_snapshots (id),
    source_type text not null,
    record_key text not null,
    normalized_values jsonb not null,
    source_row_number integer check (source_row_number > 0),
    created_at timestamptz not null default now(),
    unique (reconciliation_run_id, source_type, record_key)
);

create table if not exists public.rules (
    id uuid primary key default gen_random_uuid(),
    rule_key text not null unique check (rule_key ~ '^[a-z0-9_]+$'),
    name text not null,
    description text,
    created_at timestamptz not null default now()
);

create table if not exists public.rule_versions (
    id uuid primary key default gen_random_uuid(),
    rule_id uuid not null references public.rules (id),
    version integer not null check (version > 0),
    definition jsonb not null,
    checksum_sha256 text not null check (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    created_by uuid not null references public.profiles (id),
    created_at timestamptz not null default now(),
    unique (rule_id, version),
    unique (id, rule_id)
);

alter table public.reconciliation_runs
    add constraint reconciliation_runs_rule_version_fk
    foreign key (rule_version_id) references public.rule_versions (id);

create table if not exists public.known_issues (
    id uuid primary key default gen_random_uuid(),
    fingerprint text not null unique,
    title text not null,
    reason text not null,
    status text not null default 'known' check (status in ('known', 'approved', 'retired')),
    created_by uuid not null references public.profiles (id),
    created_at timestamptz not null default now(),
    retired_at timestamptz
);

create table if not exists public.mismatches (
    id uuid primary key default gen_random_uuid(),
    reconciliation_run_id uuid not null references public.reconciliation_runs (id),
    reporting_period_id uuid not null references public.reporting_periods (id),
    rule_version_id uuid not null references public.rule_versions (id),
    source_type text not null,
    record_key text not null,
    fingerprint text not null,
    severity text not null check (severity in ('blocking', 'warning', 'informational')),
    status text not null default 'new' check (status in ('new', 'assigned', 'in_progress', 'resolved', 'known', 'ignored', 'reopened')),
    values_by_source jsonb not null,
    assigned_to uuid references public.profiles (id),
    known_issue_id uuid references public.known_issues (id),
    created_at timestamptz not null default now(),
    resolved_at timestamptz,
    unique (reconciliation_run_id, fingerprint)
);

create table if not exists public.mismatch_history (
    id uuid primary key default gen_random_uuid(),
    mismatch_id uuid not null references public.mismatches (id),
    changed_by uuid not null references public.profiles (id),
    from_status text,
    to_status text not null check (to_status in ('new', 'assigned', 'in_progress', 'resolved', 'known', 'ignored', 'reopened')),
    comment text,
    evidence jsonb,
    changed_at timestamptz not null default now()
);

create table if not exists public.psi_drafts (
    id uuid primary key default gen_random_uuid(),
    reporting_period_id uuid not null references public.reporting_periods (id),
    reconciliation_run_id uuid not null references public.reconciliation_runs (id),
    rule_version_id uuid not null references public.rule_versions (id),
    status text not null default 'pending_review' check (status in ('pending_review', 'approved', 'rejected', 'superseded')),
    object_path text,
    checksum_sha256 text check (checksum_sha256 is null or checksum_sha256 ~ '^[0-9a-f]{64}$'),
    created_by uuid not null references public.profiles (id),
    created_at timestamptz not null default now(),
    approved_by uuid references public.profiles (id),
    approved_at timestamptz
);

create table if not exists public.draft_sources (
    draft_id uuid not null references public.psi_drafts (id),
    source_snapshot_id uuid not null references public.source_snapshots (id),
    source_type text not null,
    primary key (draft_id, source_type),
    unique (draft_id, source_snapshot_id)
);

create table if not exists public.psi_releases (
    id uuid primary key default gen_random_uuid(),
    psi_draft_id uuid not null references public.psi_drafts (id),
    reporting_period_id uuid not null references public.reporting_periods (id),
    rule_version_id uuid not null references public.rule_versions (id),
    object_path text not null unique,
    checksum_sha256 text not null check (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    row_count bigint not null check (row_count >= 0),
    kpis jsonb not null default '{}'::jsonb,
    approved_by uuid not null references public.profiles (id),
    published_by uuid not null references public.profiles (id),
    published_at timestamptz not null default now()
);

create table if not exists public.release_sources (
    release_id uuid not null references public.psi_releases (id),
    source_snapshot_id uuid not null references public.source_snapshots (id),
    source_type text not null,
    primary key (release_id, source_type),
    unique (release_id, source_snapshot_id)
);

create table if not exists public.activity_logs (
    id uuid primary key default gen_random_uuid(),
    team_id uuid references public.teams (id),
    actor_id uuid references public.profiles (id),
    action text not null check (length(trim(action)) > 0),
    entity_type text not null,
    entity_id uuid,
    metadata jsonb not null default '{}'::jsonb,
    occurred_at timestamptz not null default now()
);
