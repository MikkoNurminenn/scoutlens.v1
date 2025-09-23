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
    """Collapse sidebar on narrow viewports; safe against cross-origin and cleans up."""
    st.markdown(
        """
        <script>
        (function() {
          // Guard against multiple inits
          const w = window;
          if (w.__sl_sb_auto_collapse_init) return;
          w.__sl_sb_auto_collapse_init = true;

          // Safe parent document access
          function getDoc() {
            try {
              return (w.parent && w.parent.document) ? w.parent.document : w.document;
            } catch (e) {
              return w.document; // cross-origin fallback
            }
          }

          let raf = 0;

          function autoCollapse(){
            const doc = getDoc();
            const btn = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
            const sb  = doc.querySelector('section[data-testid="stSidebar"]');
            if(!btn || !sb) return;
            const attr = sb.getAttribute('aria-expanded');
            const isExpanded = (attr === null) ? true : (attr !== 'false');
            if (w.innerWidth < 768 && isExpanded) btn.click();
          }

          function onResize(){
            if (raf) cancelAnimationFrame(raf);
            raf = requestAnimationFrame(autoCollapse);
          }

          // Init + cleanup
          w.addEventListener('load', autoCollapse, { once: true });
          w.addEventListener('resize', onResize);

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
          .sb-nav-icon{ margin-left:auto; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Safened alert relocation (no-op if elements missing or cross-origin)
    st.markdown(
        """
        <script>
        (function relocateAlerts(){
          function getDoc(){
            try { return (window.parent && window.parent.document) ? window.parent.document : document; }
            catch(e){ return document; }
          }
          const doc = getDoc();
          const sb = doc.querySelector('section[data-testid="stSidebar"]');
          if (!sb) return;
          const shell = sb.querySelector('.block-container') || sb;
          const footer = sb.querySelector('.sb-footer-line')?.parentElement || shell.lastElementChild || shell;
          const alerts = sb.querySelectorAll('.stAlert');
          if (!alerts.length) return;
          alerts.forEach(alert => {
            const blk = alert.closest('[data-testid="stVerticalBlock"]') || alert;
            if (blk && footer) footer.after(blk);
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
        .replace("__TITLE__", escape(app_title or ""))
        .replace("__TAGLINE__", tagline_html)
    )

    with st.sidebar:
        st.markdown(header_html, unsafe_allow_html=True)

        if nav_options:
            st.markdown(
                """
                <div class='sb-nav-title'>
                  <span class='sb-nav-text'>Navigation</span>
                  <span class='sb-nav-underline' aria-hidden='true'></span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.radio(
                "Navigate",
                options=nav_options,
                index=nav_options.index(current) if current in nav_options else 0,
                format_func=lambda key: nav_display.get(key, key),
                key="_nav_radio",
                label_visibility="collapsed",
                on_change=lambda: go(st.session_state.get("_nav_radio", nav_options[0] if nav_options else "")),
            )

        if nav_options:
            icon_map = {key: nav_icons.get(key, "") for key in nav_options}
            # ensure_ascii=False keeps emoji/codepoints readable in JS
            st.markdown(
                """
                <script>
                (function attachIcons() {
                  function getDoc(){
                    try { return (window.parent && window.parent.document) ? window.parent.document : document; }
                    catch(e){ return document; }
                  }
                  const ICON_MAP = __ICON_MAP__;
                  const rootDoc = getDoc();

                  function applyIcons() {
                    const container = rootDoc.querySelector('section[data-testid="stSidebar"]');
                    if (!container) return;
                    const group = container.querySelector('[role="radiogroup"]');
                    if (!group) return;
                    const labels = group.querySelectorAll(':scope > label');
                    labels.forEach((label) => {
                      const input = label.querySelector('input');
                      if (!input) return;
                      const iconChar = ICON_MAP[input.value] || '';
                      let iconSpan = label.querySelector('.sb-nav-icon');

                      if (!iconChar) {
                        if (iconSpan) iconSpan.remove();
                      } else {
                        if (!iconSpan) {
                          iconSpan = rootDoc.createElement('span');
                          iconSpan.className = 'sb-nav-icon';
                          iconSpan.setAttribute('aria-hidden', 'true'); // decorative
                          // push to end for consistent layout
                          label.appendChild(iconSpan);
                        }
                        iconSpan.textContent = iconChar;
                      }

                      label.classList.add('sb-nav-item');
                      label.dataset.option = input.value;
                      label.dataset.active = input.checked ? 'true' : 'false';

                      const textBlock = label.querySelector(':scope > div:last-child');
                      if (textBlock && !textBlock.classList.contains('sb-nav-label')) {
                        textBlock.classList.add('sb-nav-label');
                      }
                    });
                  }

                  // Initial pass
                  applyIcons();

                  // Observe sidebar changes (Streamlit re-renders)
                  const observer = new MutationObserver(() => applyIcons());
                  function observeSidebar() {
                    const container = rootDoc.querySelector('section[data-testid="stSidebar"]');
                    if (!container) {
                      setTimeout(observeSidebar, 120);
                      return;
                    }
                    observer.observe(container, { childList: true, subtree: true });
                  }
                  observeSidebar();

                  // Cleanup on unload to avoid leaks
                  window.addEventListener('beforeunload', () => {
                    try { observer.disconnect(); } catch(e) {}
                  });
                })();
                </script>
                """.replace("__ICON_MAP__", json.dumps(icon_map, ensure_ascii=False)),
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
            # type="secondary" is valid in recent Streamlit; safe default if older
            st.button("Sign out", on_click=logout, type="secondary", key="sidebar-signout")

        footer_html = (
            """
            <div class='sb-footer-line'>
              <span class='sb-footer-title'>{title}</span>
              <span class='sb-version'>v{version}</span>
            </div>
            """.format(title=escape(app_title or ""), version=escape(app_version or ""))
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
    # Minimal type sniffing by extension
    mime = "image/png"
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif suffix == ".svg":
        mime = "image/svg+xml"
    elif suffix == ".gif":
        mime = "image/gif"

    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


__all__ = ["bootstrap_sidebar_auto_collapse", "build_sidebar"]
