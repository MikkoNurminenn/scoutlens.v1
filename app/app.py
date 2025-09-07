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
import streamlit as st

# --- Pages
from reports_page import show_reports_page
from shortlists import show_shortlists
from export_page import show_export_page
from login import login

APP_TITLE   = "ScoutLens"
APP_TAGLINE = "LATAM scouting toolkit"
APP_VERSION = "0.9.1"

# Page config must be first Streamlit call
st.set_page_config(page_title=APP_TITLE, layout="wide")

# --------- Global CSS injection ----------
def inject_css():
    base = Path("app/styles")
    css = "\n".join(
        (base / f).read_text(encoding="utf-8")
        for f in ["tokens.css", "layout.css", "components.css", "sidebar.css", "animations.css"]
        if (base / f).exists()
    )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

inject_css()

login()

# --------- Navigation setup ----------
# Visible pages in the sidebar
NAV_KEYS = ["Reports", "Players", "Export"]

NAV_LABELS = {
    "Reports": "📝 Reports",
    "Players": "📋 Players / Shortlists",
    "Export": "⬇️ Export",
}
LABEL_LIST = [NAV_LABELS[k] for k in NAV_KEYS]
LABEL_TO_KEY = {v: k for k, v in NAV_LABELS.items() if k in NAV_KEYS}

PAGE_FUNCS = {
    "Reports": show_reports_page,
    "Players": show_shortlists,
    "Export": show_export_page,
}

# --- Legacy key remap: mapataan vanhat reitit nykyisiin label-keyhin
LEGACY_REMAP = {
    "home": "Reports",
    "team_view": "Reports",
    "scout_reporter": "Reports",
    "shortlists": "Players",
    "player_editor": "Players",
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
    st.rerun()

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
        f"<strong>{APP_TITLE}</strong> v{APP_VERSION}<br>"
        f"Indigo × Sky theme • Hover + selection gradients"
        f"</div>",
        unsafe_allow_html=True
    )

# --------- Render current page ----------
PAGE_FUNCS.get(current_page, lambda: st.error("Page not found."))()
