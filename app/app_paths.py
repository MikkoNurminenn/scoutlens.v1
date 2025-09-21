# app_paths.py — yhtenäinen datapolku local/Cloud
from pathlib import Path
import os

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


# Player photos and export artefacts can still live locally, but the
# primary data source (players, teams, matches, reports, notes) is Supabase.
PLAYER_PHOTOS_DIR = DATA_DIR / "player_photos"
PLAYER_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
