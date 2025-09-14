"""Shortlists management page."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError
from app.ui import bootstrap_sidebar_auto_collapse

from app.supabase_client import get_client
from app.perf import track


@st.cache_data(ttl=60, show_spinner=False)
def list_shortlists():
    sb = get_client()
    with track("shortlists:load_shortlists"):
        return (
            sb.table("shortlists")
            .select("id,name,created_at")
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )


@st.cache_data(ttl=60, show_spinner=False)
def list_players():
    sb = get_client()
    with track("shortlists:load_players"):
        return (
            sb.table("players")
            .select("id,name,position,current_club")
            .order("name")
            .execute()
            .data
            or []
        )


@st.cache_data(ttl=60, show_spinner=False)
def list_shortlist_items(sid: str):
    sb = get_client()
    with track("shortlists:list_items"):
        return (
            sb.table("shortlist_items")
            .select("player_id,created_at")
            .eq("shortlist_id", sid)
            .execute()
            .data
            or []
        )


@st.cache_data(ttl=60, show_spinner=False)
def list_players_by_ids(ids: list[str]):
    if not ids:
        return []
    sb = get_client()
    with track("shortlists:players_by_ids"):
        return (
            sb.table("players")
            .select("id,name,position,current_club")
            .in_("id", ids)
            .order("name")
            .execute()
            .data
            or []
        )


bootstrap_sidebar_auto_collapse()


def show_shortlists_page() -> None:
    """Render the Shortlists page."""
    st.title("⭐ Shortlists")
    sb = get_client()

    # create shortlist
    with st.expander("Create new shortlist"):
        name = st.text_input("Shortlist name", key="shortlists__name")
        if st.button("Create", type="primary"):
            if not name.strip():
                st.warning("Name required.")
            else:
                try:
                    sb.table("shortlists").insert({"name": name.strip()}).execute()
                    list_shortlists.clear()
                    st.success("Shortlist created.")
                    st.rerun()
                except APIError as e:  # pragma: no cover - UI error handling
                    st.error(f"Failed to create shortlist: {e}")

    # load shortlists
    try:
        shortlists = list_shortlists()
    except APIError as e:  # pragma: no cover - UI error handling
        st.error(f"Failed to load shortlists: {e}")
        return

    if not shortlists:
        st.info("No shortlists yet. Create one above.")
        return

    sid = st.selectbox(
        "Select shortlist",
        options=[s["id"] for s in shortlists],
        format_func=lambda x: next(s["name"] for s in shortlists if s["id"] == x),
    )
    st.session_state["shortlists__sid"] = sid

    if st.button("Delete shortlist", type="secondary"):
        try:
            sb.table("shortlist_items").delete().eq("shortlist_id", sid).execute()
            sb.table("shortlists").delete().eq("id", sid).execute()
            list_shortlists.clear()
            list_shortlist_items.clear()
            st.toast("Shortlist deleted ✅")
            st.rerun()
        except APIError as e:  # pragma: no cover - UI error handling
            st.error(f"Failed to delete shortlist: {e}")

    # add players
    st.subheader("Add players")
    try:
        players = list_players()
    except APIError as e:  # pragma: no cover - UI error handling
        st.error(f"Failed to load players: {e}")
        return

    label_by_id = {
        p["id"]: f"{p['name']} – {p.get('position') or '—'} ({p.get('current_club') or '—'})"
        for p in players
    }
    add_pid = st.selectbox(
        "Player", options=list(label_by_id.keys()), format_func=lambda x: label_by_id[x], key="shortlists__add_pid"
    )
    if st.button("Add to shortlist", type="primary"):
        try:
            sb.table("shortlist_items").insert({"shortlist_id": sid, "player_id": add_pid}).execute()
            list_shortlist_items.clear()
            list_players_by_ids.clear()
            st.toast("Added ✅")
            st.rerun()
        except APIError as e:  # pragma: no cover - UI error handling
            if "duplicate key" in str(e).lower():
                st.info("Player is already in this shortlist.")
            else:
                st.error(f"Failed to add: {e}")

    # list members
    st.subheader("Players in shortlist")
    try:
        items = list_shortlist_items(sid)
        if items:
            ids = [it["player_id"] for it in items]
            plist = list_players_by_ids(ids)
            df = pd.DataFrame(plist)
            with track("shortlists:table"):
                st.dataframe(df, use_container_width=True)

            pid_to_remove = st.selectbox(
                "Remove player",
                options=[p["id"] for p in plist],
                format_func=lambda x: next(p["name"] for p in plist if p["id"] == x),
            )
            if st.button("Remove", type="secondary"):
                sb.table("shortlist_items").delete().eq("shortlist_id", sid).eq("player_id", pid_to_remove).execute()
                list_shortlist_items.clear()
                list_players_by_ids.clear()
                st.toast("Removed ✅")
                st.rerun()
        else:
            st.info("No players in this shortlist yet.")
    except APIError as e:  # pragma: no cover - UI error handling
        st.error(f"Failed to list shortlist members: {e}")


__all__ = ["show_shortlists_page"]

