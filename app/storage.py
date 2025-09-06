# app/storage.py
from __future__ import annotations
from pathlib import Path
import json
import os
import platform

def _default_base_dir() -> Path:
    # Windows: %APPDATA%\ScoutLens ; Muut: ~/.scoutlens tai ./data Cloudissa
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "ScoutLens"
    # Streamlit Cloud/Linux: käytä repojuuren alle .data
    # __file__ on .../app/storage.py → parent.parent on repojuuri
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / ".data"

class Storage:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else _default_base_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def file_path(self, name: str) -> Path:
        p = self.base_dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # Yhteensopivat apurit
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
