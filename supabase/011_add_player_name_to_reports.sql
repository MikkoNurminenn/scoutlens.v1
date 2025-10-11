-- 011_add_player_name_to_reports.sql
-- Ensure reports table exposes player_name for UI fallbacks.

alter table if exists public.reports
  add column if not exists player_name text;

notify pgrst, 'reload schema';
