-- 010_calendar_targets.sql
-- Extend matches metadata and introduce match_targets join table for calendar sync.

alter table if exists public.matches
  add column if not exists venue text,
  add column if not exists country text,
  add column if not exists tz_name text,
  add column if not exists ends_at_utc timestamptz,
  add column if not exists notes text;

create table if not exists public.match_targets (
  id uuid primary key default gen_random_uuid(),
  match_id uuid references public.matches(id) on delete cascade,
  player_id uuid references public.players(id) on delete cascade,
  created_at timestamptz default now(),
  unique(match_id, player_id)
);

create index if not exists idx_match_targets_match on public.match_targets(match_id);
create index if not exists idx_match_targets_player on public.match_targets(player_id);
