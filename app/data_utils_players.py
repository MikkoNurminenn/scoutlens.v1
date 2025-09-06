"""Utility helpers for accessing players stored in the Supabase ``players`` table."""

from __future__ import annotations

from typing import List, Tuple

import streamlit as st

from supabase_client import get_client


# ---------------------------------------------------------------------------
# Cached loading / saving
# ---------------------------------------------------------------------------
@st.cache_data
def load_master() -> List[dict]:
    """Return all players from the ``players`` table.

    Each player is normalised to a dictionary containing the keys
    ``id``, ``name``, ``team_name`` and ``position``. Players with a
    missing name or id are skipped.
    """

    client = get_client()
    if not client:
        return []
    res = client.table("players").select("id,name,team_name,position").execute()
    raw = res.data or []

    players: List[dict] = []
    for p in raw:
        name = (p.get("name") or "").strip()
        pid = str(p.get("id") or "").strip()
        if not name or not pid:
            continue
        team = (p.get("team_name") or "").strip()
        pos = (p.get("position") or "").strip()
        players.append({"id": pid, "name": name, "team_name": team, "position": pos})
    return players


def save_master(data: List[dict]) -> None:
    """Persist ``data`` to the ``players`` table."""

    client = get_client()
    if client:
        client.table("players").upsert(data).execute()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------
def list_teams() -> List[str]:
    """Return sorted list of unique team names found in the players table."""

    return sorted({p["team_name"] for p in load_master() if p["team_name"]})


def list_players_by_team(team_name: str) -> List[Tuple[str, str]]:
    """Return ``[(id, label), ...]`` for players of ``team_name``."""

    norm = (team_name or "").strip().lower()
    opts: List[Tuple[str, str]] = []
    for p in load_master():
        team = p["team_name"].strip().lower()
        if team != norm:
            continue
        label = (
            f"{p['name']} ({p['position']}) — {p['team_name']}"
            if p["position"]
            else f"{p['name']} — {p['team_name']}"
        )
        opts.append((p["id"], label))
    return opts


def clear_players_cache() -> None:
    """Invalidate cached ``load_master`` results."""

    load_master.clear()  # type: ignore[attr-defined]


def clear_players_cache():
    """No-op shim. Exists so imports don't explode even if caching isn't used."""
    return None
