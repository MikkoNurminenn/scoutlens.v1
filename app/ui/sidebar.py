"""Sidebar utilities and builders."""

from __future__ import annotations

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
    app_title: str,
    app_tagline: str,
    app_version: str,
    go: Callable[[str], None],
    logout: Callable[[], None],
    inject_css: Callable[[], None] | None = None,
) -> None:
    """Render the application sidebar."""

    root = Path(__file__).resolve().parents[2]

    with st.sidebar:
        st.sidebar.image(str(root / "assets" / "logo.png"), use_container_width=True)
        st.markdown("<div class='scout-brand'>⚽ ScoutLens</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='scout-sub'>{app_tagline}</div>", unsafe_allow_html=True
        )
        st.markdown("<div class='nav-sep'>Navigation</div>", unsafe_allow_html=True)

        st.radio(
            "Navigate",
            options=list(nav_keys),
            index=list(nav_keys).index(current),
            format_func=lambda k: nav_labels.get(k, k),
            key="_nav_radio",
            label_visibility="collapsed",
            on_change=lambda: go(st.session_state["_nav_radio"]),
        )

        theme_options = ["dark", "light"]
        current_theme = st.session_state.get("theme", "dark")
        st.selectbox(
            "Theme",
            options=theme_options,
            index=theme_options.index(current_theme),
            key="theme",
            on_change=inject_css,
        )

        auth = st.session_state.get("auth", {})
        user = auth.get("user")
        if auth.get("authenticated") and user:
            name = user.get("name") or user.get("username", "")
            st.markdown(
                f"<div class='sb-user'>Signed in as {name}</div>",
                unsafe_allow_html=True,
            )
            st.button("Sign out", on_click=logout, type="secondary")

        st.markdown(
            f"<div class='sb-footer'><strong>{app_title}</strong> v{app_version}</div>",
            unsafe_allow_html=True,
        )


__all__ = ["bootstrap_sidebar_auto_collapse", "build_sidebar"]

