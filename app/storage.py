# app/storage.py — self-contained adapter (no app.* imports)
from __future__ import annotations
from pathlib import Path
import json, os, platform
from typing import Any

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

def load_json(name_or_fp: str | Path, default: Any | None = None):
    """Read JSON data or return *default* (``[]`` if not provided).

    This helper ensures a missing or malformed file never raises and
    instead falls back to an empty list (or the provided ``default``).
    """
    p = file_path(name_or_fp) if isinstance(name_or_fp, str) else Path(name_or_fp)
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return [] if default is None else default

def save_json(name_or_fp: str | Path, data):
    p = file_path(name_or_fp) if isinstance(name_or_fp, str) else Path(name_or_fp)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

IS_CLOUD = (platform.system() not in ("Windows", "Darwin"))

# Valinnainen luokkakääre jos joku moduuli vielä käyttää Storage-oliota
class Storage:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def file_path(self, name: str) -> Path:
        return self.base_dir / name

    def read_json(self, fp: Path, default: Any | None = None):
        try:
            if fp.exists():
                return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
        return [] if default is None else default

    def write_json(self, fp: Path, data):
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # -----------------------------------------------------
    # Player helpers
    # -----------------------------------------------------
    def _players_fp(self) -> Path:
        """Return path to the JSON file storing players."""
        return self.file_path("players.json")

    def _load_players(self) -> list[dict]:
        return self.read_json(self._players_fp(), [])

    def _save_players(self, players: list[dict]):
        self.write_json(self._players_fp(), players)

    def list_players(self) -> list[dict]:
        """Return all players stored on disk."""
        return self._load_players()

    def upsert_player(self, player: dict) -> str:
        """Insert or update a player record.

        If the supplied ``player`` dictionary does not include an ``id`` field,
        a UUID4 string is generated. Existing players are matched by ``id`` and
        replaced while keeping any unspecified fields intact. Returns the
        player's id.
        """
        players = self._load_players()
        pid = str(player.get("id") or "").strip()
        if not pid:
            from uuid import uuid4

            pid = uuid4().hex
            player["id"] = pid

        replaced = False
        for idx, existing in enumerate(players):
            if str(existing.get("id")) == pid:
                players[idx] = {**existing, **player}
                replaced = True
                break
        if not replaced:
            players.append(player)

        self._save_players(players)
        return pid

    def remove_by_ids(self, ids: list[str]) -> int:
        """Remove players whose id is in ``ids``. Returns number of removed."""
        ids_set = {str(i) for i in ids}
        players = self._load_players()
        new_players = [p for p in players if str(p.get("id")) not in ids_set]
        removed = len(players) - len(new_players)
        if removed:
            self._save_players(new_players)
        return removed

    def _update_field(self, player_id: str, field: str, value) -> bool:
        players = self._load_players()
        updated = False
        for p in players:
            if str(p.get("id")) == str(player_id):
                p[field] = value
                updated = True
                break
        if updated:
            self._save_players(players)
        return updated

    def set_photo_path(self, player_id: str, path: str) -> bool:
        """Persist photo path for the given player."""
        return self._update_field(player_id, "photo_path", path)

    def set_tags(self, player_id: str, tags: list[str]) -> bool:
        """Persist list of tags for the given player."""
        return self._update_field(player_id, "tags", tags)
