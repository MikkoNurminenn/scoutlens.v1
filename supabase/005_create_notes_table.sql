-- 005_create_notes_table.sql
-- Create notes table for player notes

create table if not exists public.notes (
  id uuid primary key default gen_random_uuid(),
  player_id uuid references public.players(id) on delete cascade,
  text text not null,
  created_at timestamptz default now(),
  tags text[]
);
