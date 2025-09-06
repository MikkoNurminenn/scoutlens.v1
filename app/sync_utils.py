# sync_utils.py
import json
from pathlib import Path
from uuid import uuid4
from datetime import date
import pandas as pd

from app_paths import file_path
from data_utils import load_master
from storage import load_json, save_json

PLAYERS_FP = file_path("players.json")

def _save_json(fp: Path, data):
    save_json(fp, data)

def _norm_nat(v):
    if v is None: return ""
    if isinstance(v, (list, tuple, set)): 
        return ", ".join(str(x).strip() for x in v if str(x).strip())
    return str(v).strip()

def bulk_sync_team_to_players_json(team_name: str) -> int:
    df = load_master(team_name)
    if df is None or df.empty:
        return 0

    players = load_json(PLAYERS_FP, [])
    index_by_key = {(p.get("name","").strip(), p.get("team_name","").strip()): i for i,p in enumerate(players)}

    added_or_updated = 0
    for _, r in df.iterrows():
        name = str(r.get("Name","")).strip()
        if not name:
            continue
        pid  = str(r.get("PlayerID") or uuid4().hex)
        rec  = {
            "id": pid,
            "name": name,
            "team_name": team_name,
            "date_of_birth": str(r.get("DateOfBirth","")),
            "nationality": _norm_nat(r.get("Nationality","")),
            "preferred_foot": str(r.get("PreferredFoot","")),
            "club_number": int(r.get("ClubNumber",0) or 0),
            "position": str(r.get("Position","")),
            "scout_rating": int(r.get("ScoutRating",0) or 0),
        }
        key = (rec["name"], rec["team_name"])
        if key in index_by_key:
            players[index_by_key[key]] = {**players[index_by_key[key]], **rec}
        else:
            players.append(rec)
        added_or_updated += 1

    _save_json(PLAYERS_FP, players)
    return added_or_updated
