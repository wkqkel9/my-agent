-- Run in the Supabase SQL Editor. Auth identities and passwords are managed by Supabase Auth.
create table if not exists public.permissions (
  user_id uuid not null references auth.users(id) on delete cascade,
  feature text not null check (feature in ('writing', 'copywriting')),
  allowed boolean not null default false,
  primary key (user_id, feature)
);

alter table public.permissions enable row level security;
drop policy if exists "users can read their own permissions" on public.permissions;
create policy "users can read their own permissions"
  on public.permissions for select to authenticated
  using ((select auth.uid()) = user_id);
grant select on public.permissions to authenticated;

create table if not exists public.preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  default_location text not null default '',
  location_kind text not null default '',
  updated_at timestamptz not null default now()
);

alter table public.preferences enable row level security;
drop policy if exists "users manage their own preferences" on public.preferences;
create policy "users manage their own preferences"
  on public.preferences for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
grant select, insert, update on public.preferences to authenticated;

create table if not exists public.access_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  feature text not null check (feature in ('writing', 'copywriting')),
  outcome text not null check (outcome in ('ok', 'denied')),
  created_at timestamptz not null default now()
);

create index if not exists access_runs_user_created_idx
  on public.access_runs (user_id, created_at desc);

alter table public.access_runs enable row level security;
drop policy if exists "users read their own access runs" on public.access_runs;
create policy "users read their own access runs"
  on public.access_runs for select to authenticated
  using ((select auth.uid()) = user_id);
drop policy if exists "users insert their own access runs" on public.access_runs;
create policy "users insert their own access runs"
  on public.access_runs for insert to authenticated
  with check ((select auth.uid()) = user_id);
grant select, insert on public.access_runs to authenticated;

-- Usernames map to internal emails as <username>@<Supabase project host>.
-- Grant access in the SQL Editor after creating the test users through the app:
-- insert into public.permissions (user_id, feature, allowed)
-- select id, feature, true from auth.users cross join (values ('writing'), ('copywriting')) as f(feature)
-- where email = 'account-a@your-project-ref.supabase.co'
-- on conflict (user_id, feature) do update set allowed = excluded.allowed;
