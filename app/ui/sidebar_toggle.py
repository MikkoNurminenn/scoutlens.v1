from __future__ import annotations

from app.ui.sidebar_toggle_css import inject_sidebar_toggle_icon_css


def render_sidebar_toggle() -> None:
    """Ensure sidebar toggle controls remain visible across Streamlit variants."""
    inject_sidebar_toggle_icon_css()
