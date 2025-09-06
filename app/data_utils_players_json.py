# data_utils_players_json.py (yhtenäistetty)
import json
from pathlib import Path
from app_paths import file_path

PLAYERS_FP = file_path("players.json")

def safe_load_json(path: Path):
    try:
        if Path(path).exists():
            txt = Path(path).read_text(encoding="utf-8").strip()
            return json.loads(txt) if txt else []
    except Exception:
        pass
    return []  # LISTA, ei dict

def load_all_players():
    return safe_load_json(PLAYERS_FP)

def get_players_by_team(team_name: str):
    data = safe_load_json(PLAYERS_FP)  # lista
    norm = lambda s: (s or "").lower().replace(" ", "")
    return [p for p in data if norm(p.get("team_name") or p.get("Team") or p.get("team")) == norm(team_name)]

def save_players(players_list: list):
    PLAYERS_FP.write_text(json.dumps(players_list, ensure_ascii=False, indent=2), encoding="utf-8")
