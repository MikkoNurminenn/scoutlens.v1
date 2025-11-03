"""Player management page allowing deletion of players."""

from __future__ import annotations

import streamlit as st

try:
    from app.ui import bootstrap_sidebar_auto_collapse
except ImportError:  # pragma: no cover - compatibility shim for legacy packages
    from app.ui.sidebar import bootstrap_sidebar_auto_collapse
from app.ui.players_delete import players_delete_panel

bootstrap_sidebar_auto_collapse()


def show_player_management_page() -> None:
    st.title("👤 Players")

    auth = st.session_state.get("auth", {})
    if not auth.get("authenticated"):
        st.info("Sign in to delete players.")
        return

    players_delete_panel()


__all__ = ["show_player_management_page"]
