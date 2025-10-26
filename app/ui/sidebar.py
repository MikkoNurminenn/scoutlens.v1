# path: app/ui/sidebar.py
from __future__ import annotations

import base64
import re
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

import streamlit as st

from app.ui_nav import render_sidebar_nav


# ----------------------------- Public API --------------------------------- #

def bootstrap_sidebar_auto_collapse() -> None:
    """Collapse sidebar on narrow viewports; idempotent & cleaned up."""
    st.markdown(
        """
        <script id="sl-sb-auto-collapse">
        (function(){
          const w = window;
          if (w.__sl_sb_auto_collapse_init) return;
          w.__sl_sb_auto_collapse_init = true;

          function getDoc(){
            try { return (w.parent && w.parent.document) ? w.parent.document : w.document; }
            catch (e) { return w.document; }
          }

          let raf = 0;
          function autoCollapse(){
            const doc = getDoc();
            const btn = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
            const sb  = doc.querySelector('section[data-testid="stSidebar"]');
            if(!btn || !sb) return;
            const attr = sb.getAttribute('aria-expanded');
            const isExpanded = (attr === null) ? true : (attr !== 'false');
            if (w.innerWidth < 768 && isExpanded) { try { btn.click(); } catch(_){} }
          }

          function onResize(){
            if (raf) cancelAnimationFrame(raf);
            raf = requestAnimationFrame(autoCollapse);
          }

          w.addEventListener('load', autoCollapse, { once: true });
          w.addEventListener('resize', onResize, { passive: true });

          w.addEventListener('beforeunload', () => {
            if (raf) cancelAnimationFrame(raf);
            w.removeEventListener('resize', onResize);
          });
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


def build_sidebar(
    *,
    current: str,
    nav_keys: Iterable[str],
    nav_labels: Dict[str, str],
    nav_icons: Dict[str, str],
    app_title: str,
    app_tagline: str,
    app_version: str,
    go: Callable[[str], None],
    logout: Callable[[], None],
    logo_path: Optional[str] = None,
) -> None:
    """Render Streamlit sidebar; single owner; resilient DOM hooks."""
    _force_dark_theme()

    with _sidebar_owner():
        root = Path(__file__).resolve().parents[2]
        logo_path = logo_path or str(root / "assets" / "logo.png")
        logo_data_uri = _get_logo_data_uri(logo_path)

        nav_options: List[str] = list(nav_keys)
        nav_display = {k: nav_labels.get(k, k) for k in nav_options}
        icon_map = {k: nav_icons.get(k, "") for k in nav_options}

        with st.sidebar:
            st.markdown(_build_header_html(app_title, app_tagline, logo_data_uri), unsafe_allow_html=True)

            selected_option: Optional[str] = None
            if nav_options:
                st.markdown(
                    """
                    <div class='sb-nav-title' role='heading' aria-level='2'>
                      <span class='sb-nav-text'>Navigation</span>
                      <span class='sb-nav-underline' aria-hidden='true'></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                try:
                    selected_option = _build_nav(
                        current,
                        nav_options,
                        nav_display,
                        icon_map,
                    )
                except Exception as exc:  # why: surface UI errors from custom nav renderer
                    st.error(f"Failed to render navigation: {exc}")
            else:
                st.info("No navigation sections available.")

            if selected_option and selected_option != current:
                try:
                    go(selected_option)
                except Exception as exc:  # noqa: BLE001
                    st.warning(f"Navigation failed: {exc}")

            auth = st.session_state.get("auth", {})
            user = auth.get("user")
            if auth.get("authenticated") and user:
                st.markdown(_build_profile_html(user), unsafe_allow_html=True)
                st.button(
                    "Sign out",
                    on_click=logout,
                    type="secondary",
                    key="sidebar-signout",
                    use_container_width=True,
                )

            st.markdown(_build_footer_html(app_title, app_version), unsafe_allow_html=True)
            st.markdown(_sidebar_alert_script(), unsafe_allow_html=True)


__all__ = ["bootstrap_sidebar_auto_collapse", "build_sidebar"]


# --------------------------- Internal helpers ------------------------------ #

@contextmanager
def _sidebar_owner():
    """Context manager to mark sidebar owner and restore prior state."""
    prev = bool(st.session_state.get("_sidebar_owner_active"))
    st.session_state["_sidebar_owner_active"] = True
    try:
        yield
    finally:
        st.session_state["_sidebar_owner_active"] = prev


def _force_dark_theme() -> None:
    st.markdown(
        """
        <script id="sl-force-dark">
        (function(){
          const w = window;
          if (w.__slForceDarkApplied) return;
          w.__slForceDarkApplied = true;
          function getDoc(){
            try { return (w.parent && w.parent.document) ? w.parent.document : document; }
            catch (e) { return document; }
          }
          const doc = getDoc();
          if (!doc || !doc.documentElement) return;
          doc.documentElement.dataset.slTheme = 'dark';
          doc.documentElement.style.colorScheme = 'dark';
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


def _build_header_html(title: str, tagline: str, logo_data_uri: str) -> str:
    logo_html = (
        f"<div class='sb-logo'><img src='{logo_data_uri}' alt='{escape(title)} logo' loading='lazy' decoding='async'/></div>"
        if logo_data_uri else ""
    )
    tagline_html = f"<p class='sb-tagline'>{escape(tagline)}</p>" if tagline else ""
    return (
        f"""
        <div class='sb-header-card' role='banner'>
          {logo_html}
          <div class='sb-title-block'>
            <h1 class='sb-title'>{escape(title or "")}</h1>
            {tagline_html}
          </div>
        </div>
        """.strip()
    )


def _build_nav(
    current: str,
    options: List[str],
    display_map: Dict[str, str],
    icon_map: Dict[str, str],
) -> Optional[str]:
    if current in options and st.session_state.get("sidebar_nav") != current:
        st.session_state["sidebar_nav"] = current
    return render_sidebar_nav(
        options,
        state_key="sidebar_nav",
        display_map=display_map,
        icon_map=icon_map,
        heading=None,
        container=nullcontext(),
        rerun_on_click=False,
    )


def _build_profile_html(user: Dict[str, object]) -> str:
    name = (
        str(user.get("name") or "")
        or str(user.get("username") or "")
        or str(user.get("user_metadata", {}).get("full_name") or "")
        or str(user.get("email") or "")
        or "Scout"
    )
    email = str(user.get("email") or "")
    avatar_url = (
        str(user.get("user_metadata", {}).get("avatar_url") or "")
        or str(user.get("avatar_url") or "")
    )
    initials = _compute_initials(name) or "SL"
    avatar_classes = "sb-profile-avatar" + (" has-image" if avatar_url else "")
    avatar_inner = f"<img src='{escape(avatar_url)}' alt='' loading='lazy' decoding='async'/>" if avatar_url else ""
    email_line = f"<div class='sb-profile-email'>{escape(email)}</div>" if email else ""
    return (
        f"""
        <div class='sb-profile-card'>
          <div class='{avatar_classes}' data-initials='{escape(initials)}'>{avatar_inner}</div>
          <div class='sb-profile-meta'>
            <div class='sb-profile-name'>{escape(name)}</div>
            {email_line}
          </div>
        </div>
        """.strip()
    )


def _build_footer_html(title: str, version: str) -> str:
    return (
        f"""
        <footer class='sb-footer-line' aria-label='Application version'>
          <span class='sb-footer-title'>{escape(title or "")}</span>
          <span class='sb-version'>v{escape(version or "")}</span>
        </footer>
        """.strip()
    )


def _sidebar_alert_script() -> str:
    return """
    <script id="sl-sidebar-alert-relocator">
    (function(){
      const w = window;
      function getDoc(){
        try { return (w.parent && w.parent.document) ? w.parent.document : document; }
        catch (e) { return document; }
      }
      function relocate(){
        const doc = getDoc();
        const sidebar = doc && doc.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) return;
        const shell = sidebar.querySelector('.block-container') || sidebar;
        const footerHost = sidebar.querySelector('.sb-footer-line')?.parentElement || shell.lastElementChild || shell;
        const alerts = sidebar.querySelectorAll('.stAlert');
        if (!alerts.length || !footerHost) return;
        alerts.forEach((alert) => {
          const block = alert.closest('[data-testid="stVerticalBlock"]') || alert;
          if (!block || block === footerHost) return;
          footerHost.after(block);
        });
      }
      if (w.__slSidebarAlertInit) { if (typeof w.__slSidebarAlertRelocate === 'function') w.__slSidebarAlertRelocate(); return; }
      w.__slSidebarAlertInit = true;
      w.__slSidebarAlertRelocate = relocate;

      const observer = new MutationObserver(relocate);
      const init = () => {
        const doc = getDoc();
        const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) { setTimeout(init, 160); return; }
        observer.observe(sidebar, { childList: true, subtree: true });
        relocate();
      };
      init();

      w.addEventListener('beforeunload', () => { try { observer.disconnect(); } catch(_){} });
    })();
    </script>
    """


@lru_cache(maxsize=1)
def _get_logo_data_uri(path_str: str, *, max_bytes: int = 5_000_000) -> str:
    """Return a base64 data URI for the sidebar logo (empty if missing/too big)."""
    path = Path(path_str)
    if not path.exists() or not path.is_file():
        return ""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if len(data) > max_bytes:
        return ""  # why: avoid embedding huge assets as data URIs

    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif suffix == ".svg":
        mime = "image/svg+xml"
    elif suffix == ".gif":
        mime = "image/gif"
    else:
        mime = "image/png"

    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


# ----------------------------- Utilities ---------------------------------- #

_INITIALS_RE = re.compile(r"[A-Za-zÅÄÖåäö0-9]", re.UNICODE)

def _compute_initials(name: str, max_len: int = 2) -> str:
    """Extract up to max_len initials from name; locale-agnostic letters/digits."""
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    if not parts:
        return ""
    chars: List[str] = []
    for part in parts:
        m = _INITIALS_RE.search(part)
        if m:
            chars.append(m.group(0).upper())
        if len(chars) >= max_len:
            break
    # fallback: take first characters from first token(s)
    if not chars:
        chars = [c.upper() for c in name[:max_len]]
    return "".join(chars)[:max_len]
