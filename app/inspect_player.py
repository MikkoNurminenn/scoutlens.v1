from __future__ import annotations
import streamlit as st
import pandas as pd
from postgrest.exceptions import APIError
from app.supabase_client import get_client

PAGE_KEY = "inspect__v2"  # change key to force fresh widgets


@st.cache_data(show_spinner=False, ttl=30)
def _load_players():
    sb = get_client()
    resp = sb.table("players").select(
        "id,name,position,current_club,nationality,date_of_birth"
    ).order("name").execute()
    return resp.data or []


@st.cache_data(show_spinner=False, ttl=10)
def _load_reports(player_id: str):
    sb = get_client()
    resp = sb.table("reports").select(
        "id,report_date,competition,opponent,location,position_played,minutes,rating,notes,created_at"
    ).eq("player_id", player_id).order("report_date", desc=True).execute()
    return resp.data or []


def show_inspect_player() -> None:
    st.title("🔍 Inspect Player")
    st.caption("Inspect view loaded ✅")  # DIAG

    # 1) Players
    try:
        players = _load_players()
    except APIError as e:
        st.error(f"Failed to load players: {e}")
        players = []

    st.caption(f"Loaded players: **{len(players)}**")  # DIAG

    # 2) Selectbox (always renders; disabled if no players)
    if players:
        labels = [f"{p['name']} ({p.get('current_club') or '—'})" for p in players]
        id_by_label = {lbl: p["id"] for lbl, p in zip(labels, players)}
        disabled = False
    else:
        labels = ["— no players found —"]
        id_by_label = {}
        disabled = True

    selected_label = st.selectbox(
        "Pick a player to inspect:",
        options=labels,
        key=PAGE_KEY + "player_select",
        index=0,
        disabled=disabled,
    )

    if disabled:
        st.info("No players found. Add a player first from Reports or Players.")
        return

    player_id = id_by_label[selected_label]
    player = next(p for p in players if p["id"] == player_id)

    # 3) Player header
    st.subheader(player["name"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Position", player.get("position") or "—")
    c2.metric("Club", player.get("current_club") or "—")
    c3.metric("Nationality", player.get("nationality") or "—")
    dob = player.get("date_of_birth")
    c4.metric("DOB", str(dob) if dob else "—")

    st.divider()
    st.markdown("### Reports")

    # 4) Reports for this player
    try:
        reps = _load_reports(player_id)
    except APIError as e:
        st.error(f"Failed to load reports: {e}")
        return

    if not reps:
        st.info("No reports yet for this player.")
        return

    df = pd.DataFrame(reps)
    prefer = [
        "report_date",
        "competition",
        "opponent",
        "location",
        "position_played",
        "minutes",
        "rating",
        "notes",
    ]
    cols = [c for c in prefer if c in df.columns] + [c for c in df.columns if c not in prefer]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)

    # Note: Do NOT call st.rerun() inside callbacks on this page.

