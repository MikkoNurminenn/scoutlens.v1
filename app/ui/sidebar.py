# path: app/ui/sidebar.py
"""Sidebar utilities and builders (Streamlit, accessible, English-only)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Callable, Dict, Iterable

import streamlit as st


def bootstrap_sidebar_auto_collapse() -> None:
    """Collapse the sidebar on narrow viewports; throttle resize."""
    st.markdown(
        """
        <script>
        (function() {
          const root = window.parent || window;
          if (!root || root.__sl_sb_auto_collapse_init) return;
          root.__sl_sb_auto_collapse_init = true;

          const collapseSel = '[data-testid="stSidebarCollapseButton"]';
          const sidebarSel = 'section[data-testid="stSidebar"]';
          const prefersReduced = root.matchMedia && root.matchMedia('(prefers-reduced-motion: reduce)').matches;

          let raf = 0;
          function autoCollapse() {
            const collapseBtn = root.document.querySelector(collapseSel);
            const sidebar = root.document.querySelector(sidebarSel);
            if (!collapseBtn || !sidebar) return;

            const isExpanded = sidebar.getAttribute('aria-expanded') !== 'false';
            const isNarrow = root.innerWidth < 768;
            if (isNarrow && isExpanded) {
              // Why: avoid layout jump storms
              if (prefersReduced) collapseBtn.click();
              else requestAnimationFrame(() => collapseBtn.click());
            }
          }

          function onResize() {
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
    """Render the application sidebar with clear buttons (no radio confusion)."""

    root = Path(__file__).resolve().parents[2]
    nav_options = list(nav_keys)

    # --- Style tokens (kept inline for portability) ---
    st.markdown(
        """
        <style>
          :root{
            --sb-bg:#1b1712; --sb-elev:#221c16; --sb-surface:#2a231c;
            --sb-text:#f4efe8; --sb-dim:#b9b2aa; --sb-border:#3a322a;
            --sb-accent:#5b83ff; --sb-focus:0 0 0 3px rgba(91,131,255,.45);
            --sb-radius:14px; --sb-gap:12px;
          }
          .sidebar-shell{padding:18px;background:
            linear-gradient(180deg,var(--sb-elev),var(--sb-surface) 60%,var(--sb-elev));
            color:var(--sb-text);}
          .sidebar-header{display:flex;gap:12px;align-items:center;margin-bottom:8px}
          .sidebar-logo img{border-radius:12px}
          .scout-brand{font-size:22px;letter-spacing:.08em;margin:0 0 2px}
          .scout-sub{color:var(--sb-dim);font-size:12px;margin-top:2px}
          .sidebar-title{display:flex;flex-direction:column}
          .sidebar-nav{margin-top:12px}
          .nav-title{text-transform:uppercase;letter-spacing:.2em;font-size:11px;color:var(--sb-dim);margin:0 0 10px 4px}
          .nav-group{display:flex;flex-direction:column;gap:10px}
          .sl-nav-btn button{
            width:100%; display:flex; align-items:center; gap:10px; justify-content:flex-start;
          }
          .sl-nav-btn.is-current button{
            border-color: rgba(91,131,255,.55) !important;
            box-shadow: 0 6px 18px rgba(0,0,0,.35);
          }
          .sl-nav-icon{opacity:.9}
          .sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
          .sidebar-profile-card{display:flex;gap:10px;align-items:center;margin-top:16px}
          .profile-avatar{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:#3b3027;color:#fff;font-weight:600}
          .profile-avatar.has-image{background:transparent;overflow:hidden}
          .profile-avatar img{width:100%;height:100%;object-fit:cover}
          .profile-meta{display:flex;flex-direction:column}
          .profile-name{font-weight:600}
          .profile-email{color:var(--sb-dim);font-size:12px}
          .sidebar-signout button{width:100%}
          .sb-footer{display:flex;justify-content:space-between;align-items:center;margin-top:18px;color:var(--sb-dim);font-size:12px}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("<div class='sidebar-shell'>", unsafe_allow_html=True)

        # --- Header / brand ---
        st.markdown("<div class='sidebar-header'>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-logo'>", unsafe_allow_html=True)
        st.image(str(root / "assets" / "logo.png"), use_column_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        tagline_html = (
            f"<div class='scout-sub'>{escape(app_tagline)}</div>" if app_tagline else ""
        )
        st.markdown(
            f"""
            <div class='sidebar-title'>
              <div class='scout-brand'>{escape(app_title)}</div>
              {tagline_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # --- Navigation (buttons, no radio) ---
        st.markdown("<div class='sidebar-nav'>", unsafe_allow_html=True)
        st.markdown("<div class='nav-title'>Navigation</div>", unsafe_allow_html=True)
        st.markdown("<div class='nav-group'>", unsafe_allow_html=True)

        for key in nav_options:
            label = nav_labels.get(key, key)
            icon = nav_icons.get(key, "")  # e.g., "📄" or "🔍"
            is_current = key == current

            # Why: disabled button visually indicates current page without causing a rerun loop.
            btn = st.button(
                f"{icon}  {label}" if icon else label,
                key=f"nav-btn-{key}",
                type="primary" if is_current else "secondary",
                disabled=is_current,
                help="Current page" if is_current else f"Go to {label}",
            )
            st.markdown(
                f"<span class='sr-only' aria-current='page'>{'yes' if is_current else ''}</span>",
                unsafe_allow_html=True,
            )
            if btn and not is_current:
                go(key)

            # Attach a class for current styling polish.
            st.markdown(
                f"""
                <script>
                (function(){{
                  const root = (window.parent && window.parent.document) ? window.parent.document : document;
                  const el = root.querySelector('[data-testid="baseButton-secondary"][aria-label="{escape(label)}"]')
                           || root.querySelector('button[kind][data-testid="{escape('nav-btn-' + key)}"]');
                  const cont = root.querySelector('[data-testid="stSidebar"]');
                  if (!cont) return;
                  const slots = cont.querySelectorAll('button[data-testid="{escape('nav-btn-' + key)}"]');
                }})();
                </script>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)  # .nav-group
        st.markdown("</div>", unsafe_allow_html=True)  # .sidebar-nav

        # --- Profile (English labels kept) ---
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
            initials = "".join(part[0].upper() for part in display_name.split() if part)[:2] or "SL"

            avatar_classes = "profile-avatar"
            avatar_inner = ""
            if avatar_url:
                avatar_classes += " has-image"
                avatar_inner = (
                    "<img src='{src}' alt='{alt} avatar' loading='lazy'/>".format(
                        src=escape(avatar_url), alt=escape(display_name)
                    )
                )

            st.markdown(
                """
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
                ),
                unsafe_allow_html=True,
            )
            st.markdown("<div class='sidebar-signout'>", unsafe_allow_html=True)
            st.button("Sign out", on_click=logout, type="secondary", key="sidebar-signout")
            st.markdown("</div>", unsafe_allow_html=True)

        # --- Footer ---
        st.markdown(
            """
            <div class='sb-footer'>
              <span class='sb-footer-title'>{title}</span>
              <span class='sb-version'>v{version}</span>
            </div>
            """.format(title=escape(app_title), version=escape(app_version)),
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)  # .sidebar-shell


__all__ = ["bootstrap_sidebar_auto_collapse", "build_sidebar"]
