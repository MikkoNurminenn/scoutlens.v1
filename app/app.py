# file: app/app.py
from __future__ import annotations
from pathlib import Path
import importlib
import importlib.util
import sys
import traceback
import streamlit as st

# ---- Peruspolut (MUST run before any local imports)
ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "app"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # why: ensure local package wins over site-packages
try:
    (PKG_DIR / "__init__.py").touch(exist_ok=True)  # why: mark as package if missing
except OSError:
    pass
importlib.invalidate_caches()

# ---- Import resolver guard (avoid 3rd‑party package named "app")
_spec = importlib.util.find_spec("app")
if not _spec or not getattr(_spec, "origin", None):
    st.error(
        "Cannot resolve local package 'app'. Check repo layout and permissions.\n"
        f"ROOT={ROOT}\nPKG_DIR={PKG_DIR}\nsys.path[0:3]={sys.path[:3]}"
    )
    st.stop()

# ---- Delay all local imports until after bootstrapping
track = importlib.import_module("app.perf").__getattribute__("track")
render_perf = importlib.import_module("app.perf").__getattribute__("render_perf")
go = importlib.import_module("app.ui.nav").__getattribute__("go")
bootstrap_sidebar_auto_collapse = importlib.import_module("app.ui").__getattribute__(
    "bootstrap_sidebar_auto_collapse"
)
set_sidebar_background = importlib.import_module("app.ui.sidebar_bg").__getattribute__(
    "set_sidebar_background"
)
build_sidebar = importlib.import_module("app.ui.sidebar").__getattribute__(
    "build_sidebar"
)

st.set_page_config(page_title="Main", layout="wide", initial_sidebar_state="expanded")

# ---- Page imports (Streamlit-safe wrapper)

def _safe_import(what: str, mod: str, attr: str):
    """Import attribute with on-screen diagnostics (Streamlit-safe)."""
    try:
        m = importlib.import_module(mod)
        v = getattr(m, attr)
        return v
    except Exception as e:  # why: surface exact failure to the UI for non-dev users
        st.error(f"ImportError while importing {what} from {mod}.{attr}: {e}")
        st.code(
            "Debug info:\n"
            f"ROOT={ROOT}\n"
            f"PKG_DIR exists={PKG_DIR.exists()} files={', '.join(sorted(p.name for p in PKG_DIR.glob('*')))}\n"
            f"sys.path[0:3]={sys.path[:3]}\n"
            f"Resolved 'app' origin={getattr(_spec, 'origin', None)}\n"
            f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
        )
        st.stop()

show_reports_page = _safe_import("reports page", "app.reports_page", "show_reports_page")
show_inspect_player = _safe_import("inspect player", "app.inspect_player", "show_inspect_player")
show_shortlists_page = _safe_import("shortlists", "app.shortlists_page", "show_shortlists_page")
show_player_management_page = _safe_import(
    "player management", "app.player_management", "show_player_management_page"
)
show_shortlist_management_page = _safe_import(
    "shortlist management", "app.shortlist_management", "show_shortlist_management_page"
)
show_export_page = _safe_import("export", "app.export_page", "show_export_page")
login = _safe_import("login", "app.login", "login")
logout = _safe_import("logout", "app.login", "logout")
show_quick_notes_page = _safe_import(
    "notes", "app.quick_notes_page", "show_quick_notes_page"
)

APP_TITLE = "ScoutLens"
APP_TAGLINE = "LATAM scouting toolkit"
APP_VERSION = "0.9.1"

# --------- CSS

def inject_css():
    styles_dir = ROOT / "app" / "styles"
    token_file = "tokens_dark.css"
    parts = []
    for name in [token_file, "layout.css", "components.css", "sidebar.css", "animations.css"]:
        p = styles_dir / name
        if p.exists():
            parts.append(p.read_text(encoding="utf-8"))
    # remove previously injected theme block if present
    st.markdown(
        "<script>var e=document.getElementById('sl-theme'); if (e) e.remove();</script>",
        unsafe_allow_html=True,
    )
    if parts:
        st.markdown(
            f"<style id='sl-theme'>{'\n'.join(parts)}</style>",
            unsafe_allow_html=True,
        )

# --------- Nav
NAV_KEYS = [
    "Reports",
    "Inspect Player",
    "Shortlists",
    "Manage Shortlists",
    "Players",
    "Notes",
    "Export",
]
NAV_LABELS = {
    "Reports": "📝 Reports",
    "Inspect Player": "🔍 Inspect Player",
    "Shortlists": "⭐ Shortlists",
    "Manage Shortlists": "🗑️ Manage Shortlists",
    "Players": "👤 Players",
    "Notes": "🗒️ Quick notes",
    "Export": "⬇️ Export",
}
LEGACY_REMAP = {
    "home": "Reports",
    "team_view": "Reports",
    "scout_reporter": "Reports",
    "shortlists": "Shortlists",
    "player_editor": "Shortlists",
}
PAGE_FUNCS = {
    "Reports": show_reports_page,
    "Inspect Player": show_inspect_player,
    "Shortlists": show_shortlists_page,
    "Manage Shortlists": show_shortlist_management_page,
    "Players": show_player_management_page,
    "Notes": show_quick_notes_page,
    "Export": show_export_page,
}


def main() -> None:
    try:
        bootstrap_sidebar_auto_collapse()
    except Exception:
        pass

    login()

    if "current_page" not in st.session_state:
        p = st.query_params.get("p", None)
        p = LEGACY_REMAP.get(p, p)
        st.session_state["current_page"] = p if p in NAV_KEYS else NAV_KEYS[0]

    current = st.session_state.get("current_page", NAV_KEYS[0])

    build_sidebar(
        current=current,
        nav_keys=NAV_KEYS,
        nav_labels=NAV_LABELS,
        app_title=APP_TITLE,
        app_tagline=APP_TAGLINE,
        app_version=APP_VERSION,
        go=go,
        logout=logout,
    )

    inject_css()
    set_sidebar_background()

    page_func = PAGE_FUNCS.get(current, lambda: st.error("Page not found."))
    with track(f"page:{current}"):
        page_func()
    render_perf()


if __name__ == "__main__":
    main()
