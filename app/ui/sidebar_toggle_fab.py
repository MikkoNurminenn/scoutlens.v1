from __future__ import annotations
from typing import Literal, Tuple

import json
import streamlit as st
from streamlit.components.v1 import html as _html

Position = Literal["tl", "tr", "bl", "br"]
IconMode = Literal["chevron", "hamburger"]

_DEF_BG = "#ffffff"
_DEF_FG = "#0b1020"


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def sl_inject_sidebar_fab(
    *,
    position: Position = "tl",
    offset: Tuple[int, int] = (12, 12),
    size_px: int = 44,
    always_white: bool = False,
    bg_open: str = _DEF_BG,
    fg_open: str = _DEF_FG,
    bg_closed: str = _DEF_BG,
    fg_closed: str = _DEF_FG,
    ring: str = "rgba(99,102,241,.35)",
    border: str = "1px solid rgba(15,23,42,.22)",
    shadow: str = "0 16px 36px rgba(15,23,42,.28)",
    hover_shadow: str = "0 20px 42px rgba(15,23,42,.32)",
    icon_mode: IconMode = "hamburger",
    badge: bool = False,
    badge_open_text: str = "Close",
    badge_closed_text: str = "Open",
) -> None:
    """Inject a floating action button that proxies the sidebar toggle."""

    if st.session_state.get("_sl_sidebar_fab_injected"):
        return
    st.session_state["_sl_sidebar_fab_injected"] = True

    if always_white:
        bg_open = bg_closed = _DEF_BG
        fg_open = fg_closed = _DEF_FG

    x_offset, y_offset = offset
    inset_block_start = "auto"
    inset_block_end = "auto"
    inset_inline_start = "auto"
    inset_inline_end = "auto"
    if position == "tl":
        inset_block_start = f"max({y_offset}px, env(safe-area-inset-top))"
        inset_inline_start = f"max({x_offset}px, env(safe-area-inset-left))"
    elif position == "tr":
        inset_block_start = f"max({y_offset}px, env(safe-area-inset-top))"
        inset_inline_end = f"max({x_offset}px, env(safe-area-inset-right))"
    elif position == "bl":
        inset_block_end = f"max({y_offset}px, env(safe-area-inset-bottom))"
        inset_inline_start = f"max({x_offset}px, env(safe-area-inset-left))"
    elif position == "br":
        inset_block_end = f"max({y_offset}px, env(safe-area-inset-bottom))"
        inset_inline_end = f"max({x_offset}px, env(safe-area-inset-right))"

    chevron_svg = (
        '<g class="sl-ico sl-ico-chevron" aria-hidden="true">'
        '<path d="M15.5 19a1 1 0 0 1-.7-.3l-6-6a1 1 0 0 1 0-1.4l6-6a1 1 0 1 1 1.4 1.4L10.9 12l5.3 5.3A1 1 0 0 1 15.5 19z" />'
        '</g>'
    )
    hamburger_svg = (
        '<g class="sl-ico sl-ico-hamburger" aria-hidden="true">'
        '<rect x="4" y="7" width="16" height="2" rx="1"></rect>'
        '<rect x="4" y="11" width="16" height="2" rx="1"></rect>'
        '<rect x="4" y="15" width="16" height="2" rx="1"></rect>'
        '</g>'
        '<g class="sl-ico sl-ico-close" aria-hidden="true">'
        '<path d="M7 7 L17 17 M17 7 L7 17" stroke-width="2" stroke-linecap="round" fill="none"></path>'
        '</g>'
    )

    icon_markup_json = json.dumps(
        chevron_svg if icon_mode == "chevron" else hamburger_svg,
        ensure_ascii=False,
    )
    badge_markup_json = json.dumps(
        "<span class=\"sl-badge\"></span>" if badge else "",
        ensure_ascii=False,
    )

    style_block = f"""
  #sl-sidebar-fab {{
    position: fixed;
    inset-block-start: {inset_block_start};
    inset-block-end: {inset_block_end};
    inset-inline-start: {inset_inline_start};
    inset-inline-end: {inset_inline_end};
    inline-size: {size_px}px;
    block-size: {size_px}px;
    z-index: 1300;
    display: grid;
    place-items: center;
    border-radius: 999px;
    border: {border};
    box-shadow: {shadow}, inset 0 0 0 .6px rgba(255,255,255,.45);
    backdrop-filter: blur(6px);
    cursor: pointer;
    transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease, color .18s ease;
  }}
  #sl-sidebar-fab:hover {{
    transform: translateY(-1px);
    box-shadow: {hover_shadow}, inset 0 0 0 .8px rgba(255,255,255,.55), 0 0 0 3px {ring};
    border-color: rgba(99,102,241,.55);
  }}
  #sl-sidebar-fab:focus-visible {{
    outline: none;
    box-shadow: 0 0 0 3px {ring};
  }}
  #sl-sidebar-fab svg {{
    width: 20px;
    height: 20px;
    fill: currentColor;
    stroke: currentColor;
    transition: transform .18s ease, opacity .18s ease;
  }}
  #sl-sidebar-fab[data-icon="hamburger"][data-collapsed="true"] .sl-ico-hamburger {{ opacity: 1; }}
  #sl-sidebar-fab[data-icon="hamburger"][data-collapsed="true"] .sl-ico-close {{ opacity: 0; }}
  #sl-sidebar-fab[data-icon="hamburger"][data-collapsed="false"] .sl-ico-hamburger {{ opacity: 0; }}
  #sl-sidebar-fab[data-icon="hamburger"][data-collapsed="false"] .sl-ico-close {{ opacity: 1; }}
  #sl-sidebar-fab[data-icon="chevron"][data-collapsed="true"] .sl-ico-chevron {{ transform: rotate(180deg); opacity: 1; }}
  #sl-sidebar-fab[data-icon="chevron"][data-collapsed="false"] .sl-ico-chevron {{ transform: rotate(0deg); opacity: 1; }}
  .sl-ico-hamburger, .sl-ico-close {{ opacity: 0; }}
  #sl-sidebar-fab .sl-badge {{
    position: absolute;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    background: rgba(15,23,42,0.78);
    color: #fff;
    pointer-events: none;
    white-space: nowrap;
  }}
  [data-testid="stSidebarCollapseButton"],
  button[data-testid="stSidebarCollapseButton"] {{
    opacity: 0 !important;
  }}
    """

    script = f"""
(function() {{
  try {{
    const w = window.parent && window.parent.document ? window.parent : window;
    const doc = w.document;
    if (!doc) return;

    if (w.__slSidebarFabInjected) return;
    w.__slSidebarFabInjected = true;

    const styleId = 'sl-sidebar-fab-style';
    if (!doc.getElementById(styleId)) {{
      const styleEl = doc.createElement('style');
      styleEl.id = styleId;
      styleEl.textContent = {json.dumps(style_block)};
      doc.head.appendChild(styleEl);
    }}

    const iconMarkup = {icon_markup_json};
    const badgeMarkup = {badge_markup_json};

    let fab = doc.getElementById('sl-sidebar-fab');
    if (!fab) {{
      fab = doc.createElement('div');
      fab.id = 'sl-sidebar-fab';
      fab.setAttribute('role', 'button');
      fab.setAttribute('tabindex', '0');
      fab.setAttribute('aria-label', 'Toggle sidebar');
      fab.setAttribute('title', 'Toggle sidebar');
      fab.dataset.icon = {json.dumps(icon_mode)};
      fab.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + iconMarkup + '</svg>' + badgeMarkup;
      doc.body.appendChild(fab);
    }} else {{
      fab.dataset.icon = {json.dumps(icon_mode)};
      fab.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + iconMarkup + '</svg>' + badgeMarkup;
    }}

    const badgeEl = fab.querySelector('.sl-badge');

    function findNative() {{
      return doc.querySelector('[data-testid="stSidebarCollapseButton"] button, button[data-testid="stSidebarCollapseButton"]');
    }}

    function isCollapsed() {{
      return doc.body.classList.contains('stSidebarCollapsedControl');
    }}

    function setFabState(collapsed) {{
      fab.dataset.collapsed = collapsed ? 'true' : 'false';
      const bgOpen = {_string(bg_open)};
      const fgOpen = {_string(fg_open)};
      const bgClosed = {_string(bg_closed)};
      const fgClosed = {_string(fg_closed)};
      const bg = collapsed ? bgClosed : bgOpen;
      const fg = collapsed ? fgClosed : fgOpen;
      fab.style.background = bg;
      fab.style.color = fg;
      if (badgeEl) {{
        badgeEl.textContent = collapsed ? {_string(badge_closed_text)} : {_string(badge_open_text)};
        const rect = fab.getBoundingClientRect();
        badgeEl.style.left = (rect.width + 8) + 'px';
        badgeEl.style.top = '50%';
        badgeEl.style.transform = 'translateY(-50%)';
      }}
    }}

    function syncUI() {{
      setFabState(isCollapsed());
    }}

    function clickNative() {{
      const btn = findNative();
      if (btn) {{
        btn.click();
      }}
      setTimeout(syncUI, 0);
    }}

    fab.addEventListener('click', clickNative);
    fab.addEventListener('keydown', function(event) {{
      if (event.key === 'Enter' || event.key === ' ') {{
        event.preventDefault();
        clickNative();
      }}
    }});

    const observer = new MutationObserver(syncUI);
    observer.observe(doc.body, {{ attributes: true, attributeFilter: ['class'] }});

    syncUI();
  }} catch (error) {{
    console.error(error);
  }}
}})();
    """

    _html(f"<script>{script}</script>", height=0, width=0)
