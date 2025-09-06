# teams_store.py
from pathlib import Path
import json
from app_paths import file_path, DATA_DIR

TEAMS_FP = file_path("teams.json")
TEAMS_DIR = DATA_DIR / "teams"


def _load(fp: Path, default):
    try:
        if Path(fp).exists():
            return json.loads(Path(fp).read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save(fp: Path, obj):
    fp.parent.mkdir(parents=True, exist_ok=True)
    Path(fp).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _norm(s: str) -> str:
    return (s or "").strip()


def add_team(name: str) -> tuple[bool, str]:
    """
    Lisää tiimin ja alustaa varaston.
    Palauttaa (ok, msg_or_folder).
    - ok=True  → msg_or_folder = polku tiimikansioon
    - ok=False → msg_or_folder = virheviesti
    """
    name = _norm(name)
    if not name:
        return (False, "Team name is empty.")

    teams = _load(TEAMS_FP, [])
    if any((t or "").lower().strip() == name.lower() for t in teams):
        return (False, "Team already exists.")

    # 1) Päivitä teams.json
    teams.append(name)
    _save(TEAMS_FP, sorted(teams, key=lambda x: x.lower()))

    # 2) Luo kansio
    folder = TEAMS_DIR / name
    folder.mkdir(parents=True, exist_ok=True)

    # 3) Tyhjä players.json jos puuttuu
    players_fp = folder / "players.json"
    if not players_fp.exists():
        players_fp.write_text("[]", encoding="utf-8")

    return (True, str(folder))


def list_teams() -> list[str]:
    # Yhtenäinen listaus samasta lähteestä
    return _load(TEAMS_FP, [])


# Säilytetään aiemman rajapinnan yhteensopivuus
list_teams_all = list_teams
