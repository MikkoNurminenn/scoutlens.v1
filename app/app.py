# app/app.py
from __future__ import annotations
from pathlib import Path
import importlib
import sys
from types import ModuleType
import traceback
import streamlit as st

# ---- Peruspolut
ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "app"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
importlib.invalidate_caches()


def bootstrap_sidebar_auto_collapse() -> None:
    if st.session_state.get("_collapse_sidebar"):
        st.session_state._collapse_sidebar = False
        st.markdown(
            """
            <script>
            const root = window.parent?.document || document;
            const btn = root.querySelector('button[aria-label="Main menu"]')
                      || root.querySelector('button[title="Main menu"]');
            btn?.click();
            </script>
            """,
            unsafe_allow_html=True,
        )


_ui_mod = ModuleType("app.ui")
_ui_mod.bootstrap_sidebar_auto_collapse = bootstrap_sidebar_auto_collapse
sys.modules.setdefault("app.ui", _ui_mod)

st.set_page_config(page_title="ScoutLens", layout="wide", initial_sidebar_state="expanded")
bootstrap_sidebar_auto_collapse()

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
show_export_page    = _safe_import("export",         "app.export_page",    "show_export_page")
login               = _safe_import("login",          "app.login",          "login")

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
NAV_KEYS = ["Reports", "Inspect Player", "Shortlists", "Export"]
NAV_LABELS = {
    "Reports": "📝 Reports",
    "Inspect Player": "🔍 Inspect Player",
    "Shortlists": "⭐ Shortlists",
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
    "Export": show_export_page,
}

def _sync_query(page: str) -> None:
    try:
        st.query_params = {"p": page}
    except Exception:
        pass

def main() -> None:
    inject_css()
    login()

    # URL → state init
    if "nav_page" not in st.session_state:
        p = st.query_params.get("p", None)
        p = LEGACY_REMAP.get(p, p)
        st.session_state["nav_page"] = p if p in NAV_KEYS else NAV_KEYS[0]
        _sync_query(st.session_state["nav_page"])

    # Clamp
    current = st.session_state.get("nav_page", NAV_KEYS[0])
    current = LEGACY_REMAP.get(current, current)
    if current not in NAV_KEYS:
        current = NAV_KEYS[0]
        st.session_state["nav_page"] = current

    # Sidebar: pidä state avaimena page-key; renderöi labelit format_funcilla
    with st.sidebar:
        st.markdown("<div class='scout-brand'>⚽ ScoutLens</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='scout-sub'>{APP_TAGLINE}</div>", unsafe_allow_html=True)
        st.markdown("<div class='nav-sep'>Navigation</div>", unsafe_allow_html=True)

        selection = st.radio(
            "Navigate",
            options=NAV_KEYS,
            index=NAV_KEYS.index(current),
            format_func=lambda k: NAV_LABELS.get(k, k),
            key="nav_choice_keyed",
            label_visibility="collapsed",
        )

        st.markdown(
            f"<div class='sb-footer'><strong>{APP_TITLE}</strong> v{APP_VERSION}</div>",
            unsafe_allow_html=True
        )

    if st.session_state.get("_prev_nav") != selection:
        st.session_state["_prev_nav"] = selection
        st.session_state["_collapse_sidebar"] = True
        st.session_state["nav_page"] = selection
        _sync_query(selection)
        st.stop()

    PAGE_FUNCS.get(selection, lambda: st.error("Page not found."))()

if __name__ == "__main__":
    main()
