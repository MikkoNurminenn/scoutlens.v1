# path: app/ui/sidebar.py

from __future__ import annotations

import base64
import json
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

import streamlit as st


def bootstrap_sidebar_auto_collapse() -> None:
    """Collapse sidebar on narrow viewports; safe against cross-origin and cleans up."""
    st.markdown(
        """
        <script>
        (function() {
          const w = window;
          if (w.__sl_sb_auto_collapse_init) return;
          w.__sl_sb_auto_collapse_init = true;

          function getDoc() {
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
            if (w.innerWidth < 768 && isExpanded) btn.click();
          }

          function onResize(){
            if (raf) cancelAnimationFrame(raf);
            raf = requestAnimationFrame(autoCollapse);
          }

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
    logo_path: Optional[str] = None,
) -> None:
    """Render the Streamlit sidebar using a single, accessible owner."""

    root = Path(__file__).resolve().parents[2]
    nav_options: List[str] = list(nav_keys)
    nav_display = {key: nav_labels.get(key, key) for key in nav_options}
    icon_map = {key: nav_icons.get(key, "") for key in nav_options}

    _force_dark_theme()

    previous_state = bool(st.session_state.get("_sidebar_owner_active"))
    st.session_state["_sidebar_owner_active"] = True

    if not logo_path:
        logo_path = str(root / "assets" / "logo.png")

    logo_data_uri = _get_logo_data_uri(logo_path)
    logo_html = (
        f"<div class='sb-logo'><img src='{logo_data_uri}' alt='{escape(app_title)} logo' "
        "loading='lazy' decoding='async'/></div>"
        if logo_data_uri
        else ""
    )
    tagline_html = f"<p class='sb-tagline'>{escape(app_tagline)}</p>" if app_tagline else ""

    header_html = (
        """
        <div class='sb-header-card' role='banner'>
          {logo}
          <div class='sb-title-block'>
            <h1 class='sb-title'>{title}</h1>
            {tagline}
          </div>
        </div>
        """
        .format(
            logo=logo_html,
            title=escape(app_title or ""),
            tagline=tagline_html,
        )
        .strip()
    )

    try:
        with st.sidebar:
            st.markdown(header_html, unsafe_allow_html=True)

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
                selected_option = st.radio(
                    "Navigate",
                    options=nav_options,
                    index=nav_options.index(current) if current in nav_options else 0,
                    format_func=lambda key: nav_display.get(key, key),
                    key="sidebar_nav",
                    label_visibility="collapsed",
                )

            if selected_option and selected_option != current:
                go(selected_option)

            st.markdown(_nav_behavior_script(icon_map), unsafe_allow_html=True)

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
                avatar_classes = "sb-profile-avatar" + (" has-image" if avatar_url else "")
                avatar_inner = (
                    "<img src='{src}' alt='' loading='lazy' decoding='async'/>".format(
                        src=escape(avatar_url)
                    )
                    if avatar_url
                    else ""
                )
                profile_html = (
                    """
                    <div class='sb-profile-card'>
                      <div class='{classes}' data-initials='{initials}'>{inner}</div>
                      <div class='sb-profile-meta'>
                        <div class='sb-profile-name'>{name}</div>
                        {email_line}
                      </div>
                    </div>
                    """
                    .format(
                        classes=avatar_classes,
                        initials=escape(initials),
                        inner=avatar_inner,
                        name=escape(display_name),
                        email_line=(
                            f"<div class='sb-profile-email'>{escape(email)}</div>" if email else ""
                        ),
                    )
                    .strip()
                )
                st.markdown(profile_html, unsafe_allow_html=True)
                st.button(
                    "Sign out",
                    on_click=logout,
                    type="secondary",
                    key="sidebar-signout",
                    use_container_width=True,
                )

            footer_html = (
                """
                <footer class='sb-footer-line' aria-label='Application version'>
                  <span class='sb-footer-title'>{title}</span>
                  <span class='sb-version'>v{version}</span>
                </footer>
                """
                .format(
                    title=escape(app_title or ""),
                    version=escape(app_version or ""),
                )
                .strip()
            )
            st.markdown(footer_html, unsafe_allow_html=True)
            st.markdown(_sidebar_alert_script(), unsafe_allow_html=True)
    finally:
        st.session_state["_sidebar_owner_active"] = previous_state


def _force_dark_theme() -> None:
    st.markdown(
        """
        <script id="sl-force-dark">
        (function forceDark(){
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


def _nav_behavior_script(icon_map: Dict[str, str]) -> str:
    icon_payload = json.dumps(icon_map, ensure_ascii=False)
    return """
    <script>
    (function sidebarNavEnhancer(){
      const ICON_MAP = __ICON_MAP__;
      const w = window;
      function getDoc(){
        try { return (w.parent && w.parent.document) ? w.parent.document : document; }
        catch (e) { return document; }
      }
      function syncNav(){
        const doc = getDoc();
        if (!doc) return;
        const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) return;
        const group = sidebar.querySelector('[role="radiogroup"]');
        if (!group) return;
        group.setAttribute('aria-label', 'Primary navigation');
        group.dataset.owner = 'scoutlens';
        const labels = group.querySelectorAll(':scope > label');
        labels.forEach((label) => {
          const input = label.querySelector('input');
          if (!input) return;
          const value = input.value;
          const spec = ICON_MAP[value] || '';
          let iconSpan = label.querySelector('.sb-nav-icon');
          if (spec) {
            if (!iconSpan) {
              iconSpan = doc.createElement('span');
              iconSpan.className = 'sb-nav-icon';
              iconSpan.setAttribute('aria-hidden', 'true');
              iconSpan.setAttribute('role', 'presentation');
              input.insertAdjacentElement('afterend', iconSpan);
            }
            if (/\\bfa-/.test(spec)) {
              iconSpan.innerHTML = '<i class="' + spec + '"></i>';
            } else {
              iconSpan.textContent = spec;
            }
          } else if (iconSpan) {
            iconSpan.remove();
            iconSpan = null;
          }
          const isActive = input.checked;
          label.dataset.option = value;
          label.dataset.active = isActive ? 'true' : 'false';
          label.setAttribute('aria-current', isActive ? 'page' : 'false');
          label.classList.add('sb-nav-item');
          const textWrap = label.querySelector(':scope > div:last-child');
          if (textWrap && !textWrap.classList.contains('sb-nav-label')) {
            textWrap.classList.add('sb-nav-label');
          }
        });
      }
      w.__slSidebarIconMap = ICON_MAP;
      w.__slSidebarNavSync = syncNav;
      if (!w.__slSidebarNavObserver) {
        const observer = new MutationObserver(() => {
          if (typeof w.__slSidebarNavSync === 'function') {
            w.__slSidebarNavSync();
          }
        });
        w.__slSidebarNavObserver = observer;
        const init = () => {
          const doc = getDoc();
          const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
          if (!sidebar) {
            setTimeout(init, 150);
            return;
          }
          observer.observe(sidebar, { childList: true, subtree: true });
          if (typeof w.__slSidebarNavSync === 'function') {
            w.__slSidebarNavSync();
          }
        };
        init();
        w.addEventListener('beforeunload', () => {
          try { observer.disconnect(); } catch (e) {}
          if (w.__slSidebarNavObserver === observer) {
            w.__slSidebarNavObserver = null;
          }
        });
      } else if (typeof w.__slSidebarNavSync === 'function') {
        w.__slSidebarNavSync();
      }
    })();
    </script>
    """.replace("__ICON_MAP__", icon_payload)


def _sidebar_alert_script() -> str:
    return """
    <script>
    (function sidebarAlertRelocator(){
      const w = window;
      function getDoc(){
        try { return (w.parent && w.parent.document) ? w.parent.document : document; }
        catch (e) { return document; }
      }
      function relocate(){
        const doc = getDoc();
        if (!doc) return;
        const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) return;
        const shell = sidebar.querySelector('.block-container') || sidebar;
        const footerHost = sidebar.querySelector('.sb-footer-line')?.parentElement || shell.lastElementChild || shell;
        const alerts = Array.from(sidebar.querySelectorAll('.stAlert'));
        if (!alerts.length || !footerHost) return;
        alerts.forEach((alert) => {
          const block = alert.closest('[data-testid="stVerticalBlock"]') || alert;
          if (!block || block === footerHost) return;
          footerHost.after(block);
        });
      }
      if (w.__slSidebarAlertInit) {
        if (typeof w.__slSidebarAlertRelocate === 'function') {
          w.__slSidebarAlertRelocate();
        }
        return;
      }
      w.__slSidebarAlertInit = true;
      w.__slSidebarAlertRelocate = relocate;
      const observer = new MutationObserver(relocate);
      const init = () => {
        const doc = getDoc();
        const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) {
          setTimeout(init, 160);
          return;
        }
        observer.observe(sidebar, { childList: true, subtree: true });
        relocate();
      };
      init();
      w.addEventListener('beforeunload', () => {
        try { observer.disconnect(); } catch (e) {}
      });
    })();
    </script>
    """


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
    if suffix in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif suffix == ".svg":
        mime = "image/svg+xml"
    elif suffix == ".gif":
        mime = "image/gif"

    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


__all__ = ["bootstrap_sidebar_auto_collapse", "build_sidebar"]
