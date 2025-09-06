# launch.py — käynnistää Streamlit-sovelluksen myös PyInstaller-paketista
import sys, os
from streamlit.web.cli import main as st_main

def resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)

if __name__ == "__main__":
    # Aja paketin sisältä / kehityksestä käsin
    os.chdir(getattr(sys, "_MEIPASS", os.path.abspath(".")))

    # Windows-datapolku: %APPDATA%/ScoutLens
    os.environ.setdefault(
        "SCOUTLENS_APPDATA",
        os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "ScoutLens")
    )

    app_path = resource_path(os.path.join("app", "app.py"))
    sys.argv = ["streamlit", "run", app_path, "--server.headless=true"]
    raise SystemExit(st_main())
