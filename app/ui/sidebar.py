# path: app/ui/sidebar.py

from __future__ import annotations

import base64
import json
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Callable, Dict, Iterable, List

import streamlit as st


def bootstrap_sidebar_auto_collapse() -> None:
    """Collapse the sidebar automatically on narrow viewports (throttled)."""
    st.markdown(
        """
        <script>
        (function() {
          const root = window.parent || window;
          if (!root || root.__sl_sb_auto_collapse_init) return;
          root.__sl_sb_auto_collapse_init = true;

          const collapseSel='[data-testid="stSidebarCollapseButton"]';
          const sidebarSel='section[data-testid="stSidebar"]';
          let raf = 0;

          function autoCollapse(){
            const btn = root.document.querySelector(collapseSel);
            const sb  = root.document.querySelector(sidebarSel);
            if(!btn || !sb) return;
            const isExpanded = sb.getAttribute('aria-expanded') !== 'false';
            if (root.innerWidth < 768 && isExpanded) btn.click();
          }
          function onResize(){
            if (raf) cancelAnimationFrame(raf);
            raf = requestAnimationFrame(autoCollapse);
          }
          root.addEventListener('load', autoCollapse, { once: true });
          root.addEventListener('resize', onResize);
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
) -> None:
    """Render the application sidebar with a minimal wrapper structure."""

    root = Path(__file__).resolve().parents[2]
    nav_options: List[str] = list(nav_keys)
    nav_display = {key: nav_labels.get(key, key) for key in nav_options}

    st.markdown(
        """
        <style>
          section[data-testid="stSidebar"]{
            font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          }
          .sb-logo img{
            display:block; margin:0 auto; width:100%; max-width:180px; height:auto; border-radius:18px;
            box-shadow:0 22px 38px rgba(12,20,44,.45);
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <script>
        (function relocateAlerts(){
          const doc = window.parent?.document ?? document;
          const sb = doc.querySelector('section[data-testid="stSidebar"]');
          if (!sb) return;
          const shell = sb.querySelector('.block-container') || sb;
          const footer = sb.querySelector('.sb-footer-line')?.parentElement || shell.lastElementChild || shell;
          const alerts = sb.querySelectorAll('.stAlert');
          if (!alerts.length) return;
          alerts.forEach(alert => {
            const blk = alert.closest('[data-testid="stVerticalBlock"]') || alert;
            if (!blk) return;
            footer?.after(blk);
          });
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

    logo_data_uri = _get_logo_data_uri(str(root / "assets" / "logo.png"))
    tagline_html = f"<div class='sb-tagline'>{escape(app_tagline)}</div>" if app_tagline else ""
    logo_html = (
        f"<div class='sb-logo'><img src=\"{logo_data_uri}\" alt=\"{escape(app_title)} logo\" loading=\"lazy\"/></div>"
        if logo_data_uri
        else ""
    )

    header_html = (
        """
        <div class='sb-header-card'>
          __LOGO__
          <div class='sb-title-block'>
            <div class='sb-title'>__TITLE__</div>
            __TAGLINE__
          </div>
        </div>
        """
        .replace("__LOGO__", logo_html)
        .replace("__TITLE__", escape(app_title))
        .replace("__TAGLINE__", tagline_html)
    )

    with st.sidebar:
        st.markdown(header_html, unsafe_allow_html=True)

        if nav_options:
            st.markdown("<div class='sb-nav-title'>Navigation</div>", unsafe_allow_html=True)
            st.radio(
                "Navigate",
                options=nav_options,
                index=nav_options.index(current) if current in nav_options else 0,
                format_func=lambda key: nav_display.get(key, key),
                key="_nav_radio",
                label_visibility="collapsed",
                on_change=lambda: go(st.session_state["_nav_radio"]),
            )

        if nav_options:
            icon_map = {key: nav_icons.get(key, "") for key in nav_options}
            st.markdown(
                """
                <script>
                (function attachIcons() {
                  const ICON_MAP = __ICON_MAP__;
                  const rootDoc = (window.parent && window.parent.document) ? window.parent.document : document;
                  const labels = rootDoc.querySelectorAll('section[data-testid="stSidebar"] [role="radiogroup"] > label');
                  labels.forEach((label) => {
                    const input = label.querySelector('input');
                    if (!input) return;
                    const icon = ICON_MAP[input.value] || '';
                    if (icon) label.setAttribute('data-icon', icon);
                    else label.removeAttribute('data-icon');
                  });
                })();
                </script>
                """.replace("__ICON_MAP__", json.dumps(icon_map)),
                unsafe_allow_html=True,
            )

        auth = st.session_state.get("auth", {})
        user = auth.get("user")
        if auth.get("authenticated") and user:
            display_name = (
                user.get("name")
                or user.get("username")
                or user.get("user_metadata", {}).get("full_name")
                or user.get("email")
                or "Scout"
            )
            email = user.get("email") or ""
            avatar_url = (
                user.get("user_metadata", {}).get("avatar_url")
                or user.get("avatar_url")
                or ""
            )
            initials = "".join(p[0].upper() for p in display_name.split() if p)[:2] or "SL"
            avatar_classes = "sb-profile-avatar"
            avatar_inner = ""
            if avatar_url:
                avatar_classes += " has-image"
                avatar_inner = (
                    "<img src='{src}' alt='{alt} avatar' loading='lazy'/>".format(
                        src=escape(avatar_url), alt=escape(display_name)
                    )
                )

            profile_html = """
                <div class='sb-profile-card'>
                  <div class='{classes}' data-initials='{initials}'>{inner}</div>
                  <div class='sb-profile-meta'>
                    <div class='sb-profile-name'>{name}</div>
                    {email_line}
                  </div>
                </div>
            """.format(
                classes=avatar_classes,
                initials=escape(initials),
                inner=avatar_inner,
                name=escape(display_name),
                email_line=(f"<div class='sb-profile-email'>{escape(email)}</div>" if email else ""),
            )

            st.markdown(profile_html, unsafe_allow_html=True)
            st.button("Sign out", on_click=logout, type="secondary", key="sidebar-signout")

        footer_html = (
            """
            <div class='sb-footer-line'>
              <span class='sb-footer-title'>{title}</span>
              <span class='sb-version'>v{version}</span>
            </div>
            """.format(title=escape(app_title), version=escape(app_version))
        )
        st.markdown(footer_html, unsafe_allow_html=True)


@lru_cache(maxsize=1)
def _get_logo_data_uri(path_str: str) -> str:
    """Return a base64 data URI for the sidebar logo (empty if missing)."""

    path = Path(path_str)
    if not path.exists():
        return ""

    try:
        data = path.read_bytes()
    except OSError:
        return ""

    mime = "image/png"
    suffix = path.suffix.lower()
    if suffix == ".jpg" or suffix == ".jpeg":
        mime = "image/jpeg"
    elif suffix == ".svg":
        mime = "image/svg+xml"
    elif suffix == ".gif":
        mime = "image/gif"

    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


__all__ = ["bootstrap_sidebar_auto_collapse", "build_sidebar"]
