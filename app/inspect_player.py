"""Inspect Player page for viewing player profile and linked reports."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError
from .ui import bootstrap_sidebar_auto_collapse

from app.supabase_client import get_client


bootstrap_sidebar_auto_collapse()


def show_inspect_player() -> None:
    """Render the Inspect Player page."""
    st.title("🔍 Inspect Player")
    sb = get_client()

    # --- Players dropdown ---
    try:
        players = (
            sb.table("players")
            .select(
                "id,name,position,current_club,nationality,date_of_birth,team_name,preferred_foot,club_number,scout_rating,transfermarkt_url"
            )
            .order("name")
            .execute()
            .data
            or []
        )
    except APIError as e:  # pragma: no cover - UI error handling
        st.error(f"Failed to load players: {e}")
        return

    if not players:
        st.info("No players found. Create a player from Reports or Players first.")
        return

    label_by_id = {
        p["id"]: f"{p['name']} ({p.get('current_club') or p.get('team_name') or '—'})"
        for p in players
    }
    default_id = st.session_state.get("inspect__player_id") or players[0]["id"]
    player_id = st.selectbox(
        "Player",
        options=list(label_by_id.keys()),
        format_func=lambda x: label_by_id[x],
        index=list(label_by_id.keys()).index(default_id)
        if default_id in label_by_id
        else 0,
    )
    st.session_state["inspect__player_id"] = player_id

    player = next(p for p in players if p["id"] == player_id)

    # --- Player header ---
    st.subheader(player["name"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Position", player.get("position") or "—")
    col2.metric("Club", player.get("current_club") or player.get("team_name") or "—")
    col3.metric("Nationality", player.get("nationality") or "—")
    with st.expander("Details"):
        st.write(
            {
                "Date of birth": player.get("date_of_birth"),
                "Preferred foot": player.get("preferred_foot"),
                "Number": player.get("club_number"),
                "Scout rating": player.get("scout_rating"),
                "Transfermarkt": player.get("transfermarkt_url"),
            }
        )

    # --- Reports list ---
    try:
        reports = (
            sb.table("reports")
            .select(
                "id,report_date,competition,opponent,location,position_played,minutes,rating,strengths,weaknesses,notes,scout_name,attributes,created_at,updated_at"
            )
            .eq("player_id", player_id)
            .order("report_date", desc=True)
            .execute()
            .data
            or []
        )
    except APIError as e:  # pragma: no cover - UI error handling
        st.error(f"Failed to load reports: {e}")
        return

    if reports:
        total_minutes = sum(r.get("minutes") or 0 for r in reports)
        ratings = [float(r["rating"]) for r in reports if r.get("rating") is not None]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
        stats = f"Reports: **{len(reports)}** | Total minutes: **{total_minutes}**"
        if avg_rating is not None:
            stats += f" | Avg rating: **{avg_rating}**"
        st.caption(stats)

        df = pd.DataFrame(reports)
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "⬇️ Export CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"{player['name']}_reports.csv",
            mime="text/csv",
        )
        st.download_button(
            "⬇️ Export JSON",
            df.to_json(orient="records").encode("utf-8"),
            file_name=f"{player['name']}_reports.json",
            mime="application/json",
        )
    else:
        st.info("No reports yet for this player.")


__all__ = ["show_inspect_player"]

