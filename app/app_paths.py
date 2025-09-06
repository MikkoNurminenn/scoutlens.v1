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

# Luo oletustiedostot jos puuttuu (turvallinen ajaa aina)
for fname, default in [
    ("players.json", []),
    ("matches.json", []),
    ("scout_reports.json", []),
    ("shortlists.json", {}),
    ("notes.json", [])
]:
    fp = file_path(fname)
    if not fp.exists():
        fp.write_text(json.dumps(default), encoding="utf-8")
