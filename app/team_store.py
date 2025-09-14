# file: app/teams_store.py
"""Minimal team store shim for Streamlit app.

Provides `add_team` and `list_teams` to satisfy imports from `app.player_editor`.
Data is persisted to `app/data/teams.json` as a simple JSON array.
This is a safe fallback when a dedicated backend module is missing/renamed.

If you later wire a real DB (e.g., Supabase), replace the internals while
keeping the same public functions.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import threading
import time
import uuid

# --- paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "app" / "data"
TEAMS_FILE = DATA_DIR / "teams.json"
_LOCK = threading.Lock()


# --- helpers

def _read() -> List[Dict[str, Any]]:
    if not TEAMS_FILE.exists():
        return []
    try:
        return json.loads(TEAMS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # why: keep app running even if file is corrupted; start fresh
        return []


def _write(items: List[Dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEAMS_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# --- public API (keep names/signatures as imported elsewhere)

def list_teams() -> List[Dict[str, Any]]:
    """Return all teams as a list of dicts.

    Format: {"id": str, "name": str, ...}
    """
    with _LOCK:
        return _read()


def add_team(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Add or upsert a team.

    Accepts either a single dict positional argument or keyword fields.
    Ensures a stable "id" (uuid4) and unique name constraint.
    Returns the stored team dict.
    """
    # Accept {..} or fields
    if len(args) == 1 and isinstance(args[0], dict):
        team: Dict[str, Any] = dict(args[0])
    else:
        team = dict(kwargs)

    name: Optional[str] = team.get("name")
    if not name or not isinstance(name, str):
        raise ValueError("add_team requires a 'name' string field")

    team.setdefault("id", str(uuid.uuid4()))
    team.setdefault("created_at", int(time.time()))

    with _LOCK:
        items = _read()
        # unique by name (case-insensitive)
        lower = name.strip().casefold()
        existing_idx = next(
            (i for i, t in enumerate(items) if str(t.get("name", "")).strip().casefold() == lower),
            None,
        )
        if existing_idx is None:
            items.append(team)
        else:
            # merge (upsert) preserving original id
            existing = dict(items[existing_idx])
            team["id"] = existing.get("id", team["id"])  # preserve
            existing.update(team)
            items[existing_idx] = existing
            team = items[existing_idx]
        _write(items)
        return team


__all__ = ["add_team", "list_teams"]
