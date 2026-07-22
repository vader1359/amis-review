create table if not exists public.psi_source_owners (
    login_id text primary key check (length(trim(login_id)) > 0),
    created_at timestamptz not null default now()
);

create table if not exists public.psi_source_ownership (
    source_type text primary key check (source_type in ('product', 'purchase', 'revenue', 'inventory', 'preorder', 'crm', 'target')),
    login_id text not null references public.psi_source_owners (login_id),
    created_at timestamptz not null default now()
);

insert into public.psi_source_owners (login_id)
values ('purchase'), ('sale'), ('accounting'), ('tech')
on conflict (login_id) do nothing;

insert into public.psi_source_ownership (source_type, login_id)
values
    ('purchase', 'purchase'),
    ('preorder', 'purchase'),
    ('crm', 'sale'),
    ('revenue', 'accounting'),
    ('inventory', 'accounting'),
    ('product', 'tech'),
    ('target', 'tech')
on conflict (source_type) do update set login_id = excluded.login_id;

alter table public.psi_source_owners enable row level security;
alter table public.psi_source_ownership enable row level security;

grant select, insert, update, delete on public.psi_source_owners to authenticated;
grant select, insert, update, delete on public.psi_source_ownership to authenticated;

create policy psi_source_owners_admin_manage on public.psi_source_owners
for all to authenticated
using (exists (
    select 1
    from public.team_memberships membership
    where membership.profile_id = (select auth.uid())
      and membership.role = 'admin'
))
with check (exists (
    select 1
    from public.team_memberships membership
    where membership.profile_id = (select auth.uid())
      and membership.role = 'admin'
));

create policy psi_source_ownership_admin_manage on public.psi_source_ownership
for all to authenticated
using (exists (
    select 1
    from public.team_memberships membership
    where membership.profile_id = (select auth.uid())
      and membership.role = 'admin'
))
with check (exists (
    select 1
    from public.team_memberships membership
    where membership.profile_id = (select auth.uid())
      and membership.role = 'admin'
));

create or replace function public.is_psi_source_owner(p_source_type text)
returns boolean
language sql
stable
security definer
set search_path = public, auth
as $$
    select exists (
        select 1
        from public.psi_source_ownership ownership
        join public.psi_source_owners owner on owner.login_id = ownership.login_id
        join auth.users user_account on split_part(lower(user_account.email), '@', 1) = lower(owner.login_id)
        where ownership.source_type = p_source_type
          and user_account.id = (select auth.uid())
    );
$$;

revoke all on function public.is_psi_source_owner(text) from public, anon;
grant execute on function public.is_psi_source_owner(text) to authenticated;

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
          and public.is_psi_source_owner(snapshot.source_type)
          and public.is_team_member(snapshot.team_id, array['contributor', 'reviewer', 'admin'])
    );
$$;

drop policy if exists snapshots_contributor_create on public.source_snapshots;
create policy snapshots_source_owner_create on public.source_snapshots
for insert to authenticated
with check (
    uploaded_by = (select auth.uid())
    and public.is_psi_source_owner(source_type)
    and public.is_team_member(team_id, array['contributor', 'reviewer', 'admin'])
);

drop policy if exists selections_contributor_manage on public.source_selections;
drop policy if exists selections_admin_manage on public.source_selections;
create policy selections_source_owner_manage on public.source_selections
for insert to authenticated
with check (
    selected_by = (select auth.uid())
    and public.is_psi_source_owner(source_type)
    and exists (
        select 1
        from public.source_snapshots snapshot
        where snapshot.id = source_snapshot_id
          and snapshot.reporting_period_id = source_selections.reporting_period_id
          and snapshot.source_type = source_selections.source_type
          and snapshot.uploaded_by = (select auth.uid())
          and public.is_team_member(snapshot.team_id, array['contributor', 'reviewer', 'admin'])
    )
);
