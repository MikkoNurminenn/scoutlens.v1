"""Inspect Player page to view profile and scouting reports."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError

from app.supabase_client import get_client


PLAYER_FIELDS = (
    "id,name,position,preferred_foot,nationality,current_club,"
    "date_of_birth,transfermarkt_url,created_at,updated_at"
)


def _players_for_picker(sb):
    """Return list of players for the selectbox."""
    return (
        sb.table("players")
        .select("id,name,current_club")
        .order("name")
        .execute()
        .data
        or []
    )


def _player_profile(sb, player_id: str):
    """Fetch a player's profile."""
    return (
        sb.table("players")
        .select(PLAYER_FIELDS)
        .eq("id", player_id)
        .single()
        .execute()
        .data
    )


def _reports_for_player(sb, player_id: str, limit: int = 100):
    """Fetch scouting reports for a player."""
    return (
        sb.table("reports")
        .select(
            "id,report_date,competition,opponent,location,position_played," \
            "minutes,rating,strengths,weaknesses,notes,scout_name"
        )
        .eq("player_id", player_id)
        .order("report_date", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def show_inspect_player() -> None:
    """Render Inspect Player page."""
    st.title("🔍 Inspect Player")
    sb = get_client()

    try:
        players = _players_for_picker(sb)
    except APIError as e:
        st.error(f"Failed to load players: {e}")
        return

    if not players:
        st.info("No players found. Create a player from Reports or Players first.")
        return

    labels = [f"{p['name']} ({p.get('current_club') or '—'})" for p in players]
    id_by_label = {lbl: p["id"] for lbl, p in zip(labels, players)}
    choice = st.selectbox("Pick a player to inspect.", labels, key="inspect__player_select")
    player_id = id_by_label[choice]

    try:
        player = _player_profile(sb, player_id)
        reports = _reports_for_player(sb, player_id)
    except APIError as e:
        st.error(f"Failed to load player data: {e}")
        return

    with st.container(border=True):
        st.subheader(player["name"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Position", player.get("position") or "—")
        c2.metric("Club", player.get("current_club") or "—")
        c3.metric("Nationality", player.get("nationality") or "—")
        r1, r2, r3 = st.columns(3)
        r1.write(f"**Preferred foot:** {player.get('preferred_foot') or '—'}")
        r2.write(f"**Date of birth:** {player.get('date_of_birth') or '—'}")
        tm = player.get("transfermarkt_url")
        r3.write("**Transfermarkt:** " + (f"[link]({tm})" if tm else "—"))

    st.markdown("### Scout reports")
    if not reports:
        st.info("No reports for this player yet.")
        return

    df = pd.DataFrame(reports)
    avg = df["rating"].dropna().mean() if "rating" in df else None
    mins = int(df["minutes"].dropna().sum()) if "minutes" in df else None
    m1, m2 = st.columns(2)
    m1.metric("Avg rating", f"{avg:.1f}" if avg is not None else "—")
    m2.metric("Total minutes", f"{mins}" if mins is not None else "—")

    cols = [
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
    cols = [c for c in cols if c in df.columns]
    st.dataframe(df[cols], hide_index=True, use_container_width=True)


__all__ = ["show_inspect_player"]

