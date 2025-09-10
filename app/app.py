# app/app.py
from __future__ import annotations
from pathlib import Path
import importlib
import sys
import traceback
import streamlit as st

# --- Robust ROOT/path bootstrap ------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent  # projektin juuri
PKG_DIR = ROOT / "app"                         # pakettihakemisto

# Miksi: Streamlitin käynnistyspolku vaihtelee; varmistetaan projektijuuri sys.pathissa.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Miksi: jos kansiot eivät ole paketteja, importit kaatuvat riippumatta sys.pathista.
# Luo tyhjä __init__.py jos puuttuu (turvallista myös olemassaolevalle tiedostolle).
for pkg in [PKG_DIR]:
    init_py = pkg / "__init__.py"
    if not init_py.exists():
        try:
            init_py.write_text("# package marker\n", encoding="utf-8")
        except Exception:
            # Lukuoikeudet Cloudissa voivat estää kirjoituksen; jatketaan silti diagnostiikalla.
            pass

# Invalidoi importtikäyttövälimuisti siltä varalta, että rakenteet juuri kirjoitettiin.
importlib.invalidate_caches()

# --- Yksittäiset importit diagnostiikalla -------------------------------------
def _fail_hard(context: str, err: BaseException) -> None:
    st.error(f"ImportError {context}: {type(err).__name__}: {err}")
    # Näytä hyödylliset tiedot debugiin ilman arkaluontoista dataa
    st.code(
        "Debug info:\n"
        f"ROOT={ROOT}\n"
        f"PKG_DIR exists={PKG_DIR.exists()} files={', '.join(sorted(p.name for p in PKG_DIR.glob('*')))}\n"
        f"sys.path[0:3]={sys.path[:3]}\n"
        f"Traceback:\n{''.join(traceback.format_exception(type(err), err, err.__traceback__))}"
    )
    st.stop()

try:
    from app.ui import bootstrap_sidebar_auto_collapse
except Exception as e:
    _fail_hard("while importing app.ui.bootstrap_sidebar_auto_collapse", e)

st.set_page_config(page_title="ScoutLens", layout="wide", initial_sidebar_state="expanded")
bootstrap_sidebar_auto_collapse()

# Sivukohtaiset importit – tee nämä erikseen, jotta näemme mikä kaatuu
try:
    from app.reports_page import show_reports_page
except Exception as e:
    _fail_hard("while importing app.reports_page.show_reports_page", e)

try:
    from app.inspect_player import show_inspect_player
except Exception as e:
    _fail_hard("while importing app.inspect_player.show_inspect_player", e)

try:
    from app.shortlists_page import show_shortlists_page
except Exception as e:
    _fail_hard("while importing app.shortlists_page.show_shortlists_page", e)

try:
    from app.export_page import show_export_page
except Exception as e:
    _fail_hard("while importing app.export_page.show_export_page", e)

try:
    from app.login import login
except Exception as e:
    _fail_hard("while importing app.login.login", e)

APP_TITLE   = "ScoutLens"
APP_TAGLINE = "LATAM scouting toolkit"
APP_VERSION = "0.9.1"

# --------- Global CSS injection ----------
def inject_css():
    styles_dir = ROOT / "app" / "styles"
    parts = []
    for name in ["tokens.css", "layout.css", "components.css", "sidebar.css", "animations.css"]:
        p = styles_dir / name
        if p.exists():
            parts.append(p.read_text(encoding="utf-8"))
    if parts:
        st.markdown(f"<style>{'\n'.join(parts)}</style>", unsafe_allow_html=True)

# --------- Navigation setup ----------
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
LEGACY_REMAP = {
    "home": "Reports",
    "team_view": "Reports",
    "scout_reporter": "Reports",
    "shortlists": "Shortlists",
    "player_editor": "Shortlists",
}

def _sync_query(page: str) -> None:
    try:
        # Aseta koko mapping kerralla (vähentää versioriippuvuutta)
        st.query_params = {"p": page}
    except Exception:
        pass

def main() -> None:
    inject_css()
    login()

    # Init from URL once
    if "nav_page" not in st.session_state:
        p = st.query_params.get("p", None)
        p = LEGACY_REMAP.get(p, p)
        st.session_state["nav_page"] = p if p in NAV_KEYS else NAV_KEYS[0]
        _sync_query(st.session_state["nav_page"])

    current_page = st.session_state.get("nav_page", NAV_KEYS[0])
    current_page = LEGACY_REMAP.get(current_page, current_page)
    if current_page not in NAV_KEYS:
        current_page = NAV_KEYS[0]
        st.session_state["nav_page"] = current_page

    if "_prev_nav" not in st.session_state:
        st.session_state["_prev_nav"] = current_page

    desired_label = NAV_LABELS.get(current_page, NAV_LABELS[NAV_KEYS[0]])
    if st.session_state.get("nav_choice") != desired_label:
        st.session_state["nav_choice"] = desired_label

    # Sidebar
    with st.sidebar:
        st.markdown("<div class='scout-brand'>⚽ ScoutLens</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='scout-sub'>{APP_TAGLINE}</div>", unsafe_allow_html=True)
        st.markdown("<div class='nav-sep'>Navigation</div>", unsafe_allow_html=True)

        selection = st.radio(
            "Navigate",
            options=LABEL_LIST,
            key="nav_choice",
            label_visibility="collapsed",
        )

        st.markdown(
            f"<div class='sb-footer'><strong>{APP_TITLE}</strong> v{APP_VERSION}</div>",
            unsafe_allow_html=True
        )

    page = LABEL_TO_KEY.get(selection, NAV_KEYS[0])
    prev = st.session_state.get("_prev_nav")
    if prev != page:
        st.session_state["_prev_nav"] = page
        st.session_state["_collapse_sidebar"] = True
        st.session_state["nav_page"] = page
        _sync_query(page)
        st.stop()

    current_page = st.session_state.get("nav_page", NAV_KEYS[0])
    PAGE_FUNCS.get(current_page, lambda: st.error("Page not found."))()

if __name__ == "__main__":
    main()
