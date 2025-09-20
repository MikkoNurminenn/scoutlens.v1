-- View for quick note counts (idempotent)
create or replace view public.quick_note_counts as
select player_id, count(*)::int as note_count
from public.quick_notes
group by player_id;

-- Helpful index for player-scoped queries
create index if not exists idx_quick_notes_player_created
on public.quick_notes (player_id, created_at desc);
