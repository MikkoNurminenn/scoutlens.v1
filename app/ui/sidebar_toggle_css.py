from __future__ import annotations

import streamlit as st


_TOGGLE_STYLE_ID = "sl-sidebar-toggle-icon"
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


def inject_sidebar_toggle_icon_css() -> None:
    """Ensure the sidebar toggle icon keeps high contrast on dark headers."""
    st.markdown(_TOGGLE_STYLE, unsafe_allow_html=True)


def improve_collapsed_toggle_visibility() -> None:
    """Backwards-compatible wrapper that applies the toggle icon CSS."""
    inject_sidebar_toggle_icon_css()
