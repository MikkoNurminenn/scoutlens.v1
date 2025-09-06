-- 001_create_tables.sql
-- Schema definitions for ScoutLens Supabase tables.
-- Ensure each table includes all fields required by the UI and a created_at timestamp.

create extension if not exists "uuid-ossp";

create table if not exists players (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    team_name text not null,
    date_of_birth date,
    nationality text,
    height integer,
    weight integer,
    preferred_foot text,
    club_number integer,
    primary_position text,
    secondary_positions text[],
    notes text,
    tags text[],
    photo_path text,
    created_at timestamptz not null default now()
);

create table if not exists teams (
    id uuid primary key default uuid_generate_v4(),
    name text unique not null,
    created_at timestamptz not null default now()
);

create table if not exists matches (
    id uuid primary key default uuid_generate_v4(),
    date date,
    time text,
    tz text,
    home text,
    away text,
    competition text,
    location text,
    city text,
    targets text[],
    notes text,
    created_at timestamptz not null default now()
);

create table if not exists scout_reports (
    id uuid primary key default uuid_generate_v4(),
    match_id uuid references matches(id) on delete cascade,
    player_id uuid references players(id) on delete cascade,
    competition text,
    foot text,
    position text,
    ratings jsonb,
    general_comment text,
    created_at timestamptz not null default now()
);

create table if not exists shortlists (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    items jsonb,
    created_at timestamptz not null default now()
);

create table if not exists notes (
    id uuid primary key default uuid_generate_v4(),
    text text not null,
    tags text[],
    created_at timestamptz not null default now()
);
