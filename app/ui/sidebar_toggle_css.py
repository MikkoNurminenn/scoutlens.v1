from __future__ import annotations

import streamlit as st


_TOGGLE_STYLE_ID = "sl-sidebar-toggle-icon"
_COLLAPSED_WHITE_STYLE_ID = "sl-sidebar-toggle-collapsed-white"

_TOGGLE_STYLE = f"""
<style id=\"{_TOGGLE_STYLE_ID}\">
  :root {{
    --sl-sidebar-toggle-icon-color: #ffffff;
  }}

  html[data-theme="light"] {{
    --sl-sidebar-toggle-icon-color: #111827;
  }}

  :is(
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"]
  ) {{
    color: var(--sl-sidebar-toggle-icon-color) !important;
  }}

  :is(
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarCollapseButton"],
    [data-testid="baseButton-headerNoPadding"],
    button[aria-label*="sidebar" i]
  ) {{
    color: var(--sl-sidebar-toggle-icon-color) !important;
  }}

  :is(
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarCollapseButton"],
    [data-testid="baseButton-headerNoPadding"],
    button[aria-label*="sidebar" i]
  ):is(:hover, :focus, :focus-visible, :active) {{
    color: var(--sl-sidebar-toggle-icon-color) !important;
  }}

  :is(
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarCollapseButton"],
    [data-testid="baseButton-headerNoPadding"],
    button[aria-label*="sidebar" i]
  ) svg {{
    color: inherit !important;
  }}

  :is(
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarCollapseButton"],
    [data-testid="baseButton-headerNoPadding"],
    button[aria-label*="sidebar" i]
  ) svg *:not([fill="none"]) {{
    fill: currentColor !important;
  }}

  :is(
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarCollapseButton"],
    [data-testid="baseButton-headerNoPadding"],
    button[aria-label*="sidebar" i]
  ) svg *[stroke]:not([stroke="none"]) {{
    stroke: currentColor !important;
  }}
</style>
"""

_COLLAPSED_WHITE_STYLE = f"""
<style id=\"{_COLLAPSED_WHITE_STYLE_ID}\">
  /* === Collapsed sidebar toggle: force white background & high-contrast icon == */
  body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"],
  body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"] > button,
  body.stSidebarCollapsedControl button[data-testid="stSidebarCollapseButton"] {{
    position: fixed !important;
    inset-block-start: max(0.75rem, env(safe-area-inset-top)) !important;
    inset-inline-start: max(0.75rem, env(safe-area-inset-left)) !important;
    z-index: 1300 !important;

    width: 2.75rem !important;
    height: 2.75rem !important;
    padding: 0 !important;

    background: #ffffff !important;
    color: #0b1020 !important;
    border: 1px solid rgba(15, 23, 42, 0.22) !important;
    border-radius: 999px !important;

    box-shadow:
      0 16px 36px rgba(15, 23, 42, 0.28),
      inset 0 0 0 0.6px rgba(255, 255, 255, 0.45) !important;

    mix-blend-mode: normal !important;
    filter: none !important;
    backdrop-filter: blur(6px) !important;

    transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease !important;
  }}

  body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"] svg,
  body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"] svg *,
  body.stSidebarCollapsedControl button[data-testid="stSidebarCollapseButton"] svg,
  body.stSidebarCollapsedControl button[data-testid="stSidebarCollapseButton"] svg * {{
    fill: currentColor !important;
    stroke: currentColor !important;
  }}

  body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"] svg {{
    transform: rotate(180deg) !important;
    transition: transform .18s ease !important;
  }}

  body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"]:hover,
  body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"] > button:hover,
  body.stSidebarCollapsedControl button[data-testid="stSidebarCollapseButton"]:hover,
  body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"]:focus-visible,
  body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"] > button:focus-visible,
  body.stSidebarCollapsedControl button[data-testid="stSidebarCollapseButton"]:focus-visible {{
    transform: translateY(-1px) !important;
    outline: none !important;
    border-color: rgba(99, 102, 241, 0.55) !important;
    box-shadow:
      0 20px 42px rgba(15, 23, 42, 0.32),
      inset 0 0 0 0.8px rgba(255, 255, 255, 0.55),
      0 0 0 3px rgba(99, 102, 241, 0.35) !important;
  }}

  @media (max-width: 520px) {{
    body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"],
    body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"] > button,
    body.stSidebarCollapsedControl button[data-testid="stSidebarCollapseButton"] {{
      width: 2.4rem !important;
      height: 2.4rem !important;
      inset-block-start: max(0.6rem, env(safe-area-inset-top)) !important;
      inset-inline-start: max(0.6rem, env(safe-area-inset-left)) !important;
    }}
  }}

  @media (prefers-reduced-motion: reduce) {{
    body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"],
    body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"] > button,
    body.stSidebarCollapsedControl button[data-testid="stSidebarCollapseButton"],
    body.stSidebarCollapsedControl [data-testid="stSidebarCollapseButton"] svg {{
      transition: none !important;
      transform: none !important;
    }}
  }}
</style>
"""


def inject_sidebar_toggle_icon_css() -> None:
    """Ensure the sidebar toggle icon keeps high contrast on dark headers."""
    st.markdown(_TOGGLE_STYLE, unsafe_allow_html=True)


def improve_collapsed_toggle_visibility() -> None:
    """Backwards-compatible wrapper that applies the toggle icon CSS."""
    inject_sidebar_toggle_icon_css()


def inject_collapsed_toggle_white_style() -> None:
    """Force the collapsed toggle button to stay white with dark iconography."""

    st.markdown(
        f"""
        <script>
          (function() {{
            const doc = window.parent?.document || document;
            if (!doc) return;
            const existing = doc.getElementById('{_COLLAPSED_WHITE_STYLE_ID}');
            if (existing) existing.remove();
          }})();
        </script>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(_COLLAPSED_WHITE_STYLE, unsafe_allow_html=True)
