# teams_store.py
from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Tuple, List

from app_paths import file_path, DATA_DIR

# Yritä käyttää projektin Storagea; jos ei löydy, käytetään fallbackia
try:
    from storage import load_json as _storage_load_json, save_json as _storage_save_json  # type: ignore
    _HAS_STORAGE = True
except Exception:
    _storage_load_json = None
    _storage_save_json = None
    _HAS_STORAGE = False

TEAMS_FP: Path = file_path("teams.json")
TEAMS_DIR: Path = DATA_DIR / "teams"


# ---------------- JSON apurit ----------------
def _load_json_fallback(fp: Path, default: Any):
    try:
        if fp.exists():
            return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json_fallback(fp: Path, data: Any) -> None:
    fp.parent.mkdir(parents=True, exist_ok=True)
    try:
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # viimeinen yritys ilman indentiä
        fp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _load(fp: Path, default: Any):
    if _HAS_STORAGE and _storage_load_json is not None:
        try:
            return _storage_load_json(fp, default)
        except Exception:
            return _load_json_fallback(fp, default)
    return _load_json_fallback(fp, default)


def _save(fp: Path, data: Any) -> None:
    if _HAS_STORAGE and _storage_save_json is not None:
        try:
            _storage_save_json(fp, data)
            return
        except Exception:
            _save_json_fallback(fp, data)
            return
    _save_json_fallback(fp, data)


# ---------------- Utilit ----------------
def _norm(s: str) -> str:
    return (s or "").strip()


# ---------------- Public API ----------------
def add_team(name: str) -> Tuple[bool, str]:
    """
    Lisää tiimin ja alustaa varaston.
    Palauttaa (ok, msg_or_folder).
      - ok=True  → msg_or_folder = polku tiimikansioon
      - ok=False → msg_or_folder = virheviesti
    """
    name = _norm(name)
    if not name:
        return (False, "Team name is empty.")

    teams: List[str] = _load(TEAMS_FP, [])
    if any((t or "").lower().strip() == name.lower() for t in teams):
        return (False, "Team already exists.")

    # 1) Päivitä teams.json (aakkosjärjestys, case-insensitiivinen)
    teams.append(name)
    _save(TEAMS_FP, sorted(teams, key=lambda x: x.lower()))

    # 2) Luo tiimikansio
    folder = TEAMS_DIR / name
    folder.mkdir(parents=True, exist_ok=True)

    # 3) Varmista tyhjä players.json tiimikansioon
    players_fp = folder / "players.json"
    if not players_fp.exists():
        players_fp.write_text("[]", encoding="utf-8")

    return (True, str(folder))


def list_teams() -> List[str]:
    """Palauta kaikkien tiimien lista `teams.json`ista (tyhjä lista, jos ei ole)."""
    teams: List[str] = _load(TEAMS_FP, [])
    # siivoa mahdolliset None/tyhjät
    return [t for t in teams if isinstance(t, str) and t.strip()]


# Säilytetään aiemman rajapinnan yhteensopivuus
list_teams_all = list_teams
