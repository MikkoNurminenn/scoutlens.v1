# app_paths.py
from pathlib import Path
import os, platform, tempfile

def _is_writable(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True
    except Exception:
        return False

def get_data_dir() -> Path:
    home = Path.home()
    system = platform.system()

    candidates = []
    if system == "Windows":
        appdata = Path(os.getenv("APPDATA", home))
        candidates += [appdata / "ScoutLens"]
    elif system == "Darwin":  # macOS
        candidates += [
            home / "Library" / "Application Support" / "ScoutLens",
            home / "ScoutLens",  # fallback
        ]
    else:  # Linux & muut
        candidates += [
            home / ".local" / "share" / "ScoutLens",
            home / "ScoutLens",  # fallback
        ]

    # Viimeinen hätävara: temp-kansio
    candidates.append(Path(tempfile.gettempdir()) / "ScoutLens")

    for c in candidates:
        if _is_writable(c):
            return c

    # Jos mikään ei onnistu (erittäin harvinaista), käytä current working dir
    cwd = Path.cwd() / "ScoutLens"
    cwd.mkdir(parents=True, exist_ok=True)
    return cwd

DATA_DIR = get_data_dir()

def file_path(name: str) -> Path:
    p = DATA_DIR / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
