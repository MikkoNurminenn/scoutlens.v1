-- 002_reports_view.sql
-- Legacy view support for scout_reports table.

-- (A) Minimal base table (safe if exists already)
create extension if not exists pgcrypto;

create table if not exists public.scout_reports (
  id uuid primary key default gen_random_uuid(),
  title text,
  player_id uuid,
  player_name text,
  competition text,
  opponent text,
  report_date date,
  location text,
  ratings jsonb,
  tags text[],
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- (C) View with unified columns for the legacy app pieces
create or replace view public.scout_reports_v as
select
  r.id,
  coalesce(r.title, r.report_title) as title,
  r.player_id,
  r.player_name,
  r.competition,
  r.opponent,
  r.report_date,
  r.location,
  r.ratings,
  r.tags,
  r.notes,
  r.created_at,
  r.updated_at
from public.scout_reports r;

-- (D) Grants for anon access (RLS not enforced here)
grant usage on schema public to anon;
grant select on public.scout_reports_v to anon;

-- (E) Reload PostgREST schema cache
notify pgrst, 'reload schema';
