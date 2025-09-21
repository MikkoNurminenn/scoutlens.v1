# app/storage.py — Supabase-backed storage helpers with local export paths
from __future__ import annotations
from pathlib import Path
import os
import platform
from typing import Any, Dict, Iterable, List, Optional

try:  # pragma: no cover - optional dependency for UI feedback
    import streamlit as st
except Exception:  # pragma: no cover
    st = None  # type: ignore

from postgrest.exceptions import APIError

from app.supabase_client import get_client

# --- Base dir: Windows -> %APPDATA%\ScoutLens, muut -> repo/.data
def _default_base_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "ScoutLens"
    # Linux/mac/Cloud: repojuuren alle .data (tämä tiedosto: .../app/storage.py)
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / ".data"

BASE_DIR = _default_base_dir()
BASE_DIR.mkdir(parents=True, exist_ok=True)


def file_path(name: str) -> Path:
    p = BASE_DIR / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


_TABLE_MAP = {
    "players.json": "players",
    "teams.json": "teams",
    "matches.json": "matches",
    "scout_reports.json": "reports",
    "notes.json": "notes",
}


def _notify_error(msg: str) -> None:
    if st is not None:
        st.error(msg)
    else:
        print(msg)


def _resolve_table(name_or_fp: str | Path) -> Optional[str]:
    name = name_or_fp if isinstance(name_or_fp, str) else name_or_fp.name
    return _TABLE_MAP.get(Path(name).name)


def load_json(name_or_fp: str | Path, default):
    table = _resolve_table(name_or_fp)
    if not table:
        return default
    client = get_client()
    if not client:
        return default
    try:
        res = client.table(table).select("*").execute()
    except APIError as err:  # pragma: no cover - UI feedback
        _notify_error(f"Failed to load {table}: {getattr(err, 'message', str(err))}")
        return default
    data = res.data or []
    if isinstance(default, list):
        return data
    if isinstance(default, dict) and data:
        # Reduce to first row when dict requested
        return dict(data[0])
    return data or default


def save_json(name_or_fp: str | Path, data):
    table = _resolve_table(name_or_fp)
    if not table or data is None:
        return
    client = get_client()
    if not client:
        return
    rows: List[Dict[str, Any]]
    if isinstance(data, dict):
        rows = [data]
    elif isinstance(data, Iterable):
        rows = [r for r in data if isinstance(r, dict)]
    else:
        rows = []
    if not rows:
        return
    try:
        try:
            client.table(table).upsert(rows).execute()
        except TypeError:
            client.table(table).upsert(rows, on_conflict="id").execute()
    except APIError as err:  # pragma: no cover - surface error but keep running
        _notify_error(f"Failed to save {table}: {getattr(err, 'message', str(err))}")

IS_CLOUD = (platform.system() not in ("Windows", "Darwin"))

# Valinnainen luokkakääre jos joku moduuli vielä käyttää Storage-oliota
class Storage:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def file_path(self, name: str) -> Path:
        return self.base_dir / name

    # -----------------------------------------------------
    # Player helpers
    # -----------------------------------------------------
    def list_players(self) -> list[dict]:
        """Return all players stored in Supabase."""
        return load_json("players.json", [])

    def upsert_player(self, player: dict) -> str:
        """Insert or update a player record.

        If the supplied ``player`` dictionary does not include an ``id`` field,
        a UUID4 string is generated. Existing players are matched by ``id`` and
        replaced while keeping any unspecified fields intact. Returns the
        player's id.
        """
        from uuid import uuid4

        pid = str(player.get("id") or "").strip()
        if not pid:
            pid = uuid4().hex
            player["id"] = pid

        client = get_client()
        if not client:
            raise RuntimeError("Supabase client is not configured")

        try:
            try:
                client.table("players").upsert(player, on_conflict="id").execute()
            except TypeError:
                client.table("players").upsert(player).execute()
        except APIError as err:
            _notify_error(f"Failed to upsert player: {getattr(err, 'message', str(err))}")
            raise

        if st is not None:
            st.cache_data.clear()
        return pid

    def remove_by_ids(self, ids: list[str]) -> int:
        """Remove players whose id is in ``ids``. Returns number of removed."""
        ids_clean = [str(i) for i in ids if i]
        if not ids_clean:
            return 0
        client = get_client()
        if not client:
            return 0
        # Fetch count before deletion for accurate return value
        existing = load_json("players.json", [])
        existing_ids = {str(p.get("id")) for p in existing}
        to_remove = [pid for pid in ids_clean if pid in existing_ids]
        if not to_remove:
            return 0
        try:
            client.table("players").delete().in_("id", to_remove).execute()
        except APIError as err:
            _notify_error(f"Failed to delete players: {getattr(err, 'message', str(err))}")
            return 0
        if st is not None:
            st.cache_data.clear()
        return len(to_remove)

    def _update_field(self, player_id: str, field: str, value) -> bool:
        client = get_client()
        if not client:
            return False
        try:
            client.table("players").update({field: value}).eq("id", player_id).execute()
        except APIError as err:
            _notify_error(f"Failed to update player: {getattr(err, 'message', str(err))}")
            return False
        if st is not None:
            st.cache_data.clear()
        return True

    def set_photo_path(self, player_id: str, path: str) -> bool:
        """Persist photo path for the given player."""
        return self._update_field(player_id, "photo_path", path)

    def set_tags(self, player_id: str, tags: list[str]) -> bool:
        """Persist list of tags for the given player."""
        return self._update_field(player_id, "tags", tags)
