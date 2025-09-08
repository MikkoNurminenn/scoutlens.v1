from __future__ import annotations
from datetime import date
import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError

from app.supabase_client import get_client
from app.db_tables import PLAYERS, REPORTS

TABLE_REPORTS = REPORTS  # reports table name

@st.cache_data(ttl=30)
def load_players():
    """Fetch all players ordered by name."""
    client = get_client()
    try:
        res = client.table(PLAYERS).select(
            "id,name,position,nationality,preferred_foot,current_club,"
            "date_of_birth,height_cm,weight_kg,general_comment,image_url,transfermarkt_url"
        ).order("name").execute()
        return pd.DataFrame(res.data or [])
    except APIError as e:
        st.error(f"Failed to load players: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=30)
def load_reports(player_id: str):
    """Fetch reports for the given player ordered by report_date desc."""
    client = get_client()
    try:
        res = (
            client.table(TABLE_REPORTS)
            .select("id,report_date,competition,opponent,minutes,rating,summary,scout_name")
            .eq("player_id", player_id)
            .order("report_date", desc=True)
            .execute()
        )
        return pd.DataFrame(res.data or [])
    except APIError as e:
        st.error(f"Failed to load reports: {e}")
        return pd.DataFrame()

def show_player_inspect():
    """Render the Inspect Player page."""
    st.title("🔍 Inspect Player")

    df_players = load_players()
    if df_players.empty:
        st.info("No players available.")
        return

    selected_name = st.selectbox("Select a player", df_players["name"].tolist())
    player = df_players[df_players["name"] == selected_name].iloc[0]

    # Profile header
    cols = st.columns([1, 3])
    with cols[0]:
        if player.get("image_url"):
            st.image(player["image_url"], use_column_width=True)
    with cols[1]:
        dob = player.get("date_of_birth")
        age = "?"
        if dob:
            dob_ts = pd.to_datetime(dob, errors="coerce")
            if pd.notna(dob_ts):
                today = pd.Timestamp(date.today())
                age = today.year - dob_ts.year - ((today.month, today.day) < (dob_ts.month, dob_ts.day))
        st.subheader(f"{player['name']} ({player['position']})")
        st.write(
            f"Age: {age} | Club: {player['current_club']} | "
            f"{player['nationality']} | {player['preferred_foot']} foot"
        )

    if player.get("general_comment"):
        st.info(f"**General Comment:** {player['general_comment']}")

    # Attributes
    st.write("**Player Details**")
    st.write(f"Height: {player['height_cm']} cm | Weight: {player['weight_kg']} kg")
    if player.get("transfermarkt_url"):
        st.markdown(f"[Transfermarkt Profile]({player['transfermarkt_url']})")

    # Reports
    df_reports = load_reports(player["id"])
    if df_reports.empty:
        st.warning("No reports for this player yet.")
        return

    # Latest report
    latest = df_reports.iloc[0]
    st.subheader("Latest Report")
    st.write(
        f"{latest['report_date']} vs {latest['opponent']} ({latest['competition']}) — "
        f"{latest['minutes']} min, Rating: {latest['rating']}"
    )
    if latest.get("summary"):
        st.write(f"Summary: {latest['summary']}")

    # All reports table + CSV
    st.subheader("All Reports")
    st.dataframe(df_reports)
    csv = df_reports.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV", csv, f"{player['name']}_reports.csv", "text/csv"
    )
