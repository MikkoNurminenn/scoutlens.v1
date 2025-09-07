-- 002_reports_view.sql
-- Normalize reports via a stable VIEW and ensure kickoff_at is available.

-- (A) Minimal base table (safe if exists already)
create extension if not exists pgcrypto;

create table if not exists public.scout_reports (
  id uuid primary key default gen_random_uuid(),
  title text,
  player_id uuid,
  player_name text,
  competition text,
  opponent text,
  match_datetime timestamptz,
  location text,
  ratings jsonb,
  tags text[],
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- (B) Optional physical column for kickoff time
alter table public.scout_reports
  add column if not exists kickoff_at timestamptz;

-- (C) View with unified columns for the app
create or replace view public.reports as
select
  r.id,
  coalesce(r.title, r.report_title)         as title,
  r.player_id,
  r.player_name,
  r.competition,
  r.opponent,
  coalesce(r.kickoff_at, r.match_datetime)  as kickoff_at,
  r.location,
  r.ratings,
  r.tags,
  r.notes,
  r.created_at,
  r.updated_at
from public.scout_reports r;

-- (D) Grants for anon access (RLS not enforced here)
grant usage on schema public to anon;
grant select on public.reports to anon;

-- (E) Reload PostgREST schema cache
notify pgrst, 'reload schema';
