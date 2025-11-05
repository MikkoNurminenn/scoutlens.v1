from __future__ import annotations

from app.ui.sidebar_toggle_css import inject_sidebar_toggle_icon_css
from app.ui.sidebar_toggle_fab import sl_inject_sidebar_fab


def render_sidebar_toggle() -> None:
    """Ensure sidebar toggle controls remain visible across Streamlit variants."""
    inject_sidebar_toggle_icon_css()
    sl_inject_sidebar_fab(always_white=True, icon_mode="hamburger")
