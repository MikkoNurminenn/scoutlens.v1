-- 001_create_tables.sql
-- Schema definitions for ScoutLens Supabase tables.

create extension if not exists "pgcrypto";

create table if not exists public.teams (
  id uuid primary key default gen_random_uuid(),
  name text unique not null,
  country text,
  created_at timestamptz default now()
);

create table if not exists public.players (
  id uuid primary key default gen_random_uuid(),
  team_id uuid references public.teams(id) on delete set null,
  team_name text,
  name text not null,
  nationality text,
  date_of_birth date,
  preferred_foot text check (
    preferred_foot in ('Left', 'Right', 'Both') or preferred_foot is null
  ),
  club_number int,
  position text,
  primary_position text,
  secondary_positions text[],
  current_club text,
  scout_rating numeric,
  height int,
  weight int,
  transfermarkt_url text,
  external_id text unique,
  notes text,
  tags text[],
  photo_path text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.matches (
  id uuid primary key default gen_random_uuid(),
  home_team text not null,
  away_team text not null,
  competition text,
  country text,
  location text,
  venue text,
  tz_name text,
  kickoff_at timestamptz not null,
  ends_at_utc timestamptz,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.scout_reports (
  id uuid primary key default gen_random_uuid(),
  match_id uuid references public.matches(id) on delete cascade,
  player_id uuid references public.players(id) on delete set null,
  player_name text,
  team_name text,
  rating numeric,
  summary text,
  tags text[],
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  match_id uuid references public.matches(id) on delete set null,
  player_id uuid references public.players(id) on delete cascade,
  player_name text,
  report_date date not null default (now() at time zone 'utc')::date,
  competition text,
  opponent text,
  location text,
  position_played text,
  minutes int,
  rating numeric(3,1),
  notes text,
  scout_name text,
  attributes jsonb not null default '{}'::jsonb,
  tags text[],
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.shortlists (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.quick_notes (
  id uuid primary key default gen_random_uuid(),
  player_id uuid references public.players(id) on delete cascade,
  content text not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.notes (
  id uuid primary key default gen_random_uuid(),
  player_id uuid references public.players(id) on delete cascade,
  text text not null,
  tags text[],
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
