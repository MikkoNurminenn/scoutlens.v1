# -*- coding: utf-8 -*-
# file: app/app.py
from __future__ import annotations
from pathlib import Path
import re
import importlib
import importlib.util
import sys
import traceback
import streamlit as st

# Kun Streamlit suorittaa tämän tiedoston "app/app.py" suoraan, Python saattaa
# rekisteröidä väliaikaisen moduulin nimeltä "app" ilman __path__-attribuuttia.
# Poistetaan se heti, jotta myöhemmät "from app.…" -importit eivät kaadu
# virheilmoitukseen "'app' is not a package".
_existing_app_mod = sys.modules.get("app")
if _existing_app_mod is not None and not getattr(_existing_app_mod, "__path__", None):
    del sys.modules["app"]


def _install_sidebar_guard() -> None:
    """Wrap ``st.sidebar`` so accidental writes outside ``build_sidebar`` get logged."""

    original_sidebar = st.sidebar

    if getattr(original_sidebar, "_sl_guard_installed", False):
        return

    def _log_violation(action: str) -> None:
        store = st.session_state.setdefault("_sidebar_guard", {"violations": []})
        message = f"{action} (outside build_sidebar)"
        if message not in store["violations"]:
            store["violations"].append(message)
            store.pop("notified", None)
            print(f"[ScoutLens] Sidebar guard: {message}")

    class _SidebarProxy:
        """Proxy that mirrors ``DeltaGenerator`` but records misuse."""

        __slots__ = ("_target",)

        def __init__(self, target):
            self._target = target

        def _active(self) -> bool:
            return bool(st.session_state.get("_sidebar_owner_active"))

        def __getattr__(self, name):  # noqa: D401 - proxy helper
            attr = getattr(self._target, name)
            if callable(attr):

                def wrapped(*args, **kwargs):
                    if not self._active():
                        _log_violation(f"st.sidebar.{name}")
                    return attr(*args, **kwargs)

                return wrapped
            return attr

        def __call__(self, *args, **kwargs):
            if not self._active():
                _log_violation("st.sidebar(...)")
            return self._target(*args, **kwargs)

        def __enter__(self):
            if not self._active():
                _log_violation("with st.sidebar")
            return self._target.__enter__()

        def __exit__(self, exc_type, exc, tb):
            return self._target.__exit__(exc_type, exc, tb)

    proxy = _SidebarProxy(original_sidebar)
    setattr(proxy, "_sl_guard_installed", True)
    st.sidebar = proxy  # type: ignore[assignment]


# --- Polkutarkistus + sys.path varmistus ---
try:
    from app.utils.paths import ensure_project_paths, assert_app_paths
except Exception:
    # Fallback jos polut eivät vielä toimi
    import sys as _sys
    from pathlib import Path as _Path

    _root = _Path(__file__).resolve().parent.parent
    for _cand in (str(_root), str(_root / "app")):
        if _cand not in _sys.path:
            _sys.path.append(_cand)
    _cached_app = _sys.modules.get("app")
    if _cached_app is not None and not getattr(_cached_app, "__path__", None):
        del _sys.modules["app"]

    from app.utils.paths import ensure_project_paths, assert_app_paths

ROOT = ensure_project_paths()
paths_ok = assert_app_paths()
PKG_DIR = ROOT / "app"

_install_sidebar_guard()

importlib.invalidate_caches()

# ---- Import resolver guard (avoid 3rd‑party package named "app")
_spec = importlib.util.find_spec("app")
_spec_has_location = False
if _spec is not None:
    origin = getattr(_spec, "origin", None)
    search_locations = getattr(_spec, "submodule_search_locations", None)
    _spec_has_location = bool(origin or search_locations)
if not _spec or not _spec_has_location:
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
bootstrap_global_ui = importlib.import_module("app.ui.bootstrap").__getattribute__(
    "bootstrap_global_ui"
)
set_sidebar_background = importlib.import_module("app.ui.sidebar_bg").__getattribute__(
    "set_sidebar_background"
)
build_sidebar = importlib.import_module("app.ui.sidebar").__getattribute__(
    "build_sidebar"
)
render_sidebar_toggle = importlib.import_module("app.ui.sidebar_toggle").__getattribute__(
    "render_sidebar_toggle"
)
apply_theme = importlib.import_module("app.theme.codex_theme").__getattribute__(
    "apply_theme"
)
ensure_fontawesome = importlib.import_module("app.ui.icon_pack").__getattribute__(
    "ensure_fontawesome"
)
try:
    improve_collapsed_toggle_visibility = importlib.import_module(
        "app.ui.sidebar_toggle_css"
    ).__getattribute__(
        "improve_collapsed_toggle_visibility"
    )
