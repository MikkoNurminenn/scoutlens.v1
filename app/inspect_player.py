"""Inspect Player page aligned with Reports schema (attributes JSON, 0–5)."""

from __future__ import annotations

from datetime import date
import textwrap
import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError

from app.ui import bootstrap_sidebar_auto_collapse
from app.supabase_client import get_client

bootstrap_sidebar_auto_collapse()


def _calc_age(dob_str: str | None) -> str:
    if not dob_str:
        return "—"
    dob = pd.to_datetime(dob_str, errors="coerce")
    if pd.isna(dob):
        return "—"
    today = date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return f"{years} yrs"


def _avg_0_5(*vals) -> float | None:
    nums = [float(v) for v in vals if v is not None and pd.notna(v)]
    if not nums:
        return None
    nums = [min(5.0, max(1.0, n)) for n in nums]
    return round(min(5.0, max(0.0, sum(nums) / len(nums))), 1)


def show_inspect_player() -> None:
    """Render the Inspect Player page (reads reports.attributes)."""
    st.title("🔍 Inspect Player")
    sb = get_client()

    # --- Players dropdown (essential fields only) ---
    try:
        players = (
            sb.table("players")
            .select(
                "id,name,position,current_club,nationality,date_of_birth,"
                "team_name,preferred_foot,transfermarkt_url"
            )
            .order("name")
            .execute()
            .data
            or []
        )
    except APIError as e:
        st.error(f"Failed to load players: {e}")
        return

    if not players:
        st.info("No players found. Create a player from Reports or Players first.")
        return

    ids = [p["id"] for p in players]
    labels = {
        p["id"]: f"{p['name']} ({p.get('current_club') or p.get('team_name') or '—'})"
        for p in players
    }
    default_id = st.session_state.get("inspect__player_id") or ids[0]
    try:
        default_idx = ids.index(default_id)
    except ValueError:
        default_idx = 0

    player_id = st.selectbox(
        "Player",
        options=ids,
        format_func=lambda x: labels.get(x, "—"),
        index=default_idx,
    )
    st.session_state["inspect__player_id"] = player_id
    player = next((p for p in players if p["id"] == player_id), players[0])

    # --- Player header (compact)
    st.subheader(player["name"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Position", player.get("position") or "—")
    c2.metric("Club", player.get("current_club") or player.get("team_name") or "—")
    c3.metric("Nationality", player.get("nationality") or "—")
    c4.metric("Age", _calc_age(player.get("date_of_birth")))

    with st.expander("Details"):
        tm = player.get("transfermarkt_url")
        st.write(
            {
                "Preferred foot": player.get("preferred_foot") or "—",
                "Date of birth": player.get("date_of_birth") or "—",
                "Transfermarkt": tm if tm else "—",
            }
        )
        if tm:
            st.markdown(f"[Open on Transfermarkt]({tm})")

    # --- Filters for reports ---
    st.markdown("### Match Reports")
    fc1, fc2 = st.columns([2, 1])
    comp_filter = fc1.text_input("Filter by competition (contains)", "")
    date_range = fc2.date_input(
        "Date range",
        value=(),
        help="Optional: filter reports between two dates",
    )

    # --- Reports query (reads attributes JSON) ---
    try:
        reports = (
            sb.table("reports")
            .select("id,report_date,competition,opponent,attributes")
            .eq("player_id", player_id)
            .order("report_date", desc=True)
            .limit(500)
            .execute()
            .data
            or []
        )
    except APIError as e:
        st.error(f"Failed to load reports: {e}")
        return

    if not reports:
        st.info("No reports yet for this player.")
        return

    # --- Build rows to MATCH Reports page: Date, Player, Club, Opponent, Competition, Pos, Foot, Tech, GI, MENT, ATH, Comments
    player_name = player.get("name") or ""
    player_club = player.get("current_club") or player.get("team_name") or ""

    rows = []
    for r in reports:
        a = r.get("attributes") or {}
        if not isinstance(a, dict):
            a = {}

        tech = pd.to_numeric(a.get("technique"), errors="coerce")
        gi   = pd.to_numeric(a.get("game_intelligence"), errors="coerce")
        ment = pd.to_numeric(a.get("mental"), errors="coerce")
        ath  = pd.to_numeric(a.get("athletic"), errors="coerce")

        comment = (a.get("comments") or "").strip()
        if len(comment) > 120:
            comment = textwrap.shorten(comment, width=120, placeholder="…")

        rows.append(
            {
                "Date": r.get("report_date"),
                "Player": player_name,
                "Club": player_club,
                "Opponent": r.get("opponent") or "",
                "Competition": r.get("competition") or "",
                "Pos": a.get("position"),
                "Foot": a.get("foot"),
                "Tech": float(tech) if pd.notna(tech) else None,
                "GI": float(gi) if pd.notna(gi) else None,
                "MENT": float(ment) if pd.notna(ment) else None,
                "ATH": float(ath) if pd.notna(ath) else None,
                "Comments": comment,
            }
        )

    df = pd.DataFrame(rows)

    # Types & filters
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # pyöritellään numerot yhteen desimaaliin (näyttö siisti, mutta sama sisältö)
    for col in ["Tech", "GI", "MENT", "ATH"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").round(1)

    if comp_filter:
        df = df[df["Competition"].fillna("").str.contains(comp_filter, case=False)]

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        if start and end:
            df = df[
                (df["Date"] >= pd.to_datetime(start)) &
                (df["Date"] <= pd.to_datetime(end))
            ]

    if df.empty:
        st.warning("No reports match the current filters.")
        return

    # Järjestys kuten Reports-sivulla
    cols_order = [
        "Date", "Player", "Club", "Opponent", "Competition",
        "Pos", "Foot", "Tech", "GI", "MENT", "ATH", "Comments",
    ]
    df = df[[c for c in cols_order if c in df.columns]].sort_values("Date", ascending=False)

    st.caption(f"Reports: **{len(df)}**")
    st.dataframe(df, use_container_width=True)

    # Exportit
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    json_bytes = df.to_json(orient="records", date_format="iso").encode("utf-8")
    st.download_button(
        "⬇️ Export CSV (filtered)",
        csv_bytes,
        file_name=f"{player['name']}_reports.csv",
        mime="text/csv",
    )
    st.download_button(
        "⬇️ Export JSON (filtered)",
        json_bytes,
        file_name=f"{player['name']}_reports.json",
        mime="application/json",
    )


__all__ = ["show_inspect_player"]
