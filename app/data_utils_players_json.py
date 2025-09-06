# data_utils_players_json.py (yhtenäistetty)
import json
from pathlib import Path
from app_paths import file_path
from storage import load_json, save_json

PLAYERS_FP = file_path("players.json")

def load_all_players():
    return load_json(PLAYERS_FP, [])

def get_players_by_team(team_name: str):
    data = load_json(PLAYERS_FP, [])  # lista
    norm = lambda s: (s or "").lower().replace(" ", "")
    return [p for p in data if norm(p.get("team_name") or p.get("Team") or p.get("team")) == norm(team_name)]

def save_players(players_list: list):
    save_json(PLAYERS_FP, players_list)
