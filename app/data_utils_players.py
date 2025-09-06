# app/data_utils_players_json.py
"""Utility helpers for accessing players stored in the Supabase ``players`` table."""

from __future__ import annotations
from typing import List, Tuple, Dict

import streamlit as st
from supabase_client import get_client


# ---------------------------------------------------------------------------
# Internal normalization
# ---------------------------------------------------------------------------
def _normalize_player_row(p: Dict) -> Dict[str, str]:
    """Return a normalized player dict with keys: id, name, team_name, position."""
    pid = str(p.get("id") or p.get("PlayerID") or "").strip()
    name = (p.get("name") or p.get("Name") or "").strip()
    team = (p.get("team_name") or p.get("Team") or p.get("team") or "").strip()
    pos  = (p.get("position") or p.get("Position") or "").strip()
    return {"id": pid, "name": name, "team_name": team, "position": pos}


# ---------------------------------------------------------------------------
# Cached loading / saving
# ---------------------------------------------------------------------------
@st.cache_data
def load_master() -> List[dict]:
    """Return all players from the ``players`` table.

    Each player is normalized to contain id, name, team_name, position.
    Players with missing name or id are skipped.
    """
    client = get_client()
    if not client:
        return []

    res = client.table("players").select("id,name,team_name,position").execute()
    raw = res.data or []

    players: List[dict] = []
    for p in raw:
        n = _normalize_player_row(p)
        if not n["id"] or not n["name"]:
            continue
        players.append(n)
    return players


def save_master(data: List[dict]) -> None:
    """Persist data to the players table (upsert)."""
    client = get_client()
    if not client or not data:
        return
    client.table("players").upsert(data).execute()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------
def list_teams() -> List[str]:
    """Return sorted list of unique team names found in the players table."""
    return sorted({p["team_name"] for p in load_master() if p.get("team_name")})


def list_players_by_team(team_name: str) -> List[Tuple[str, str]]:
    """Return list of (id, label) for players of team_name."""
    norm = (team_name or "").strip().lower()
    opts: List[Tuple[str, str]] = []
    for p in load_master():
        team = (p.get("team_name") or "").strip().lower()
        if team != norm:
            continue
        name = p.get("name", "").strip()
        pos  = p.get("position", "").strip()
        team_disp = p.get("team_name", "").strip()
        if not name or not p.get("id"):
            continue
        label = f"{name} ({pos}) — {team_disp}" if pos else f"{name} — {team_disp}"
        opts.append((p["id"], label))
    return opts


# ---------------------------------------------------------------------------
# Cache control
# ---------------------------------------------------------------------------
def clear_players_cache() -> None:
    """Invalidate cached load_master results."""
    try:
        load_master.clear()  # type: ignore[attr-defined]
    except Exception:
        pass
