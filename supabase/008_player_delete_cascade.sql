-- 008_player_delete_cascade.sql
-- Ensure child rows are removed when a player is deleted

-- reports.player_id → players.id
alter table if exists public.reports
  drop constraint if exists reports_player_id_fkey;
alter table if exists public.reports
  add constraint reports_player_id_fkey
  foreign key (player_id) references public.players(id) on delete cascade;

-- shortlist_items.player_id → players.id
alter table if exists public.shortlist_items
  drop constraint if exists shortlist_items_player_id_fkey;
alter table if exists public.shortlist_items
  add constraint shortlist_items_player_id_fkey
  foreign key (player_id) references public.players(id) on delete cascade;
