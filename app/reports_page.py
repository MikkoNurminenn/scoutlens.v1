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

from datetime import date
from typing import Any, Dict, List, Callable

import streamlit as st
from postgrest.exceptions import APIError

from app.supabase_client import get_client
from app.db_tables import PLAYERS
from app.services.players import insert_player


POSITIONS = [
    "GK",
    "RB",
    "CB",
    "LB",
    "RWB",
    "LWB",
    "DM",
    "CM",
    "AM",
    "RW",
    "LW",
    "SS",
    "CF",
]

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

    with st.form("scout_report_minimal"):
        selected_player_id = st.selectbox(
            "Player",
            options=list(player_options.keys()),
            format_func=lambda x: player_options.get(x, ""),
            key="reports__selected_player_id",
        )
        report_date = st.date_input(
            "Report date", value=date.today(), key="reports__report_date"
        )
        competition = st.text_input("Competition", key="reports__competition")
        opponent = st.text_input("Opponent", key="reports__opponent")
        location = st.text_input("Location", key="reports__location")

        st.markdown("### Essential attributes")
        foot = st.selectbox(
            "Foot", ["right", "left", "both"], key="reports__foot"
        )
        use_pos_dropdown = st.checkbox(
            "Use position dropdown", value=True, key="reports__use_pos_dropdown"
        )
        if use_pos_dropdown:
            position = st.selectbox(
                "Position", POSITIONS, key="reports__position_dropdown"
            )
        else:
            position = st.text_input("Position", key="reports__position_text")

        col1, col2 = st.columns(2)
        with col1:
            technique = st.slider(
                "Technique", 1, 5, 3, key="reports__technique"
            )
            mental = st.slider(
                "Mental / GRIT", 1, 5, 3, key="reports__mental"
            )
        with col2:
            game_intel = st.slider(
                "Game intelligence", 1, 5, 3, key="reports__game_intelligence"
            )
            athletic = st.slider(
                "Athletic ability", 1, 5, 3, key="reports__athletic"
            )

        comments = st.text_area(
            "General comments / Conclusion", key="reports__comments"
        )

        submitted = st.form_submit_button("Save")

    if submitted:
        sb = get_client()
        position_val = position.strip() if isinstance(position, str) else position
        attributes = {
            "foot": foot,
            "position": position_val,
            "technique": technique,
            "game_intelligence": game_intel,
            "mental": mental,
            "athletic": athletic,
            "comments": comments,
        }
        payload = {
            "player_id": selected_player_id,
            "report_date": report_date.isoformat(),
            "competition": competition.strip() or None,
            "opponent": opponent.strip() or None,
            "location": location.strip() or None,
            "attributes": attributes,
        }
        try:
            sb.table("reports").insert(payload).execute()
            st.toast("Report saved ✅")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save report: {e}")

    st.divider()

    sb = get_client()
    rows = (
        sb.table("reports")
        .select("id,report_date,player:player_id(name,current_club),attributes")
        .order("report_date", desc=True)
        .limit(50)
        .execute()
        .data
    )
    if rows:
        table = []
        for r in rows:
            a = r.get("attributes") or {}
            player = r.get("player") or {}
            table.append(
                {
                    "Date": r.get("report_date"),
                    "Player": player.get("name", ""),
                    "Club": player.get("current_club", ""),
                    "Pos": a.get("position"),
                    "Foot": a.get("foot"),
                    "Tech": a.get("technique"),
                    "GI": a.get("game_intelligence"),
                    "MENT": a.get("mental"),
                    "ATH": a.get("athletic"),
                    "Comment": (
                        (a.get("comments") or "")[:60]
                        + (
                            "…"
                            if a.get("comments") and len(a.get("comments")) > 60
                            else ""
                        )
                    ),
                }
            )
        st.dataframe(table, use_container_width=True)
    else:
        st.caption("No reports yet.")

