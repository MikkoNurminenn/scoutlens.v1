# app_paths.py — yhtenäinen datapolku local/Cloud
from pathlib import Path
import os, json

APP_NAME = "ScoutLens"
CLOUD = os.getenv("SCOUTLENS_CLOUD", "0") == "1"

if CLOUD:
    # Streamlit Cloud: repojuuren alle väliaikainen kansio
    DATA_DIR = Path("./cloud_data")
else:
    # Windows/macOS local
    DATA_DIR = Path(
        os.getenv("SCOUTLENS_APPDATA") or
        (Path(os.getenv("APPDATA", Path.home())) / APP_NAME)
    )

DATA_DIR.mkdir(parents=True, exist_ok=True)

def file_path(name: str) -> Path:
    return DATA_DIR / name

# Predefined file paths and directories
PLAYERS_FP = file_path("players.json")
MATCHES_FP = file_path("matches.json")
SCOUT_REPORTS_FP = file_path("scout_reports.json")
SHORTLISTS_FP = file_path("shortlists.json")
NOTES_FP = file_path("notes.json")

PLAYER_PHOTOS_DIR = DATA_DIR / "player_photos"
PLAYER_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Luo oletustiedostot jos puuttuu (turvallinen ajaa aina)
for fp, default in [
    (PLAYERS_FP, []),
    (MATCHES_FP, []),
    (SCOUT_REPORTS_FP, []),
    (SHORTLISTS_FP, {}),
    (NOTES_FP, [])
]:
    if not fp.exists():
        fp.write_text(json.dumps(default), encoding="utf-8")
