"""Utility helpers for accessing players stored in ``players.json``.

This module acts as the single source of truth for player data used by
both the Player Editor and the Scout Match Reporter. Reading the master
player list is cached via ``st.cache_data`` so that Streamlit apps don't
need to restart to pick up new players. Whenever the list is modified,
``clear_players_cache`` should be called to invalidate the cache.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import streamlit as st

from storage import load_json, save_json, file_path

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------
PLAYERS_FP: Path = file_path("players.json")


# ---------------------------------------------------------------------------
# Cached loading / saving
# ---------------------------------------------------------------------------
@st.cache_data
def load_master() -> List[dict]:
    """Return all players from ``players.json``.

    Each player is normalised to a dictionary containing at least the
    keys ``id`` (string), ``name`` (string), ``team_name`` (string) and
    ``position`` (string). Players missing a name are filtered out so they
    won't appear in any dropdowns.
    """

    raw = load_json(PLAYERS_FP, [])
    if not isinstance(raw, list):
        raw = []
    players: List[dict] = []
    for p in raw:
        name = (p.get("name") or p.get("Name") or "").strip()
        if not name:
            continue
        team = (
            p.get("team_name")
            or p.get("Team")
            or p.get("team")
            or ""
        ).strip()
        pos = (p.get("position") or p.get("Position") or "").strip()
        pid = str(p.get("id") or p.get("PlayerID") or "").strip()
        if not pid:
            continue
        players.append(
            {
                "id": pid,
                "name": name,
                "team_name": team,
                "position": pos,
            }
        )
    return players


def save_master(data: List[dict]) -> None:
    """Persist ``data`` to ``players.json``."""

    save_json(PLAYERS_FP, data)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------
def list_teams() -> List[str]:
    """Return sorted list of unique team names found in ``players.json``."""

    return sorted({p["team_name"] for p in load_master() if p["team_name"]})


def list_players_by_team(team_name: str) -> List[Tuple[str, str]]:
    """Return ``[(id, label), ...]`` for players of ``team_name``.

    ``label`` is formatted as ``"Name (Position) — Team"``. Players with a
    missing name are skipped.
    """

    norm = (team_name or "").strip().lower()
    opts: List[Tuple[str, str]] = []
    for p in load_master():
        team = p["team_name"].strip().lower()
        if team != norm:
            continue
        label = f"{p['name']} ({p['position']}) — {p['team_name']}" if p[
            "position"
        ] else f"{p['name']} — {p['team_name']}"
        opts.append((p["id"], label))
    return opts


def clear_players_cache() -> None:
    """Invalidate cached ``load_master`` results."""

    load_master.clear()  # type: ignore[attr-defined]

