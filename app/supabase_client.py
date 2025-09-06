# supabase_client.py
from __future__ import annotations

"""Utility helpers for interacting with a Supabase backend.

This module exposes a cached client factory ``get_sb`` that reads configuration
from environment variables or, when running inside Streamlit, from
``st.secrets``.  It also provides thin helper functions for common CRUD
operations and convenience wrappers for frequently used tables.
"""

import os
from functools import lru_cache, partial

try:  # optional dependency
    from supabase import Client, create_client
except Exception:  # pragma: no cover - missing supabase
    Client = None  # type: ignore
    create_client = None  # type: ignore

try:  # optional dependency
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover - not running in Streamlit
    st = None  # type: ignore


def _get_env_or_secret(name: str) -> str | None:
    """Fetch ``name`` from ``os.environ`` or Streamlit secrets."""

    value = os.environ.get(name)
    if value:
        return value
    if st is not None:
        return st.secrets.get(name)  # type: ignore[index]
    return None


@lru_cache
def get_sb() -> "Client | None":
    """Return a cached Supabase client if credentials are available."""

    url = _get_env_or_secret("SUPABASE_URL")
    anon_key = _get_env_or_secret("SUPABASE_ANON_KEY")
    service_key = _get_env_or_secret("SUPABASE_SERVICE_ROLE")
    key = service_key or anon_key
    if not url or not key or create_client is None:
        return None
    return create_client(url, key)


def insert_row(table: str, row: dict) -> object | None:
    """Insert ``row`` into ``table`` and return the Supabase response."""

    sb = get_sb()
    if sb is None:
        return None
    return sb.table(table).insert(row).execute()


def select_rows(
    table: str, filters: dict | None = None, columns: str = "*"
) -> object | None:
    """Select rows from ``table`` applying equality ``filters`` if provided."""

    sb = get_sb()
    if sb is None:
        return None
    query = sb.table(table).select(columns)
    if filters:
        for key, value in filters.items():
            query = query.eq(key, value)
    return query.execute()


def update_rows(table: str, updates: dict, filters: dict) -> object | None:
    """Update rows in ``table`` matching ``filters`` with ``updates``."""

    sb = get_sb()
    if sb is None:
        return None
    query = sb.table(table).update(updates)
    for key, value in filters.items():
        query = query.eq(key, value)
    return query.execute()


def delete_rows(table: str, filters: dict) -> object | None:
    """Delete rows from ``table`` matching ``filters``."""

    sb = get_sb()
    if sb is None:
        return None
    query = sb.table(table).delete()
    for key, value in filters.items():
        query = query.eq(key, value)
    return query.execute()


# Convenience wrappers for common tables
insert_player = partial(insert_row, "players")
select_players = partial(select_rows, "players")
update_players = partial(update_rows, "players")
delete_players = partial(delete_rows, "players")

insert_team = partial(insert_row, "teams")
select_teams = partial(select_rows, "teams")
update_teams = partial(update_rows, "teams")
delete_teams = partial(delete_rows, "teams")

insert_match = partial(insert_row, "matches")
select_matches = partial(select_rows, "matches")
update_matches = partial(update_rows, "matches")
delete_matches = partial(delete_rows, "matches")

insert_scout_report = partial(insert_row, "scout_reports")
select_scout_reports = partial(select_rows, "scout_reports")
update_scout_reports = partial(update_rows, "scout_reports")
delete_scout_reports = partial(delete_rows, "scout_reports")

insert_shortlist = partial(insert_row, "shortlists")
select_shortlists = partial(select_rows, "shortlists")
update_shortlists = partial(update_rows, "shortlists")
delete_shortlists = partial(delete_rows, "shortlists")

insert_note = partial(insert_row, "notes")
select_notes = partial(select_rows, "notes")
update_notes = partial(update_rows, "notes")
delete_notes = partial(delete_rows, "notes")

