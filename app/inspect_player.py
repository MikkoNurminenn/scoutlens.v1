# app/inspect_player.py
from __future__ import annotations
import streamlit as st
import pandas as pd
from postgrest.exceptions import APIError
from app.supabase_client import get_client

PAGE_KEY = "inspect__"  # yhtenäiset avainprefiksit

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

    # 1) Pelaajat
    try:
        players = _load_players()
    except APIError as e:
        st.error(f"Failed to load players: {e}")
        return

    if not players:
        st.info("No players found. Add a player first from Reports or Players.")
        return

    # 2) Selectbox
    labels = [f"{p['name']} ({p.get('current_club') or '—'})" for p in players]
    id_by_label = {lbl: p["id"] for lbl, p in zip(labels, players)}

    selected_label = st.selectbox(
        "Pick a player to inspect:",
        options=labels,
        key=PAGE_KEY + "player_select",
        index=0,
    )
    player_id = id_by_label[selected_label]
    player = next(p for p in players if p["id"] == player_id)

    # 3) Pelaajan perusinfo
    st.subheader(player["name"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Position", player.get("position") or "—")
    c2.metric("Club", player.get("current_club") or "—")
    c3.metric("Nationality", player.get("nationality") or "—")
    dob = player.get("date_of_birth")
    c4.metric("DOB", str(dob) if dob else "—")

    st.divider()

    # 4) Raportit
    st.markdown("### Reports")
    try:
        reps = _load_reports(player_id)
    except APIError as e:
        st.error(f"Failed to load reports: {e}")
        return

    if not reps:
        st.info("No reports yet for this player.")
        return

    df = pd.DataFrame(reps)

    # Kolumnien ystävällinen järjestys
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

    # Ei st.rerun() callbackeissa – Streamlit hoitaa uudellenrenderöinnin valinnasta.
