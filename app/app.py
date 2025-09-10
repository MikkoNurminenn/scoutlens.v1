# app/app.py
# =============================================================================
# ScoutLens — App shell with polished sidebar navigation (stable across reruns)
# - Single-source-of-truth nav (st.session_state["nav_page"])
# - URL sync (?p=...) both ways
# - Immediate rerun on change → page switches on first click
# - Fancy sidebar: hover effects, selected gradient, icons
# - CSS injected on EVERY run (fixes style "changing" when navigating)
# =============================================================================

from __future__ import annotations
from pathlib import Path
import sys
import streamlit as st

# Ensure package imports work when running as `python app/app.py`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Pages
from app.reports_page import show_reports_page
from app.inspect_player import show_inspect_player
from app.shortlists_page import show_shortlists_page
from app.export_page import show_export_page
from app.login import login

APP_TITLE   = "ScoutLens"
APP_TAGLINE = "LATAM scouting toolkit"
APP_VERSION = "0.9.1"

# --------- Global CSS injection ----------
def inject_css():
    base = Path("app/styles")
    css = "\n".join(
        (base / f).read_text(encoding="utf-8")
        for f in ["tokens.css", "layout.css", "components.css", "sidebar.css", "animations.css"]
        if (base / f).exists()
    )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# --------- Navigation setup ----------
# Visible pages in the sidebar
NAV_KEYS = ["Reports", "Inspect Player", "Shortlists", "Export"]

NAV_LABELS = {
    "Reports": "📝 Reports",
    "Inspect Player": "🔍 Inspect Player",
    "Shortlists": "⭐ Shortlists",
    "Export": "⬇️ Export",
}
LABEL_LIST = [NAV_LABELS[k] for k in NAV_KEYS]
LABEL_TO_KEY = {v: k for k, v in NAV_LABELS.items() if k in NAV_KEYS}

PAGE_FUNCS = {
    "Reports": show_reports_page,
    "Inspect Player": show_inspect_player,
    "Shortlists": show_shortlists_page,
    "Export": show_export_page,
}

# --- Legacy key remap: mapataan vanhat reitit nykyisiin label-keyhin
LEGACY_REMAP = {
    "home": "Reports",
    "team_view": "Reports",
    "scout_reporter": "Reports",
    "shortlists": "Shortlists",
    "player_editor": "Shortlists",
}

def _sync_query(page: str) -> None:
    try:
        st.query_params["p"] = page
    except Exception:
        try:
            st.query_params = {"p": page}
        except Exception:
            pass

def _on_nav_change() -> None:
    label = st.session_state["nav_choice"]
    page = LABEL_TO_KEY.get(label, NAV_KEYS[0])
    st.session_state["nav_page"] = page
    _sync_query(page)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    # Temporary cache bust during Supabase client upgrade
    try:
        st.cache_data.clear()
        st.cache_resource.clear()
    except Exception:
        pass

    inject_css()
    login()

    # --------- Init from URL once ----------
    if "nav_page" not in st.session_state:
        p = st.query_params.get("p", None)
        p = LEGACY_REMAP.get(p, p)  # remap legacy if present
        st.session_state["nav_page"] = p if p in NAV_KEYS else NAV_KEYS[0]
        _sync_query(st.session_state["nav_page"])

    # Clamp current page (handles legacy + invalid keys)
    current_page = st.session_state.get("nav_page", NAV_KEYS[0])
    current_page = LEGACY_REMAP.get(current_page, current_page)
    if current_page not in NAV_KEYS:
        current_page = NAV_KEYS[0]
        st.session_state["nav_page"] = current_page

    # Keep visible label in sync, safely
    desired_label = NAV_LABELS.get(current_page, NAV_LABELS[NAV_KEYS[0]])
    if st.session_state.get("nav_choice") != desired_label:
        st.session_state["nav_choice"] = desired_label

    # --------- Sidebar UI ----------
    with st.sidebar:
        st.markdown("<div class='scout-brand'>⚽ ScoutLens</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='scout-sub'>{APP_TAGLINE}</div>", unsafe_allow_html=True)
        st.markdown("<div class='nav-sep'>Navigation</div>", unsafe_allow_html=True)

        st.radio(
            "Navigate",
            options=LABEL_LIST,
            key="nav_choice",
            label_visibility="collapsed",
            on_change=_on_nav_change,
        )

        st.markdown(
            f"<div class='sb-footer'>"
            f"<strong>{APP_TITLE}</strong> v{APP_VERSION}"
            f"</div>",
            unsafe_allow_html=True
        )

    # --------- Render current page ----------
    PAGE_FUNCS.get(current_page, lambda: st.error("Page not found."))()


if __name__ == "__main__":
    main()
