# app/app.py
from __future__ import annotations
from pathlib import Path
import importlib
import sys
import traceback
import streamlit as st

from app.perf import track, render_perf
from app.ui.nav import go
from app.ui import bootstrap_sidebar_auto_collapse
from app.ui.sidebar_bg import set_sidebar_background

# ---- Peruspolut
ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "app"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
importlib.invalidate_caches()

st.set_page_config(page_title="ScoutLens", layout="wide", initial_sidebar_state="expanded")

# ---- Sivujen importit diagnoosilla
def _safe_import(what: str, mod: str, attr: str):
    try:
        m = importlib.import_module(mod)
        v = getattr(m, attr)
        return v
    except Exception as e:
        st.error(f"ImportError while importing {what} from {mod}.{attr}: {e}")
        st.code(
            "Debug info:\n"
            f"ROOT={ROOT}\n"
            f"PKG_DIR exists={PKG_DIR.exists()} files={', '.join(sorted(p.name for p in PKG_DIR.glob('*')))}\n"
            f"sys.path[0:3]={sys.path[:3]}\n"
            f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
        )
        st.stop()

show_reports_page   = _safe_import("reports page",   "app.reports_page",   "show_reports_page")
show_inspect_player = _safe_import("inspect player", "app.inspect_player", "show_inspect_player")
show_shortlists_page= _safe_import("shortlists",     "app.shortlists_page","show_shortlists_page")
show_player_management_page = _safe_import("player management", "app.player_management", "show_player_management_page")
show_shortlist_management_page = _safe_import("shortlist management", "app.shortlist_management", "show_shortlist_management_page")
show_export_page    = _safe_import("export",         "app.export_page",    "show_export_page")
login               = _safe_import("login",          "app.login",          "login")
logout              = _safe_import("logout",         "app.login",          "logout")

APP_TITLE   = "ScoutLens"
APP_TAGLINE = "LATAM scouting toolkit"
APP_VERSION = "0.9.1"

# --------- CSS
def inject_css():
    styles_dir = ROOT / "app" / "styles"
    parts = []
    for name in ["tokens.css", "layout.css", "components.css", "sidebar.css", "animations.css"]:
        p = styles_dir / name
        if p.exists():
            parts.append(p.read_text(encoding="utf-8"))
    if parts:
        st.markdown(f"<style>{'\n'.join(parts)}</style>", unsafe_allow_html=True)

# --------- Nav
NAV_KEYS = ["Reports", "Inspect Player", "Shortlists", "Manage Shortlists", "Players", "Export"]
NAV_LABELS = {
    "Reports": "📝 Reports",
    "Inspect Player": "🔍 Inspect Player",
    "Shortlists": "⭐ Shortlists",
    "Manage Shortlists": "🗑️ Manage Shortlists",
    "Players": "👤 Players",
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
    "Export": show_export_page,
}

def main() -> None:
    try:
        bootstrap_sidebar_auto_collapse()
    except Exception:
        pass

    inject_css()
    set_sidebar_background()
    login()

    if "current_page" not in st.session_state:
        p = st.query_params.get("p", None)
        p = LEGACY_REMAP.get(p, p)
        st.session_state["current_page"] = p if p in NAV_KEYS else NAV_KEYS[0]

    current = st.session_state.get("current_page", NAV_KEYS[0])

    with st.sidebar:
        st.markdown("<div class='scout-brand'>⚽ ScoutLens</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='scout-sub'>{APP_TAGLINE}</div>", unsafe_allow_html=True)
        st.markdown("<div class='nav-sep'>Navigation</div>", unsafe_allow_html=True)

        st.radio(
            "Navigate",
            options=NAV_KEYS,
            index=NAV_KEYS.index(current),
            format_func=lambda k: NAV_LABELS.get(k, k),
            key="_nav_radio",
            label_visibility="collapsed",
            on_change=lambda: go(st.session_state["_nav_radio"]),
        )

        auth = st.session_state.get("auth", {})
        user = auth.get("user")
        if auth.get("authenticated") and user:
            name = user.get("name") or user.get("username", "")
            st.markdown(
                f"<div class='sb-user'>Signed in as {name}</div>",
                unsafe_allow_html=True,
            )
            st.button("Sign out", on_click=logout, type="secondary")

        st.markdown(
            f"<div class='sb-footer'><strong>{APP_TITLE}</strong> v{APP_VERSION}</div>",
            unsafe_allow_html=True
        )

    page_func = PAGE_FUNCS.get(current, lambda: st.error("Page not found."))
    with track(f"page:{current}"):
        page_func()
    render_perf()

if __name__ == "__main__":
    main()
