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
from typing import Any, Dict, List, Callable

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError
import traceback

from supabase_client import get_client
from db_tables import PLAYERS, REPORTS
from services.players import insert_player

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_query(
    table_name: str, select: str = "*", order_by: str | None = None,
    desc: bool = False, limit: int | None = None,
):
    client = get_client()
    q = client.table(table_name).select(select)
    if order_by:
        q = q.order(order_by, desc=desc)
    if limit:
        q = q.limit(limit)
    try:
        return q.execute().data or []
    except APIError as e:
        st.error(
            f"Supabase APIError on {table_name}: {getattr(e, 'message', e)}"
        )
        return []


def _load_players() -> List[Dict[str, Any]]:
    """Return normalized players."""
    rows = _safe_query("players_v") or _safe_query(PLAYERS)
    norm: List[Dict[str, Any]] = []
    for r in rows:
        norm.append(
            {
                "id": r.get("id"),
                "name": r.get("name") or r.get("full_name") or r.get("player_name"),
                "position": r.get("position") or r.get("pos"),
                "nationality": r.get("nationality") or r.get("nation"),
                "current_club": r.get("current_club")
                or r.get("club")
                or r.get("team")
                or r.get("current_team"),
                "preferred_foot": r.get("preferred_foot") or r.get("foot"),
                "transfermarkt_url": r.get("transfermarkt_url") or r.get("tm_url"),
            }
        )
    return norm


def _insert_report(payload: Dict[str, Any]) -> bool:
    """Insert a new report into Supabase. Returns True on success."""
    client = get_client()
    try:
        client.table(REPORTS).insert(payload).execute()
        return True
    except Exception:
        st.error("❌ Save failed")
        st.code("".join(traceback.format_exc()), language="text")
        raise


def _list_reports() -> List[Dict[str, Any]]:
    """Return normalized reports with ordering fallbacks."""
    # Prefer VIEW; if schema cache wasn't refreshed yet, fallback to base table
    # Ordering strategy:
    # 1) Try kickoff_at desc (VIEW provides it via COALESCE)
    # 2) If that fails (e.g., querying base table without kickoff_at),
    #    retry created_at desc
    rows = _safe_query("reports", order_by="kickoff_at", desc=True)
    if not rows:
        rows = _safe_query("reports", order_by="created_at", desc=True)

    if not rows:
        # fallback to base table (some envs call scout_reports directly)
        rows = _safe_query("scout_reports", order_by="kickoff_at", desc=True)
        if not rows:
            rows = _safe_query("scout_reports", order_by="created_at", desc=True)

    norm: List[Dict[str, Any]] = []
    for r in rows:
        norm.append(
            {
                "id": r.get("id"),
                "title": r.get("title") or r.get("report_title"),
                "player_id": r.get("player_id"),
                "player_name": r.get("player_name"),
                "competition": r.get("competition"),
                "opponent": r.get("opponent"),
                "kickoff_at": r.get("kickoff_at") or r.get("match_datetime"),
                "location": r.get("location"),
                "ratings": r.get("ratings"),
                "tags": r.get("tags"),
                "notes": r.get("notes"),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
            }
        )
    return norm


def render_add_player_form(on_success: Callable | None = None) -> None:
    with st.form(key="players__add_form", border=True):
        name = st.text_input("Name*", "")
        position = st.text_input("Position", "")
        preferred_foot = st.selectbox("Preferred Foot", ["", "Right", "Left", "Both"])
        nationality = st.text_input("Nationality", "")
        current_club = st.text_input("Current Club", "")
        transfermarkt_url = st.text_input("Transfermarkt URL", "")

        submitted = st.form_submit_button("Create Player", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Name is required.")
                return

            payload = {
                "name": name.strip(),
                "position": position.strip() or None,
                "preferred_foot": preferred_foot or None,
                "nationality": nationality.strip() or None,
                "current_club": current_club.strip() or None,
                "transfermarkt_url": transfermarkt_url.strip() or None,
            }

            try:
                row = insert_player(payload)
                st.success(f"Player created: {row.get('name')} (id: {row.get('id')})")
                st.session_state["players__last_created"] = row
                if callable(on_success):
                    on_success(row)
            except APIError as e:
                st.error(f"Supabase error: {getattr(e, 'message', str(e))}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


def show_reports_page() -> None:
    """Render the reports page."""

    st.markdown("## 📝 Reports")
    def _on_player_created(row):
        st.session_state["reports__selected_player_id"] = row["id"]

    with st.expander("➕ Add Player", expanded=False):
        render_add_player_form(on_success=_on_player_created)

    players = _load_players()
    player_options = {p["id"]: p["name"] for p in players}

    with st.form("reports__new_report"):
        selected_player_id = st.selectbox(
            "Player",
            options=list(player_options.keys()),
            format_func=lambda x: player_options.get(x, ""),
            key="reports__selected_player_id",
        )
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
            "player_id": selected_player_id,
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

