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
  external_id text unique,
  team_id uuid references public.teams(id) on delete set null,
  team_name text,
  name text not null,
  nationality text,
  date_of_birth date,
  preferred_foot text,
  club_number int,
  position text,
  scout_rating numeric,
  transfermarkt_url text,
  notes text,
  updated_at timestamptz default now()
);

create table if not exists public.matches (
  id uuid primary key default gen_random_uuid(),
  home_team text not null,
  away_team text not null,
  competition text,
  location text,
  kickoff_at timestamptz not null,
  targets text[],
  created_at timestamptz default now()
);

create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  match_id uuid references public.matches(id) on delete cascade,
  player_id uuid references public.players(id) on delete set null,
  player_name text,
  team_name text,
  rating numeric,
  summary text,
  tags text[],
  created_at timestamptz default now()
);

create table if not exists public.shortlists (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  player_ids uuid[] default '{}',
  created_at timestamptz default now()
);
