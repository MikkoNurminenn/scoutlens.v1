"""teams_store.py — Supabase-backed team helpers."""

from __future__ import annotations

from typing import List, Tuple

from supabase_client import get_client


def _norm(s: str) -> str:
    return (s or "").strip()


def add_team(name: str) -> tuple[bool, str]:
    """Insert a team into the ``teams`` table.

    Returns ``(ok, info)`` where ``info`` is an error message when ``ok`` is
    ``False`` or the team name when the insert succeeds.
    """

    name = _norm(name)
    if not name:
        return False, "Team name is empty."

    client = get_client()
    if not client:
        return False, "Supabase client not available."

    existing = client.table("teams").select("name").execute().data or []
    if any((t.get("name", "").lower() == name.lower()) for t in existing):
        return False, "Team already exists."

    client.table("teams").insert({"name": name}).execute()
    return True, name


def list_teams() -> List[str]:
    """Return a sorted list of team names from the ``teams`` table."""

    client = get_client()
    if not client:
        return []
    res = client.table("teams").select("name").execute()
    return sorted(t["name"] for t in (res.data or []) if t.get("name"))


# Backwards compatibility alias
list_teams_all = list_teams

