create or replace function public.reports_count_by_player()
returns table(player_id uuid, reports_count bigint)
language sql stable as $$
  select player_id, count(*) as reports_count
  from public.reports
  group by 1;
$$;

create index if not exists idx_reports_player on public.reports(player_id);
create index if not exists idx_reports_date on public.reports(report_date);
create index if not exists idx_shortlist_items on public.shortlist_items(shortlist_id, player_id);
create index if not exists idx_players_name on public.players(name);
create index if not exists idx_players_club on public.players(current_club);
