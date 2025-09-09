from __future__ import annotations
import pandas as pd
import streamlit as st
from app.supabase_client import get_client
from postgrest.exceptions import APIError


def show_inspect_player() -> None:
    st.title("🔍 Inspect Player")
    sb = get_client()

    # Load players (name + id + a few columns for context)
    try:
        resp = sb.table("players").select(
            "id,name,position,current_club,nationality,date_of_birth"
        ).order("name").execute()
        players = resp.data or []
    except APIError as e:
        st.error(f"Failed to load players: {e}")
        return

    if not players:
        st.info("No players found. Add a player first from Reports or Players.")
        return

    # Build label→id map to keep select labels clean
    labels = [f"{p['name']} ({p.get('current_club') or '—'})" for p in players]
    id_by_label = {lbl: p["id"] for lbl, p in zip(labels, players)}

    selected_label = st.selectbox(
        "Pick a player to inspect:",
        labels,
        index=None,
        placeholder="— Select a player —",
        key="inspect__player_select",
    )
    if not selected_label:
        return

    player_id = id_by_label[selected_label]
    player = next(p for p in players if p["id"] == player_id)

    # Player header
    st.subheader(player["name"])
    cols = st.columns(4)
    cols[0].metric("Position", player.get("position") or "—")
    cols[1].metric("Club", player.get("current_club") or "—")
    cols[2].metric("Nationality", player.get("nationality") or "—")
    cols[3].metric("DOB", str(player.get("date_of_birth") or "—"))

    # Fetch reports for this player
    try:
        reps = sb.table("reports").select(
            "id,report_date,competition,opponent,location,position_played,minutes,rating,notes,created_at"
        ).eq("player_id", player_id).order("report_date", desc=True).execute().data or []
    except APIError as e:
        st.error(f"Failed to load reports: {e}")
        return

    st.markdown("### Reports")
    if not reps:
        st.info("No reports yet for this player.")
        return

    # Simple table; could be upgraded later
    df = pd.DataFrame(reps)
    # Reorder and prettify columns
    cols_order = ["report_date","competition","opponent","location","position_played","minutes","rating","notes"]
    df = df[[c for c in cols_order if c in df.columns]]
    st.dataframe(df, use_container_width=True)
