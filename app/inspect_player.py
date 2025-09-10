"""Inspect Player page for viewing player profile and linked reports (0–5 rating)."""

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


def show_inspect_player() -> None:
    """Render the Inspect Player page (clean columns, rating 0–5)."""
    st.title("🔍 Inspect Player")
    sb = get_client()

    # --- Players dropdown (only essential fields) ---
    try:
        players = (
            sb.table("players")
            .select(
                "id,name,position,current_club,nationality,date_of_birth,"
                "team_name,preferred_foot,club_number,scout_rating,transfermarkt_url"
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

    # Map id -> label and keep stable order
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

    # --- Player header (compact & useful) ---
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
                "Preferred foot": player.get("preferred_foot"),
                "Number": player.get("club_number"),
                "Scout rating": player.get("scout_rating"),
                "Date of birth": player.get("date_of_birth"),
                "Transfermarkt": tm if tm else "—",
            }
        )
        if tm:
            st.markdown(f"[Open on Transfermarkt]({tm})")

    # --- Lightweight filters for reports ---
    st.markdown("### Match Reports")
    fc1, fc2 = st.columns([2, 1])
    comp_filter = fc1.text_input("Filter by competition (contains)", "")
    date_range = fc2.date_input(
        "Date range",
        value=(),
        help="Optional: filter reports between two dates",
    )

    # --- Reports query (attributes-based) ---
    try:
        reports = (
            sb.table("reports")
            .select("id,report_date,competition,opponent,location,attributes")
            .eq("player_id", player_id)
            .order("report_date", desc=True)
            .limit(500)
            .execute()
            .data
            or []
        )
    except APIError as e:  # pragma: no cover - UI error handling
        st.error(f"Failed to load reports: {e}")
        return

    if not reports:
        st.info("No reports yet for this player.")
        return

    # --- Data shaping & filters ---
    df = pd.DataFrame(reports)
    if "report_date" in df:
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")

    # expand attributes jsonb
    attrs = df.pop("attributes", pd.Series(dtype="object"))
    if not attrs.empty:
        attrs = attrs.apply(lambda a: a or {})
        for key in [
            "position",
            "foot",
            "technique",
            "game_intelligence",
            "mental",
            "athletic",
            "comments",
        ]:
            df[key] = attrs.apply(lambda x, k=key: x.get(k))

    # numeric conversions
    for col in ["technique", "game_intelligence", "mental", "athletic"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if {"technique", "game_intelligence", "mental", "athletic"}.issubset(df.columns):
        df["rating"] = df[["technique", "game_intelligence", "mental", "athletic"]].mean(
            axis=1, skipna=True
        )
        df["rating"] = df["rating"].round(1)

    # text filter
    if comp_filter:
        df = df[df["competition"].fillna("").str.contains(comp_filter, case=False)]

    # date range filter
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        if start and end:
            df = df[
                (df["report_date"] >= pd.to_datetime(start))
                & (df["report_date"] <= pd.to_datetime(end))
            ]

    if df.empty:
        st.warning("No reports match the current filters.")
        return

    # keep only clean columns and friendly headers
    cols_order = [
        "report_date",
        "competition",
        "opponent",
        "position",
        "foot",
        "technique",
        "game_intelligence",
        "mental",
        "athletic",
        "rating",
        "comments",
    ]
    df = df[[c for c in cols_order if c in df.columns]].copy()

    if "comments" in df:
        df["comments"] = df["comments"].fillna("").apply(
            lambda s: textwrap.shorten(str(s), width=120, placeholder="…")
        )

    ratings = pd.to_numeric(df.get("rating", pd.Series(dtype=float)), errors="coerce").dropna()
    avg_rating = round(float(ratings.mean()), 2) if not ratings.empty else None

    df = df.rename(
        columns={
            "report_date": "Date",
            "competition": "Competition",
            "opponent": "Opponent",
            "position": "Pos",
            "foot": "Foot",
            "technique": "Technique",
            "game_intelligence": "Game Intelligence",
            "mental": "Mental",
            "athletic": "Athletic",
            "rating": "Rating (0–5)",
            "comments": "Comments",
        }
    ).sort_values("Date", ascending=False)

    stats = f"Reports: **{len(df)}**"
    if avg_rating is not None:
        stats += f" | Avg rating: **{avg_rating} / 5**"
    st.caption(stats)

    # --- Table & exports ---
    st.dataframe(df, use_container_width=True)

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
