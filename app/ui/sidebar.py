"""Sidebar utilities and builders."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Callable, Dict, Iterable

import streamlit as st


def bootstrap_sidebar_auto_collapse() -> None:
    """Collapse the sidebar automatically on narrow viewports."""
    st.markdown(
        """
        <script>
        (function() {
          const collapseBtn = window.parent.document.querySelector(
            '[data-testid="stSidebarCollapseButton"]'
          );
          function autoCollapse() {
            if (window.innerWidth < 768 && collapseBtn) {
              collapseBtn.click();
            }
          }
          window.addEventListener('load', autoCollapse);
          window.addEventListener('resize', autoCollapse);
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
    """Render the application sidebar."""

    root = Path(__file__).resolve().parents[2]

    with st.sidebar:
        nav_options = list(nav_keys)
        nav_display = {key: nav_labels.get(key, key) for key in nav_options}

        st.markdown("<div class='sidebar-shell'>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-header'>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-logo'>", unsafe_allow_html=True)
        st.image(str(root / "assets" / "logo.png"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        tagline_html = (
            f"<div class='scout-sub'>{escape(app_tagline)}</div>" if app_tagline else ""
        )
        st.markdown(
            """
            <div class='sidebar-title'>
              <div class='scout-brand'>{title}</div>
              {tagline}
            </div>
            """.format(title=escape(app_title), tagline=tagline_html),
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='sidebar-nav'>", unsafe_allow_html=True)
        st.markdown("<div class='nav-title'>Navigation</div>", unsafe_allow_html=True)

        st.radio(
            "Navigate",
            options=nav_options,
            index=nav_options.index(current) if current in nav_options else 0,
            format_func=lambda key: nav_display.get(key, key),
            key="_nav_radio",
            label_visibility="collapsed",
            on_change=lambda: go(st.session_state["_nav_radio"]),
        )
        st.markdown("</div>", unsafe_allow_html=True)

        icon_map = {key: nav_icons.get(key, "") for key in nav_options}
        st.markdown(
            """
            <script>
            (function() {
              const ICON_MAP = {icon_map};
              const rootDoc = (window.parent && window.parent.document) ? window.parent.document : document;
              if (!rootDoc) {{
                return;
              }}
              const labels = rootDoc.querySelectorAll('section[data-testid="stSidebar"] [role="radiogroup"] > label');
              labels.forEach((label) => {{
                const input = label.querySelector('input');
                if (!input) {{
                  return;
                }}
                const icon = ICON_MAP[input.value] || '';
                if (icon) {{
                  label.setAttribute('data-icon', icon);
                }} else {{
                  label.removeAttribute('data-icon');
                }}
              }});
            })();
            </script>
            """.format(icon_map=json.dumps(icon_map)),
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
            initials = "".join(part[0].upper() for part in display_name.split() if part)[:2]
            initials = initials or "SL"

            avatar_classes = "profile-avatar"
            avatar_inner = ""
            if avatar_url:
                avatar_classes += " has-image"
                avatar_inner = (
                    "<img src='{src}' alt='{alt} avatar' loading='lazy'/>".format(
                        src=escape(avatar_url), alt=escape(display_name)
                    )
                )

            profile_html = """
            <div class='sidebar-profile-card'>
              <div class='{classes}' data-initials='{initials}'>{inner}</div>
              <div class='profile-meta'>
                <div class='profile-name'>{name}</div>
                {email_line}
              </div>
            </div>
            """.format(
                classes=avatar_classes,
                initials=escape(initials),
                inner=avatar_inner,
                name=escape(display_name),
                email_line=(
                    f"<div class='profile-email'>{escape(email)}</div>" if email else ""
                ),
            )
            st.markdown(profile_html, unsafe_allow_html=True)
            st.markdown("<div class='sidebar-signout'>", unsafe_allow_html=True)
            st.button("Sign out", on_click=logout, type="secondary", key="sidebar-signout")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class='sb-footer'>
              <span class='sb-footer-title'>{title}</span>
              <span class='sb-version'>v{version}</span>
            </div>
            """.format(title=escape(app_title), version=escape(app_version)),
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


__all__ = ["bootstrap_sidebar_auto_collapse", "build_sidebar"]

