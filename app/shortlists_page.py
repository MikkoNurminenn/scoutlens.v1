"""Shortlists management page."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError

from app.supabase_client import get_client


def show_shortlists_page() -> None:
    """Render the Shortlists page."""
    st.title("⭐ Shortlists")
    sb = get_client()

    # create shortlist
    with st.expander("Create new shortlist"):
        name = st.text_input("Shortlist name", key="shortlist__name")
        if st.button("Create"):
            if not name.strip():
                st.warning("Name required.")
            else:
                try:
                    sb.table("shortlists").insert({"name": name.strip()}).execute()
                    st.success("Shortlist created.")
                    st.rerun()
                except APIError as e:  # pragma: no cover - UI error handling
                    st.error(f"Failed to create shortlist: {e}")

    # load shortlists
    try:
        shortlists = (
            sb.table("shortlists")
            .select("id,name,created_at")
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )
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
    st.session_state["shortlist__sid"] = sid

    # add players
    st.subheader("Add players")
    try:
        players = (
            sb.table("players")
            .select("id,name,position,current_club")
            .order("name")
            .execute()
            .data
            or []
        )
    except APIError as e:  # pragma: no cover - UI error handling
        st.error(f"Failed to load players: {e}")
        return

    label_by_id = {
        p["id"]: f"{p['name']} – {p.get('position') or '—'} ({p.get('current_club') or '—'})"
        for p in players
    }
    add_pid = st.selectbox(
        "Player", options=list(label_by_id.keys()), format_func=lambda x: label_by_id[x], key="shortlist__add_pid"
    )
    if st.button("Add to shortlist"):
        try:
            sb.table("shortlist_items").insert({"shortlist_id": sid, "player_id": add_pid}).execute()
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
        items = (
            sb.table("shortlist_items")
            .select("player_id,created_at")
            .eq("shortlist_id", sid)
            .execute()
            .data
            or []
        )
        if items:
            ids = [it["player_id"] for it in items]
            plist = (
                sb.table("players")
                .select("id,name,position,current_club")
                .in_("id", ids)
                .order("name")
                .execute()
                .data
                or []
            )
            df = pd.DataFrame(plist)
            st.dataframe(df, use_container_width=True)

            pid_to_remove = st.selectbox(
                "Remove player",
                options=[p["id"] for p in plist],
                format_func=lambda x: next(p["name"] for p in plist if p["id"] == x),
            )
            if st.button("Remove"):
                sb.table("shortlist_items").delete().eq("shortlist_id", sid).eq("player_id", pid_to_remove).execute()
                st.toast("Removed ✅")
                st.rerun()
        else:
            st.info("No players in this shortlist yet.")
    except APIError as e:  # pragma: no cover - UI error handling
        st.error(f"Failed to list shortlist members: {e}")


__all__ = ["show_shortlists_page"]

