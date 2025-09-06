# teams_store.py
from pathlib import Path
import json
from app_paths import file_path
from supabase_client import get_client

TEAMS_FP   = file_path("teams.json")
PLAYERS_FP = file_path("players.json")

def _load(fp: Path, default):
    try:
        if Path(fp).exists():
            return json.loads(Path(fp).read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def _save(fp: Path, data):
    Path(fp).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _norm_team(p: dict) -> str:
    # ✅ Huom: ei enää lueta current_club/CurrentClub kenttiä
    return (p.get("team_name") or p.get("Team") or p.get("team") or "").strip()

def list_teams_all() -> list[str]:
    """Return all known team names.

    If Supabase credentials are configured, teams are loaded from the
    "teams" table. Otherwise teams.json ∪ players.json(team_name/Team/team)
    is used.
    """
    sb = get_client()
    if sb:
        try:
            res = sb.table("teams").select("name").execute()
            return sorted(t.get("name", "") for t in res.data or [])
        except Exception:
            pass

    teams = set(_load(TEAMS_FP, []))
    for p in _load(PLAYERS_FP, []):
        t = _norm_team(p)
        if t:
            teams.add(t)
    return sorted(teams)

def add_team(name: str) -> bool:
    name = (name or "").strip()
    if not name:
        return False
    sb = get_client()
    if sb:
        try:
            sb.table("teams").upsert({"name": name}).execute()
            return True
        except Exception:
            pass
    teams = set(_load(TEAMS_FP, []))
    if name not in teams:
        teams.add(name)
        _save(TEAMS_FP, sorted(teams))
    return True

def remove_team(name: str) -> None:
    sb = get_client()
    if sb:
        try:
            sb.table("teams").delete().eq("name", name).execute()
            return
        except Exception:
            pass
    teams = [t for t in _load(TEAMS_FP, []) if t != name]
    _save(TEAMS_FP, teams)

