-- 006_shortlists_refactor.sql
-- Normalize shortlist players into a separate table.

-- Drop old array column if it exists
alter table if exists public.shortlists
  drop column if exists player_ids;

-- Table linking shortlists and players
create table if not exists public.shortlist_items (
  id uuid primary key default gen_random_uuid(),
  shortlist_id uuid references public.shortlists(id) on delete cascade,
  player_id uuid references public.players(id) on delete cascade,
  created_at timestamptz default now(),
  unique(shortlist_id, player_id)
);
