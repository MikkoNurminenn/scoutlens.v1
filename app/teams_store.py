"""teams_store.py — Supabase-backed team helpers."""

from __future__ import annotations

from typing import List, Tuple

from supabase_client import get_client


def list_teams() -> List[str]:
    """Return team names ordered alphabetically."""

    client = get_client()
    if not client:
        return []
    r = client.table("teams").select("name").order("name").execute()
    return [row["name"] for row in (r.data or []) if row.get("name")]


def add_team(name: str) -> tuple[bool, str]:
    nm = (name or "").strip()
    client = get_client()
    if not nm:
        return False, "Team name is empty."
    existing = client.table("teams").select("name").execute().data or []
    if any((t.get("name", "").lower() == nm.lower()) for t in existing):
        return False, "Team already exists."
    try:
        client.table("teams").upsert({"name": nm}).execute()
        return True, nm
    except Exception as e:
        return False, str(e)


# Backwards compatibility alias
list_teams_all = list_teams

