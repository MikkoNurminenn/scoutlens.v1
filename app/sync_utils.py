# sync_utils.py
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
from typing import Any, List, Dict, Tuple, Optional

# --- Projektin polut / datalähteet ---
from app_paths import file_path
from data_utils import load_master  # palauttaa DataFrame:n

# Yritetään käyttää projektin Storagea; jos ei ole, fallback paikalliseen JSON-lukuun
try:
    from storage import load_json as _storage_load_json, save_json as _storage_save_json  # type: ignore
    _HAS_STORAGE = True
except Exception:
    _HAS_STORAGE = False
    _storage_load_json = None
    _storage_save_json = None

# Supabase on vapaaehtoinen. Jos clienttiä ei ole tai ei konffattu, upload/download palauttaa 0.
try:
    from supabase_client import get_client  # type: ignore
except Exception:
    def get_client():
        return None  # pragma: no cover

PLAYERS_FP = file_path("players.json")


# -------------------------
# JSON apurit (safe fallback)
# -------------------------
def _load_json(fp: Path, default: Any) -> Any:
    """Lue JSON turvallisesti. Käytä Storagea jos saatavilla, muuten fallback."""
    if _HAS_STORAGE and _storage_load_json is not None:
        try:
            return _storage_load_json(fp, default)
        except Exception:
            return default
    try:
        if fp.exists():
            return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json(fp: Path, data: Any) -> None:
    """Tallenna JSON turvallisesti. Käytä Storagea jos saatavilla, muuten fallback."""
    if _HAS_STORAGE and _storage_save_json is not None:
        try:
            _storage_save_json(fp, data)
            return
        except Exception:
            pass
    try:
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # Viimeinen oljenkorsi: yritetään ilman indentiä
        fp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _norm_nat(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple, set)):
        return ", ".join(str(x).strip() for x in v if str(x).strip())
    return str(v).strip()


# -------------------------
# Bulk sync: team → players.json
# -------------------------
def bulk_sync_team_to_players_json(team_name: str) -> int:
    """Lue teamin master-DF ja synkkaa/mergeä se players.json:iin nimen+joukkueen avaimella."""
    df = load_master(team_name)
    if df is None or getattr(df, "empty", True):
        return 0

    players: List[Dict[str, Any]] = _load_json(PLAYERS_FP, [])
    index_by_key: Dict[Tuple[str, str], int] = {
        (str(p.get("name", "")).strip(), str(p.get("team_name", "")).strip()): i
        for i, p in enumerate(players)
    }

    added_or_updated = 0
    for _, r in df.iterrows():
        name = str(r.get("Name", "")).strip()
        if not name:
            continue

        pid = str(r.get("PlayerID") or uuid4().hex)
        rec = {
            "id": pid,
            "name": name,
            "team_name": str(team_name).strip(),
            "date_of_birth": str(r.get("DateOfBirth", "") or ""),
            "nationality": _norm_nat(r.get("Nationality", "")),
            "preferred_foot": str(r.get("PreferredFoot", "") or "").strip(),
            "club_number": int(r.get("ClubNumber", 0) or 0),
            "position": str(r.get("Position", "") or "").strip(),
            "scout_rating": int(r.get("ScoutRating", 0) or 0),
        }

        key = (rec["name"], rec["team_name"])
        if key in index_by_key:
            # Mergeä olemassa olevaan (säilytä muut kentät)
            players[index_by_key[key]] = {**players[index_by_key[key]], **rec}
        else:
            players.append(rec)
            index_by_key[key] = len(players) - 1
        added_or_updated += 1

    _save_json(PLAYERS_FP, players)
    return added_or_updated


# -------------------------
# Supabase sync (optional)
# -------------------------
def upload_players_to_supabase() -> int:
    """Lähetä players.json Supabasen 'players'-tauluun (upsert). Palauttaa rivimäärän tai 0."""
    sb = get_client()
    if not sb:
        return 0

    players: List[Dict[str, Any]] = _load_json(PLAYERS_FP, [])
    if not players:
        return 0
    try:
        sb.table("players").upsert(players).execute()
        return len(players)
    except Exception:
        return 0


def download_players_from_supabase() -> int:
    """Hae Supabasesta 'players' ja korvaa paikallinen players.json. Palauttaa rivimäärän tai 0."""
    sb = get_client()
    if not sb:
        return 0
    try:
        res = sb.table("players").select("*").execute()
        players = res.data or []
    except Exception:
        return 0

    _save_json(PLAYERS_FP, players)
    return len(players)


__all__ = [
    "bulk_sync_team_to_players_json",
    "upload_players_to_supabase",
    "download_players_from_supabase",
]
