from __future__ import annotations
from pathlib import Path
import sys

def ensure_project_paths() -> Path:
    """
    Lisää projektin juuressa olevan polun sys.pathiin,
    jotta 'app.*' -importit toimivat riippumatta käynnistyspaikasta.
    Palauttaa projektijuuripolun.
    """
    here = Path(__file__).resolve()
    app_dir = here.parents[1]          # .../app
    project_root = app_dir.parent      # projektin juuri
    for cand in (str(project_root), str(app_dir)):
        if cand not in sys.path:
            sys.path.append(cand)
    return project_root

def assert_app_paths() -> dict:
    """
    Varmista että app/ui/sidebar_toggle_css.py löytyy. Palauttaa statuksen.
    """
    project_root = ensure_project_paths()
    app_dir = project_root / "app"
    ui_dir = app_dir / "ui"
    css_file = ui_dir / "sidebar_toggle_css.py"
    return {
        "project_root": str(project_root),
        "app_dir_exists": app_dir.exists(),
        "ui_dir_exists": ui_dir.exists(),
        "css_file_exists": css_file.exists(),
        "css_file_path": str(css_file),
    }
