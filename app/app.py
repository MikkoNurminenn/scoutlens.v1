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
import streamlit as st

# --- Pages
from home import show_home
from team_view import show_team_view
from player_editor import show_player_editor
from scout_reporter import show_scout_match_reporter
from notes import show_notes  # varmista, että notes.py sisältää show_notes()
from shortlists import show_shortlists  # ⭐ uusi sivu

APP_TITLE   = "ScoutLens"
APP_TAGLINE = "LATAM scouting toolkit"
APP_VERSION = "0.9.1"

# Page config must be first Streamlit call
st.set_page_config(page_title=APP_TITLE, layout="wide")

# --------- Sidebar CSS (inject every run) ----------
SIDEBAR_CSS = r"""
:root{
  --sb-bg-1:#0d1117;
  --sb-bg-2:#111827;
  --sb-fg:#e5e7eb;
  --sb-fg-dim:#cbd5e1;
  --sb-ac-1:#6366f1;
  --sb-ac-2:#0ea5e9;
  --sb-border:rgba(255,255,255,.08);
  --sb-border-strong:rgba(255,255,255,.18);
  --sb-item:rgba(255,255,255,.04);
  --sb-item-hover:rgba(255,255,255,.08);
  --sb-shadow:0 6px 24px rgba(0,0,0,.35);
}

section[data-testid="stSidebar"]{
  background: linear-gradient(180deg,var(--sb-bg-1),var(--sb-bg-2));
  color:var(--sb-fg);
  box-shadow: inset -1px 0 0 rgba(255,255,255,.03);
}
section[data-testid="stSidebar"] .block-container{
  padding-top: 12px; padding-bottom: 18px;
}

/* Brand */
.scout-brand{
  font-weight: 900; letter-spacing:.3px; margin: 2px 0 2px 0;
  font-size: 1.15rem;
  background: linear-gradient(90deg, var(--sb-fg), #ffffff 30%, var(--sb-fg));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.scout-sub{ opacity:.75; margin-top:-4px; font-size:.85rem; color:var(--sb-fg-dim); }

/* Section header */
.nav-sep{
  margin: 10px 0 6px 0; font-size:.78rem; text-transform:uppercase; letter-spacing:.12rem;
  color:var(--sb-fg-dim); opacity:.9;
}

/* Radio pills (sidebar only) */
section[data-testid="stSidebar"] [role="radiogroup"]{
  gap:8px;
}
section[data-testid="stSidebar"] [role="radiogroup"] > label{
  border:1px solid var(--sb-border);
  background:var(--sb-item);
  border-radius:12px;
  padding:10px 12px;
  transition:transform .08s ease, background .15s ease, border-color .15s ease, box-shadow .15s ease;
  cursor:pointer;
  display:flex; align-items:center; gap:.55rem;
  position: relative; isolation:isolate;
  min-height: 42px;
}

/* Hide native bullet */
section[data-testid="stSidebar"] [role="radiogroup"] input[type="radio"]{ display:none; }

/* Hover */
section[data-testid="stSidebar"] [role="radiogroup"] > label:hover{
  background:var(--sb-item-hover);
  border-color:var(--sb-border-strong);
  transform:translateX(2px);
  box-shadow: var(--sb-shadow);
}

/* Selected (preferred) */
section[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked){
  background:linear-gradient(135deg, color-mix(in srgb, var(--sb-ac-1) 30%, transparent),
                                      color-mix(in srgb, var(--sb-ac-2) 30%, transparent));
  border-color: color-mix(in srgb, var(--sb-ac-1) 65%, var(--sb-border-strong));
  box-shadow: 0 8px 26px color-mix(in srgb, var(--sb-ac-1) 35%, transparent);
}
/* Selected (fallback for browsers without :has) */
section[data-testid="stSidebar"] [role="radiogroup"] > label:focus-within{
  background:linear-gradient(135deg, color-mix(in srgb, var(--sb-ac-1) 22%, transparent),
                                      color-mix(in srgb, var(--sb-ac-2) 22%, transparent));
  border-color: color-mix(in srgb, var(--sb-ac-1) 55%, var(--sb-border-strong));
}

/* Left accent bar when selected */
section[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked)::before{
  content:""; position:absolute; left:0; top:0; bottom:0; width:4px;
  border-radius:12px 0 0 12px;
  background: linear-gradient(180deg, var(--sb-ac-1), var(--sb-ac-2));
}

/* Label text */
section[data-testid="stSidebar"] [role="radiogroup"] > label *{ color:var(--sb-fg); }

/* Footer card */
.sb-footer{
  margin-top:14px; padding:12px 12px;
  border:1px solid var(--sb-border);
  border-radius:12px; background:var(--sb-item);
  color:var(--sb-fg-dim); font-size:.82rem;
}
.sb-footer strong{ color:var(--sb-fg); }
"""
st.markdown(f"<style>{SIDEBAR_CSS}</style>", unsafe_allow_html=True)

# --------- Navigation setup ----------
# Näkyvät sivut sivupalkissa:
NAV_KEYS = ["Home", "Team View", "Shortlists", "Player Editor", "Scout Match Reporter", "Notes"]

NAV_LABELS = {
    "Home": "🏠 Home",
    "Team View": "🏟️ Team View",
    "Shortlists": "⭐ Shortlists",          # ⬅️ uusi label
    "Player Editor": "✍️ Player Editor",
    "Scout Match Reporter": "📝 Scout Match Reporter",
    "Notes": "🗒️ Notes",
}
LABEL_LIST   = [NAV_LABELS[k] for k in NAV_KEYS]
LABEL_TO_KEY = {v: k for k, v in NAV_LABELS.items() if k in NAV_KEYS}

PAGE_FUNCS = {
    "Home": show_home,
    "Team View": show_team_view,
    "Shortlists": show_shortlists,          # ⬅️ uusi reitti
    "Player Editor": show_player_editor,
    "Scout Match Reporter": show_scout_match_reporter,
    "Notes": show_notes,
}

# --- Legacy key remap: mapataan vanhat reitit nykyisiin label-keyhin
LEGACY_REMAP = {
    # snake/camel/old keys -> canonical keys used in this shell
    "home": "Home",
    "team_view": "Team View",
    "player_editor": "Player Editor",
    "player_preview": "Player Editor",
    "scout_reporter": "Scout Match Reporter",
    "scout_match_reporter": "Scout Match Reporter",
    "add_player": "Player Editor",
    "add_player_form": "Player Editor",
    "csv_importer": "Home",
    "match_calendar": "Home",
    "notes": "Notes",
    "shortlists": "Shortlists",             # ⬅️ legacy → uusi
    "shortlist": "Shortlists",
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
