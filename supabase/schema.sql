-- Run this in the Supabase SQL Editor.
-- Auth identifies the learner; RLS keeps every learner's progress private.
-- This service has no A/B feature gate. Never expose a service-role key.

create table if not exists public.learner_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  cefr_level text not null default 'B1',
  success_streak integer not null default 0,
  struggle_streak integer not null default 0,
  updated_at timestamptz not null default now()
);

create table if not exists public.drill_history (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  user_id uuid not null references auth.users(id) on delete cascade,
  category text not null default '',
  korean text not null default '',
  user_text text not null default '',
  is_correct boolean not null default false,
  time_spent integer not null default 0,
  favorite boolean not null default false,
  expression_id text,
  training_mode text,
  question_type text
);
create index if not exists drill_history_user_created_idx on public.drill_history (user_id, created_at desc);

create table if not exists public.expression_progress (
  user_id uuid not null references auth.users(id) on delete cascade,
  expression_id text not null,
  stage text not null default 'new',
  correct_count integer not null default 0,
  partial_count integer not null default 0,
  incorrect_count integer not null default 0,
  next_due_sequence integer,
  next_due_at timestamptz,
  last_seen_sequence integer,
  updated_at timestamptz not null default now(),
  primary key (user_id, expression_id)
);

alter table public.learner_profiles enable row level security;
alter table public.drill_history enable row level security;
alter table public.expression_progress enable row level security;

drop policy if exists "learner owns profile" on public.learner_profiles;
create policy "learner owns profile" on public.learner_profiles for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
drop policy if exists "learner owns drill history" on public.drill_history;
create policy "learner owns drill history" on public.drill_history for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
drop policy if exists "learner owns expression progress" on public.expression_progress;
create policy "learner owns expression progress" on public.expression_progress for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

grant select, insert, update, delete on public.learner_profiles to authenticated;
grant select, insert, update, delete on public.drill_history to authenticated;
grant select, insert, update, delete on public.expression_progress to authenticated;
grant usage, select on sequence public.drill_history_id_seq to authenticated;
