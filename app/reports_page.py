"""Reports page for ScoutLens.

This page focuses on creating and listing scouting reports stored in Supabase.

Guidelines:
- use the shared Supabase client via get_client
- handle APIError gracefully and surface a friendly st.error message
- avoid any local JSON/SQLite storage – Supabase is the single source of truth
- UTC aware dates are used when inserting new reports
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Callable

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError
from .ui import bootstrap_sidebar_auto_collapse

from app.supabase_client import get_client
from app.db_tables import PLAYERS
from app.services.players import insert_player
from app.perf import track


bootstrap_sidebar_auto_collapse()


POSITIONS = [
    "GK","RB","CB","LB","RWB","LWB","DM","CM","AM","RW","LW","SS","CF",
]

# --- Essential attributes (1–5) + foot/position + comments ---

def render_essential_section() -> dict:
    st.subheader("Essential attributes (per match)")

    col1, col2 = st.columns(2)
    with col1:
        foot = st.selectbox("Foot", ["right", "left", "both"], index=0, key="reports__foot")
        use_dd = st.toggle("Use position dropdown", value=True, key="reports__pos_toggle")
    with col2:
        position = (
            st.selectbox("Position", POSITIONS, index=6, key="reports__pos_dd")
            if use_dd
            else st.text_input("Position (free text)", value="CM", key="reports__pos_txt")
        )

    c1, c2 = st.columns(2)
    with c1:
        technique = st.slider("Technique", 1, 5, 3, key="reports__tech")
        game_intel = st.slider("Game intelligence", 1, 5, 3, key="reports__gi")
    with c2:
        mental = st.slider("Mental / GRIT", 1, 5, 3, key="reports__mental")
        athletic = st.slider("Athletic ability", 1, 5, 3, key="reports__ath")

    comments = st.text_area("General comments / conclusion", key="reports__comments", height=120)

    return {
        "foot": foot,
        "position": position,
        "technique": technique,
        "game_intelligence": game_intel,
        "mental": mental,
        "athletic": athletic,
        "comments": comments,
    }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_query(
    table_name: str,
    select: str = "*",
    order_by: str | None = None,
    desc: bool = False,
    limit: int | None = None,
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
        st.error(f"Supabase APIError on {table_name}: {getattr(e, 'message', e)}")
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
                "current_club": r.get("current_club") or r.get("club") or r.get("team") or r.get("current_team"),
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

@st.cache_data(ttl=60, show_spinner=False)
def list_latest_reports(limit: int = 50):
    sb = get_client()
    with track("reports:fetch"):
        return (
            sb.table("reports")
            .select(
                "id,report_date,competition,opponent,position_played,rating,"
                "player:player_id(name,current_club),attributes"
            )
            .order("report_date", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )


def show_reports_page() -> None:
    """Render the reports page."""
    st.markdown("## 📝 Reports")

    def _on_player_created(row):
        st.session_state["reports__selected_player_id"] = row["id"]

    with st.expander("➕ Add Player", expanded=False):
        render_add_player_form(on_success=_on_player_created)

    players = _load_players()
    player_options = {p["id"]: p["name"] for p in players}

    # Älä näytä raporttilomaketta, jos ei ole vielä yhtään pelaajaa
    if not player_options:
        st.info("No players yet — add one above to create your first report.")
        st.divider()
    else:
        with st.form("scout_report_minimal"):
            selected_player_id = st.selectbox(
                "Player",
                options=list(player_options.keys()),
                format_func=lambda x: player_options.get(x, ""),
                key="reports__selected_player_id",
            )
            report_date = st.date_input("Report date", value=date.today(), key="reports__report_date")
            competition = st.text_input("Competition", key="reports__competition")
            opponent = st.text_input("Opponent", key="reports__opponent")
            location = st.text_input("Location", key="reports__location")

            st.divider()
            attrs = render_essential_section()
            submitted = st.form_submit_button("Save")

        if submitted:
            sb = get_client()
            pos_val = attrs.get("position")
            if isinstance(pos_val, str):
                attrs["position"] = pos_val.strip()

            payload = {
                "player_id": selected_player_id,
                "report_date": report_date.isoformat(),
                "competition": (competition or "").strip() or None,
                "opponent": (opponent or "").strip() or None,
                "location": (location or "").strip() or None,
                "attributes": attrs,
            }
            try:
                sb.table("reports").insert(payload).execute()
                list_latest_reports.clear()
                st.toast("Report saved ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save report: {e}")

    st.divider()

    try:
        rows = list_latest_reports()
    except APIError as e:
        st.error(f"Supabase error: {getattr(e, 'message', e)}")
        rows = []

    if rows:
        data = []
        for r in rows:
            a = r.get("attributes") or {}
            player = r.get("player") or {}

            # Lyhennetään kommentit siististi
            txt = (a.get("comments") or "").strip()
            if len(txt) > 100:
                txt = txt[:97] + "..."

            data.append(
                {
                    "Date": r.get("report_date"),
                    "Player": player.get("name", ""),
                    "Club": player.get("current_club", ""),
                    "Opponent": r.get("opponent") or "",
                    "Competition": r.get("competition") or "",
                    "Pos": a.get("position"),
                    "Foot": a.get("foot"),
                    "Tech": a.get("technique"),
                    "GI": a.get("game_intelligence"),
                    "MENT": a.get("mental"),
                    "ATH": a.get("athletic"),
                    "Comments": txt,
                }
            )
        df = pd.DataFrame(data)

        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            q_opp = st.text_input("Filter by opponent", placeholder="e.g. Millonarios", key="reports__f_opp")
        with c2:
            q_comp = st.text_input("Filter by competition", placeholder="e.g. Liga", key="reports__f_comp")
        with c3:
            min_ment = st.slider("MENT ≥", 1, 5, 1, key="reports__f_ment")

        def _apply_filters(df_in: pd.DataFrame) -> pd.DataFrame:
            out = df_in.copy()
            if q_opp:
                out = out[out["Opponent"].str.contains(q_opp, case=False, na=False)]
            if q_comp:
                out = out[out["Competition"].str.contains(q_comp, case=False, na=False)]
            if "MENT" in out.columns and min_ment > 1:
                out = out[(out["MENT"].fillna(0) >= min_ment)]
            return out

        df_f = _apply_filters(df)

        order = [
            "Date","Player","Club","Opponent","Competition",
            "Pos","Foot","Tech","GI","MENT","ATH","Comments",
        ]
        for col in order:
            if col not in df_f.columns:
                df_f[col] = None
        df_f = df_f[order]

        if "Foot" in df_f.columns:
            df_f["Foot"] = df_f["Foot"].fillna("").astype(str).str.capitalize()

        def _style_vals(s: pd.Series) -> list[str]:
            colors: list[str] = []
            for v in s:
                if pd.isna(v):
                    colors.append("")
                elif isinstance(v, (int, float)):
                    if v >= 4:
                        colors.append("background-color: rgba(0, 200, 120, 0.15)")
                    elif v <= 2:
                        colors.append("background-color: rgba(255, 80, 80, 0.15)")
                    else:
                        colors.append("")
                else:
                    colors.append("")
            return colors

        with track("reports:style"):
            styler = (
                df_f.style
                .apply(_style_vals, subset=["Tech", "GI", "MENT", "ATH"])
                .set_properties(subset=["Comments"], **{"text-align": "left", "white-space": "pre-wrap"})
            )

        cap_col, btn_col = st.columns([3, 1])
        with cap_col:
            st.caption(f"Showing {len(df_f)} / {len(df)} reports")
        with btn_col:
            if st.button("Clear filters", key="reports__clear_filters"):
                st.session_state.update(
                    {"reports__f_opp": "", "reports__f_comp": "", "reports__f_ment": 1}
                )
                st.rerun()

        with track("reports:table"):
            st.dataframe(styler, use_container_width=True, hide_index=True, height=400)
    else:
        st.caption("No reports yet.")
