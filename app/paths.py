from pathlib import Path
import sys


def assets_dir() -> Path:
    # Works both in dev and when bundled with PyInstaller
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # _MEIPASS points to the temp unpack dir, but we still ship assets separately
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent
    return (base / "assets").resolve()
