from __future__ import annotations

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError

from app.supabase_client import get_client


PAGE_KEY = "inspect__v3"  # change key to force fresh widgets


@st.cache_data(show_spinner=False, ttl=30)
def _load_players():
    sb = get_client()
    resp = (
        sb.table("players")
        .select("id,name,current_club")
        .order("name")
        .execute()
    )
    return resp.data or []


@st.cache_data(show_spinner=False, ttl=10)
def _load_player_profile(player_id: str):
    sb = get_client()
    resp = (
        sb.table("players")
        .select(
            "id,name,position,preferred_foot,nationality,current_club,date_of_birth,transfermarkt_url"
        )
        .eq("id", player_id)
        .single()
        .execute()
    )
    return resp.data or {}


@st.cache_data(show_spinner=False, ttl=10)
def _load_reports(player_id: str):
    sb = get_client()
    resp = (
        sb.table("reports")
        .select(
            "id,report_date,competition,opponent,location,position_played,minutes,rating,scout_name,strengths,weaknesses,notes"
        )
        .eq("player_id", player_id)
        .order("report_date", desc=True)
        .execute()
    )
    return resp.data or []


def show_inspect_player() -> None:
    st.title("🔍 Inspect Player")

    # 1) Player picker
    try:
        players = _load_players()
    except APIError as e:
        st.error(f"Failed to load players: {e}")
        players = []

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

    # 2) Player profile
    try:
        profile = _load_player_profile(player_id)
    except APIError as e:
        st.error(f"Failed to load player profile: {e}")
        return

    with st.container(border=True):
        st.markdown(f"### {profile.get('name', 'Unknown')}")
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Position:** {profile.get('position') or '—'}")
        c2.write(f"**Preferred Foot:** {profile.get('preferred_foot') or '—'}")
        c3.write(f"**Nationality:** {profile.get('nationality') or '—'}")
        c4, c5, c6 = st.columns(3)
        c4.write(f"**Club:** {profile.get('current_club') or '—'}")
        dob = profile.get("date_of_birth")
        c5.write(f"**DOB:** {dob or '—'}")
        tm = profile.get("transfermarkt_url")
        c6.markdown(f"[Transfermarkt]({tm})" if tm else "**Transfermarkt:** —")

    st.markdown("### Reports")

    # 3) Reports
    try:
        reps = _load_reports(player_id)
    except APIError as e:
        st.error(f"Failed to load reports: {e}")
        return

    if not reps:
        st.info("No reports yet for this player.")
        return

    df = pd.DataFrame(reps)

    avg_rating = None
    if "rating" in df.columns:
        col = pd.to_numeric(df["rating"], errors="coerce").dropna()
        if not col.empty:
            avg_rating = col.mean()

    total_minutes = None
    if "minutes" in df.columns:
        col = pd.to_numeric(df["minutes"], errors="coerce").dropna()
        if not col.empty:
            total_minutes = col.sum()

    m1, m2 = st.columns(2)
    m1.metric("Avg rating", f"{avg_rating:.2f}" if avg_rating is not None else "—")
    m2.metric("Total minutes", int(total_minutes) if total_minutes is not None else "—")

    prefer = [
        "report_date",
        "competition",
        "opponent",
        "location",
        "position_played",
        "minutes",
        "rating",
        "scout_name",
        "strengths",
        "weaknesses",
        "notes",
    ]
    cols = [c for c in prefer if c in df.columns] + [c for c in df.columns if c not in prefer]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)


__all__ = ["show_inspect_player"]