except Exception as e:
    st.error(f"Import error: app.ui.sidebar_toggle_css ({e}). Check package files.")
    raise

st.set_page_config(page_title="Main", layout="wide", initial_sidebar_state="expanded")
bootstrap_global_ui()
apply_theme()
ensure_fontawesome()
improve_collapsed_toggle_visibility()
render_sidebar_toggle()

if not paths_ok.get("css_file_exists", True):
    st.warning(f"CSS file not found at {paths_ok.get('css_file_path')}. Check paths.")


def inject_css(path: str) -> None:
    css_path = Path(path)
    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


inject_css("app/styles/nav.css")

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
show_calendar_page = _safe_import("calendar page", "app.calendar_page", "show_calendar_page")
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

def inject_theme_css():
    styles_dir = ROOT / "app" / "styles"
    token_file = "tokens_dark.css"
    css_imports = []
    css_blocks = []
    for name in [
        token_file,
        "layout.css",
        "components.css",
        "sidebar.css",
        "animations.css",
    ]:
        p = styles_dir / name
        if p.exists():
            text = p.read_text(encoding="utf-8")
            imports = re.findall(r"@import[^;]+;", text)
            if imports:
                css_imports.extend(imports)
                text = re.sub(r"@import[^;]+;", "", text)
            css_blocks.append(text.strip())
    # remove previously injected theme blocks if present
    st.markdown(
        "<script>['sl-theme','sl-theme-imports'].forEach(id=>{const el=document.getElementById(id); if(el) el.remove();});</script>",
        unsafe_allow_html=True,
    )
    if css_imports:
        st.markdown(
            f"<style id='sl-theme-imports'>{'\n'.join(css_imports)}</style>",
            unsafe_allow_html=True,
        )
    css_body = "\n".join(block for block in css_blocks if block)
    if css_body:
        st.markdown(
            f"<style id='sl-theme'>{css_body}</style>",
            unsafe_allow_html=True,
        )

def _render_sidebar_guard_report() -> None:
    guard = st.session_state.get("_sidebar_guard")
    if not guard:
        return
    violations = guard.get("violations", [])
    if not violations or guard.get("notified"):
        return

    st.warning(
        "Sidebar guard detected direct ``st.sidebar`` usage outside ``build_sidebar``."
        " Please route sidebar content through ``build_sidebar`` instead.",
        icon="⚠️",
    )
    st.code("\n".join(violations))
    guard["notified"] = True



# --------- Nav
NAV_KEYS = [
    "Reports",
    "Calendar",
    "Inspect Player",
    "Shortlists",
    "Manage Shortlists",
    "Players",
    "Notes",
    "Export",
]
NAV_LABELS = {
    "Reports": "Reports",
    "Calendar": "Calendar",
    "Inspect Player": "Inspect Player",
    "Shortlists": "Shortlists",
    "Manage Shortlists": "Manage Shortlists",
    "Players": "Players",
    "Notes": "Quick notes",
    "Export": "Export",
}
NAV_ICONS = {
    "Reports": "",
    "Calendar": "",
    "Inspect Player": "",
    "Shortlists": "",
    "Manage Shortlists": "",
    "Players": "",
    "Notes": "",
    "Export": "",
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
    "Calendar": show_calendar_page,
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
        nav_icons=NAV_ICONS,
        app_title=APP_TITLE,
        app_tagline=APP_TAGLINE,
        app_version=APP_VERSION,
        go=go,
        logout=logout,
    )

    inject_theme_css()
    set_sidebar_background()

    page_func = PAGE_FUNCS.get(current, lambda: st.error("Page not found."))
    with track(f"page:{current}"):
        page_func()
    render_perf()
    _render_sidebar_guard_report()


if __name__ == "__main__":
    main()
