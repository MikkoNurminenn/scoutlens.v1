# teams_store.py
from pathlib import Path
import json
from app_paths import file_path
from storage import load_json, save_json

TEAMS_FP   = file_path("teams.json")
PLAYERS_FP = file_path("players.json")

def _norm_team(p: dict) -> str:
    # ✅ Huom: ei enää lueta current_club/CurrentClub kenttiä
    return (p.get("team_name") or p.get("Team") or p.get("team") or "").strip()

def list_teams_all() -> list[str]:
    """teams.json ∪ players.json(team_name/Team/team)"""
    teams = set(load_json(TEAMS_FP, []))
    for p in load_json(PLAYERS_FP, []):
        t = _norm_team(p)
        if t:
            teams.add(t)
    return sorted(teams)

def add_team(name: str) -> bool:
    name = (name or "").strip()
    if not name:
        return False
    teams = set(load_json(TEAMS_FP, []))
    if name not in teams:
        teams.add(name)
        save_json(TEAMS_FP, sorted(teams))
    return True

def remove_team(name: str) -> None:
    teams = [t for t in load_json(TEAMS_FP, []) if t != name]
    save_json(TEAMS_FP, teams)
