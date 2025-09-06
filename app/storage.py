# app/storage.py — self-contained adapter (no app.* imports)
from __future__ import annotations
from pathlib import Path
import json, os, platform

# --- Base dir: Windows -> %APPDATA%\ScoutLens, muut -> repo/.data
def _default_base_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "ScoutLens"
    # Linux/mac/Cloud: repojuuren alle .data (tämä tiedosto: .../app/storage.py)
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / ".data"

BASE_DIR = _default_base_dir()
BASE_DIR.mkdir(parents=True, exist_ok=True)

def file_path(name: str) -> Path:
    p = BASE_DIR / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def load_json(name_or_fp: str | Path, default):
    p = file_path(name_or_fp) if isinstance(name_or_fp, str) else Path(name_or_fp)
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def save_json(name_or_fp: str | Path, data):
    p = file_path(name_or_fp) if isinstance(name_or_fp, str) else Path(name_or_fp)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

IS_CLOUD = (platform.system() not in ("Windows", "Darwin"))

# Valinnainen luokkakääre jos joku moduuli vielä käyttää Storage-oliota
class Storage:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def file_path(self, name: str) -> Path:
        return self.base_dir / name

    def read_json(self, fp: Path, default):
        try:
            if fp.exists():
                return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
        return default

    def write_json(self, fp: Path, data):
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
