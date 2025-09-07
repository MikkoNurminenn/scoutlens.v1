"""Reports page for ScoutLens.

This page focuses on creating and listing scouting reports stored in Supabase.

The implementation is intentionally minimal but follows the repository's
guidelines:

* use the shared Supabase client via ``get_client``
* handle ``APIError`` gracefully and surface a friendly ``st.error`` message
* avoid any local JSON/SQLite storage – Supabase is the single source of truth
* UTC aware dates are used when inserting new reports

This file introduces a ``show_reports_page`` function which is wired into the
main navigation in ``app.py``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError

from supabase_client import get_client
from db_tables import PLAYERS, REPORTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_players() -> List[Dict[str, Any]]:
    """Return all players ordered by name."""
    client = get_client()
    try:
        res = (
            client.table(PLAYERS)
            .select("id,name,current_club")
            .order("name")
            .execute()
        )
        return res.data or []
    except APIError as e:
        st.error("Failed to load players from Supabase.")
        st.exception(e)
        return []


def _insert_report(payload: Dict[str, Any]) -> bool:
    """Insert a new report into Supabase. Returns True on success."""
    client = get_client()
    try:
        client.table(REPORTS).insert(payload).execute()
        return True
    except APIError as e:
        st.error("Could not save report to Supabase.")
        st.exception(e)
        return False


def _list_reports(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch latest reports joined with player name and club."""
    client = get_client()
    try:
        res = (
            client.table(REPORTS)
            .select(
                "id,report_date,competition,opponent,position_played,rating,"
                "player:player_id(name,current_club)"
            )
            .order("report_date", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except APIError as e:
        st.error("Failed to load reports from Supabase.")
        st.exception(e)
        return []


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


def show_reports_page() -> None:
    """Render the reports page."""

    st.markdown("## 📝 Reports")

    players = _load_players()
    player_options = {p["name"]: p["id"] for p in players}

    with st.form("reports__new_report"):
        selected_name = st.selectbox("Player", options=list(player_options.keys()))
        report_date = st.date_input("Report date", value=date.today())
        competition = st.text_input("Competition")
        opponent = st.text_input("Opponent")
        location = st.text_input("Location")
        position_played = st.text_input("Position played")
        minutes = st.number_input("Minutes", min_value=0, max_value=120, step=1)
        rating = st.number_input("Rating", min_value=0.0, max_value=10.0, step=0.1)
        strengths = st.text_area("Strengths")
        weaknesses = st.text_area("Weaknesses")
        notes = st.text_area("Notes")
        scout_name = st.text_input("Scout name")

        submitted = st.form_submit_button("Save")

    if submitted:
        payload = {
            "player_id": player_options.get(selected_name),
            "report_date": report_date.isoformat(),
            "competition": competition.strip() or None,
            "opponent": opponent.strip() or None,
            "location": location.strip() or None,
            "position_played": position_played.strip() or None,
            "minutes": int(minutes) if minutes else None,
            "rating": float(rating),
            "strengths": strengths.strip() or None,
            "weaknesses": weaknesses.strip() or None,
            "notes": notes.strip() or None,
            "scout_name": scout_name.strip() or None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        if _insert_report(payload):
            st.success("Report saved")
            st.experimental_rerun()

    st.divider()

    rows = _list_reports()
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df)
    else:
        st.caption("No reports yet.")

