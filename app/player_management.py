"""Player management page allowing deletion of players."""

from __future__ import annotations

import streamlit as st
from postgrest.exceptions import APIError

from app.ui import bootstrap_sidebar_auto_collapse
from app.supabase_client import get_client
from app.player_editor import remove_from_players_storage_by_ids


@st.cache_data(ttl=60, show_spinner=False)
def list_players():
    sb = get_client()
    return (
        sb.table("players")
        .select("id,name,position,current_club")
        .order("name")
        .execute()
        .data
        or []
    )


bootstrap_sidebar_auto_collapse()


def show_player_management_page() -> None:
    st.title("👤 Players")

    auth = st.session_state.get("auth", {})
    if not auth.get("authenticated"):
        st.info("Sign in to delete players.")
        return

    try:
        players = list_players()
    except APIError as e:  # pragma: no cover - UI error handling
        st.error(f"Failed to load players: {e}")
        return

    if not players:
        st.info("No players available.")
        return

    label_by_id = {
        p["id"]: f"{p['name']} – {p.get('position') or '—'} ({p.get('current_club') or '—'})"
        for p in players
    }
    selected_ids = st.multiselect(
        "Players to delete",
        options=list(label_by_id.keys()),
        format_func=lambda x: label_by_id[x],
        key="player_mgmt__ids",
    )

    if st.button("Delete selected", type="secondary", disabled=not selected_ids):
        try:
            remove_from_players_storage_by_ids(selected_ids)
            list_players.clear()
            st.success("Deleted selected players.")
            st.rerun()
        except Exception as e:  # pragma: no cover - UI error handling
            st.error(f"Failed to delete players: {e}")


__all__ = ["show_player_management_page"]

