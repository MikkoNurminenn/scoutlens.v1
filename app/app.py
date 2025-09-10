# app/app.py
from __future__ import annotations
from pathlib import Path
import os
import sys
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ui import bootstrap_sidebar_auto_collapse
from app.reports_page import show_reports_page
from app.inspect_player import show_inspect_player
from app.shortlists_page import show_shortlists_page
from app.export_page import show_export_page
from app.login import login

st.set_page_config(page_title="ScoutLens", layout="wide", initial_sidebar_state="expanded")
bootstrap_sidebar_auto_collapse()

APP_TITLE   = "ScoutLens"
APP_TAGLINE = "LATAM scouting toolkit"
APP_VERSION = "0.9.1"

def inject_css() -> None:
    # Miksi: suhteelliset polut hajoavat eri käynnistystavoilla.
    styles_dir = ROOT / "app" / "styles"
    parts = []
    for name in ["tokens.css", "layout.css", "components.css", "sidebar.css", "animations.css"]:
        p = styles_dir / name
        if p.exists():
            parts.append(p.read_text(encoding="utf-8"))
    if parts:
        st.markdown(f"<style>{'\n'.join(parts)}</style>", unsafe_allow_html=True)

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

def set_query_page(page: str) -> None:
    # Miksi: vähennetään versioriippuvuutta ja ylimääräisiä reruneja.
    try:
        st.query_params = {"p": page}
    except Exception:
        pass

def main() -> None:
    # Tyhjennä cache vain kun DEBUG=1
    if os.getenv("SCOUTLENS_DEBUG_CACHE") == "1":
        try:
            st.cache_data.clear()
            st.cache_resource.clear()
        except Exception:
            pass

    inject_css()
    login()

    # Init URL → state
    if "nav_page" not in st.session_state:
        p = st.query_params.get("p", None)
        if p in LEGACY_REMAP:
            p = LEGACY_REMAP[p]
        st.session_state["nav_page"] = p if p in NAV_KEYS else NAV_KEYS[0]
        set_query_page(st.session_state["nav_page"])

    # Clamp
    current = st.session_state.get("nav_page", NAV_KEYS[0])
    current = LEGACY_REMAP.get(current, current)
    if current not in NAV_KEYS:
        current = NAV_KEYS[0]
        st.session_state["nav_page"] = current

    # Sidebar (pidä state avaimena page-key, renderöi label format_funcilla)
    with st.sidebar:
        st.markdown("<div class='scout-brand'>⚽ ScoutLens</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='scout-sub'>{APP_TAGLINE}</div>", unsafe_allow_html=True)
        st.markdown("<div class='nav-sep'>Navigation</div>", unsafe_allow_html=True)

        def fmt(k: str) -> str:
            return NAV_LABELS.get(k, k)

        selection = st.radio(
            "Navigate",
            options=NAV_KEYS,
            index=NAV_KEYS.index(current),
            format_func=fmt,
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
        set_query_page(selection)
        st.stop()

    PAGE_FUNCS.get(selection, lambda: st.error("Page not found."))()

if __name__ == "__main__":
    main()
