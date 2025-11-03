"""Reports page for ScoutLens.

This page focuses on creating and listing scouting reports stored in Supabase.

Guidelines:
- use the shared Supabase client via get_client
- handle APIError gracefully and surface a friendly st.error message
- avoid any local JSON/SQLite storage – Supabase is the single source of truth
- UTC aware dates are used when inserting new reports
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError

try:
    from app.ui import bootstrap_sidebar_auto_collapse
except ImportError:  # pragma: no cover - compatibility shim for legacy packages
    from app.ui.sidebar import bootstrap_sidebar_auto_collapse

from app.supabase_client import get_client
from app.db_tables import PLAYERS
from app.services.players import insert_player
from app.perf import track
from app.report_payload import build_report_payload, serialize_report_attributes


FILTER_DEFAULTS: dict[str, Any] = {
    "reports__f_opp": "",
    "reports__f_comp": "",
    "reports__f_ment": 1,
    "reports__f_foot": [],
    "reports__f_date_toggle": False,
    "reports__f_date": None,
}


def _reset_report_filters() -> None:
    """Reset all report filter widgets back to their defaults."""

    for key, default in FILTER_DEFAULTS.items():
        if default is None:
            st.session_state.pop(key, None)
        else:
            st.session_state[key] = default
    # Ensure optional selections don't keep pointing to filtered-out rows
    st.session_state.pop("reports__inspect_select", None)


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
            else st.text_input(
                "Position (free text)",
                value="CM",
                key="reports__pos_txt",
                autocomplete="off",
            )
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

@st.cache_data(ttl=60, show_spinner=False)
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


@st.cache_data(ttl=30, show_spinner=False)
def _load_match_target_players(match_id: str) -> List[Dict[str, Any]]:
    if not match_id:
        return []
    client = get_client()
    try:
        res = (
            client.table("match_targets")
            .select("player_id,player:player_id(name,current_club)")
            .eq("match_id", match_id)
            .execute()
        )
    except APIError as e:
        st.error(f"Failed to load match targets: {getattr(e, 'message', e)}")
        return []

    rows = res.data or []
    players: List[Dict[str, Any]] = []
    for row in rows:
        pid = row.get("player_id")
        player_info = row.get("player") or {}
        if pid:
            players.append(
                {
                    "id": pid,
                    "name": player_info.get("name"),
                    "current_club": player_info.get("current_club"),
                }
            )
    return players

def render_add_player_form(on_success: Callable | None = None) -> None:
    with st.form(key="players__add_form", border=True):
        name = st.text_input("Name*", "", autocomplete="off")
        position = st.text_input("Position", "", autocomplete="off")
        preferred_foot = st.selectbox("Preferred Foot", ["", "Right", "Left", "Both"])
        nationality = st.text_input("Nationality", "", autocomplete="off")
        current_club = st.text_input("Current Club", "", autocomplete="off")
        transfermarkt_url = st.text_input("Transfermarkt URL", "", autocomplete="off")

        submitted = st.form_submit_button("Create Player", use_container_width=True, type="primary")
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

def _load_players_by_ids(ids: List[str]) -> Dict[str, Dict[str, Any]]:
    unique_ids = sorted({pid for pid in ids if pid})
    if not unique_ids:
        return {}

    sb = get_client()
    players: Dict[str, Dict[str, Any]] = {}
    chunk_size = 50
    for start in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[start : start + chunk_size]
        try:
            res = (
                sb.table("players")
                .select("id,name,current_club")
                .in_("id", chunk)
                .execute()
            )
            rows = res.data or []
        except APIError as e:
            st.error(f"Supabase error while loading players: {getattr(e, 'message', e)}")
            return players

        for row in rows:
            pid = row.get("id")
            if pid:
                players[pid] = {
                    "name": row.get("name"),
                    "current_club": row.get("current_club"),
                }
    return players


@st.cache_data(ttl=300, show_spinner=False)
def _reports_supports_player_name() -> bool:
    """Check whether the reports table exposes the player_name column."""

    sb = get_client()
    try:
        sb.table("reports").select("player_name").limit(1).execute()
        return True
    except APIError as e:
        message = getattr(e, "message", str(e))
        if message and "player_name" in message:
            print("reports.player_name missing from Supabase schema:", message)
            return False
        raise


@st.cache_data(ttl=60, show_spinner=False)
def list_latest_reports(limit: int = 50, include_player_name: bool = True):
    sb = get_client()
    with track("reports:fetch"):
        try:
            select_cols = [
                "id",
                "player_id",
                "report_date",
                "competition",
                "opponent",
                "position_played",
                "rating",
                "attributes",
            ]
            if include_player_name:
                select_cols.insert(2, "player_name")

            response = (
                sb.table("reports")
                .select(",".join(select_cols))
                .order("report_date", desc=True)
                .limit(limit)
                .execute()
            )
            rows = response.data or []
        except APIError as e:
            st.error(f"Supabase error: {getattr(e, 'message', e)}")
            return []
    player_map = _load_players_by_ids([row.get("player_id") for row in rows])

    for row in rows:
        pid = row.get("player_id")
        if pid and pid in player_map:
            row["player"] = player_map[pid]
        else:
            row["player"] = {
                "name": row.get("player_name"),
                "current_club": None,
            }
        row["attributes"] = serialize_report_attributes(row.get("attributes") or {})
        if not include_player_name:
            row.setdefault("player_name", None)

    return rows


def show_reports_page() -> None:
    """Render the reports page."""
    st.markdown("## 📝 Reports")

    try:
        supports_player_name = _reports_supports_player_name()
    except APIError as e:
        st.error(f"Failed to inspect reports schema: {getattr(e, 'message', e)}")
        supports_player_name = True
    else:
        if not supports_player_name and not st.session_state.get(
            "reports__player_name_warned", False
        ):
            st.warning(
                "Supabase schema is missing reports.player_name — run the latest migrations. "
                "Player names will be loaded via fallback in the meantime."
            )
            st.session_state["reports__player_name_warned"] = True

    def _on_player_created(row):
        st.session_state["reports__selected_player_id"] = row["id"]

    with st.expander("➕ Add Player", expanded=False):
        render_add_player_form(on_success=_on_player_created)

    prefill_match_id = st.session_state.get("report_prefill_match_id")
    target_players = _load_match_target_players(prefill_match_id) if prefill_match_id else []
    target_ids = [p.get("id") for p in target_players if p.get("id")]

    players = _load_players()
    if target_ids:
        players = [p for p in players if p.get("id") in target_ids]
        st.caption("Match prefill active — choose from saved 🎯 targets.")
        if players and st.session_state.get("reports__selected_player_id") not in target_ids:
            st.session_state["reports__selected_player_id"] = target_ids[0]
    elif prefill_match_id:
        st.info("Selected match has no saved targets yet. Add targets to limit choices.")

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
            competition = st.text_input(
                "Competition", key="reports__competition", autocomplete="off"
            )
            opponent = st.text_input("Opponent", key="reports__opponent", autocomplete="off")
            location = st.text_input("Location", key="reports__location", autocomplete="off")

            st.divider()
            attrs = render_essential_section()
            submitted = st.form_submit_button("Save", type="primary")

        if submitted:
            sb = get_client()
            pos_val = attrs.get("position")
            if isinstance(pos_val, str):
                pos_clean = pos_val.strip()
                attrs["position"] = pos_clean or None

            payload = build_report_payload(
                player_id=selected_player_id,
                player_name=player_options.get(selected_player_id),
                report_date=report_date,
                competition=competition,
                opponent=opponent,
                location=location,
                attrs=attrs,
                match_id=prefill_match_id,
                include_player_name=supports_player_name,
            )

            inserted = False
            try:
                sb.table("reports").insert(payload).execute()
                inserted = True
            except APIError as e:
                message = getattr(e, "message", str(e))
                if message and "player_name" in message and supports_player_name:
                    _reports_supports_player_name.clear()
                    supports_player_name = False
                    st.session_state["reports__player_name_warned"] = True
                    st.warning(
                        "Supabase schema is missing reports.player_name — run the latest migrations. "
                        "Player names will be loaded via fallback in the meantime."
                    )
                    fallback_payload = {
                        k: v for k, v in payload.items() if k != "player_name"
                    }
                    try:
                        sb.table("reports").insert(fallback_payload).execute()
                        inserted = True
                    except APIError as retry_err:
                        st.error(
                            f"Failed to save report: {getattr(retry_err, 'message', retry_err)}"
                        )
                else:
                    st.error(f"Failed to save report: {message}")
            except Exception as e:  # pragma: no cover - unexpected runtime issues
                st.error(f"Failed to save report: {e}")

            if inserted:
                list_latest_reports.clear()
                if prefill_match_id:
                    st.session_state.pop("report_prefill_match_id", None)
                st.toast("Report saved ✅")
                st.rerun()

    st.divider()

    rows = list_latest_reports(include_player_name=supports_player_name)

    if rows:
        data: List[Dict[str, Any]] = []
        row_lookup: Dict[str, Dict[str, Any]] = {}
        ordered_ids: List[str] = []
        for idx, r in enumerate(rows):
            a = r.get("attributes") or {}
            player = r.get("player") or {}

            # Lyhennetään kommentit siististi
            txt = (a.get("comments") or "").strip()
            if len(txt) > 100:
                txt = txt[:97] + "..."

            row_id = str(r.get("id") or f"row-{idx}")
            ordered_ids.append(row_id)
            row_lookup[row_id] = r

            data.append(
                {
                    "_id": row_id,
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

        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        with c1:
            q_opp = st.text_input(
                "Filter by opponent",
                placeholder="e.g. Millonarios",
                key="reports__f_opp",
                autocomplete="off",
            )
        with c2:
            q_comp = st.text_input(
                "Filter by competition",
                placeholder="e.g. Liga",
                key="reports__f_comp",
                autocomplete="off",
            )
        with c3:
            min_ment = st.slider("MENT ≥", 1, 5, 1, key="reports__f_ment")
        with c4:
            enable_dates = st.toggle(
                "Use date range",
                value=False,
                key="reports__f_date_toggle",
                help="Limit the list to reports inside a specific window.",
            )

        foot_choices: list[str] = []
        if "Foot" in df.columns:
            foot_choices = sorted(
                v
                for v in df["Foot"].fillna("").astype(str).str.capitalize().unique()
                if v
            )
        c5, _ = st.columns([1, 3])
        with c5:
            foot_filter = st.multiselect(
                "Foot",
                options=foot_choices,
                default=[],
                key="reports__f_foot",
                help="Show only reports with these preferred foot values.",
                disabled=not foot_choices,
            )

        if enable_dates:
            default_end = date.today()
            default_start = default_end - timedelta(days=90)
            stored_range = st.session_state.get("reports__f_date")
            if not (isinstance(stored_range, tuple) and len(stored_range) == 2):
                stored_range = (default_start, default_end)
                st.session_state["reports__f_date"] = stored_range
            date_range = st.date_input(
                "Date range",
                value=stored_range,
                key="reports__f_date",
                help="Filter reports between two dates (inclusive).",
            )
        else:
            date_range = ()

        def _apply_filters(df_in: pd.DataFrame) -> pd.DataFrame:
            out = df_in.copy()
            if "Date" in out.columns:
                out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
            if q_opp and "Opponent" in out.columns:
                out = out[
                    out["Opponent"].fillna("").astype(str).str.contains(q_opp, case=False)
                ]
            if q_comp and "Competition" in out.columns:
                out = out[
                    out["Competition"].fillna("").astype(str).str.contains(q_comp, case=False)
                ]
            if "MENT" in out.columns and min_ment > 1:
                out = out[(out["MENT"].fillna(0) >= min_ment)]
            if foot_filter and "Foot" in out.columns:
                out = out[
                    out["Foot"].fillna("").astype(str).str.capitalize().isin(foot_filter)
                ]
            if enable_dates and isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = date_range
                if start and end:
                    start_ts = pd.to_datetime(start)
                    end_ts = pd.to_datetime(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                    out = out[(out["Date"] >= start_ts) & (out["Date"] <= end_ts)]
            return out

        df_f = _apply_filters(df)
        filtered_ids: List[str] = []
        if "_id" in df_f.columns:
            filtered_ids = (
                df_f["_id"].dropna().astype(str).tolist()
            )
            df_f = df_f.drop(columns=["_id"])

        order = [
            "Date","Player","Club","Opponent","Competition",
            "Pos","Foot","Tech","GI","MENT","ATH","Comments",
        ]
        for col in order:
            if col not in df_f.columns:
                df_f[col] = None
        df_f = df_f[order]

        if "Date" in df_f.columns:
            df_f["Date"] = pd.to_datetime(df_f["Date"], errors="coerce")

        for col in ["Tech", "GI", "MENT", "ATH"]:
            if col in df_f.columns:
                df_f[col] = pd.to_numeric(df_f[col], errors="coerce").round(1)

        if "Foot" in df_f.columns:
            df_f["Foot"] = df_f["Foot"].fillna("").astype(str).str.capitalize()

        if "Date" in df_f.columns:
            df_f["Date"] = df_f["Date"].dt.strftime("%Y-%m-%d")

        if not df_f.empty:
            metrics: dict[str, float | None] = {}
            for col in ["Tech", "GI", "MENT", "ATH"]:
                if col in df_f.columns:
                    avg_val = pd.to_numeric(df_f[col], errors="coerce").dropna().mean()
                    metrics[col] = round(float(avg_val), 1) if pd.notna(avg_val) else None
                else:
                    metrics[col] = None

            summary_cols = st.columns(5)
            def _fmt_metric(value: float | None) -> str:
                return f"{value:.1f}" if value is not None else "—"

            summary_cols[0].metric("Reports", len(df_f))
            summary_cols[1].metric("Avg Tech", _fmt_metric(metrics.get("Tech")))
            summary_cols[2].metric("Avg GI", _fmt_metric(metrics.get("GI")))
            summary_cols[3].metric("Avg MENT", _fmt_metric(metrics.get("MENT")))
            summary_cols[4].metric("Avg ATH", _fmt_metric(metrics.get("ATH")))
        def _highlight_class(v: float | None) -> str:
            if pd.isna(v):
                return ""
            if v >= 4:
                return "sl-highlight"
            if v <= 2:
                return "sl-highlight-error"
            return "sl-highlight-warning"

        classes = pd.DataFrame("", index=df_f.index, columns=df_f.columns)
        for col in ["Tech", "GI", "MENT", "ATH"]:
            if col in classes.columns:
                classes[col] = df_f[col].apply(_highlight_class)

        with track("reports:style"):
            styler = (
                df_f.style.set_td_classes(classes)
                .format({col: "{:.1f}" for col in ["Tech", "GI", "MENT", "ATH"]})
                .set_properties(
                    subset=["Comments"],
                    **{"text-align": "left", "white-space": "pre-wrap"},
                )
            )

        cap_col, btn_col = st.columns([3, 1])
        with cap_col:
            st.caption(f"Showing {len(df_f)} / {len(df)} reports")
        with btn_col:
            if st.button("Clear filters", key="reports__clear_filters", type="secondary"):
                _reset_report_filters()
                st.rerun()

        with track("reports:table"):
            st.dataframe(styler, use_container_width=True, hide_index=True, height=400)

        if not df_f.empty:
            csv_bytes = df_f.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Export CSV",
                csv_bytes,
                file_name="reports_filtered.csv",
                mime="text/csv",
            )

        inspector_ids = [rid for rid in (filtered_ids or ordered_ids) if rid in row_lookup]

        if inspector_ids:
            def _format_label(row: Dict[str, Any]) -> str:
                player_info = row.get("player") or {}
                player_name = (
                    player_info.get("name")
                    or row.get("player_name")
                    or "Unknown player"
                )
                date_val = row.get("report_date") or "—"
                opponent = row.get("opponent") or ""
                competition = row.get("competition") or ""
                parts = [str(date_val), player_name]
                if opponent:
                    parts.append(f"vs {opponent}")
                if competition:
                    parts.append(competition)
                return " · ".join(parts)

            labels: Dict[str, str] = {}
            for rid in inspector_ids:
                row = row_lookup.get(rid)
                if not row:
                    continue
                labels[rid] = _format_label(row)

            valid_ids = [rid for rid in inspector_ids if rid in labels]

            if valid_ids:
                with st.expander("🔍 Inspect report details", expanded=False):
                    stored_selection = st.session_state.get("reports__inspect_select")
                    try:
                        default_index = valid_ids.index(stored_selection)
                    except (ValueError, TypeError):
                        default_index = 0

                    selected_id = st.selectbox(
                        "Select report",
                        options=valid_ids,
                        format_func=lambda x: labels.get(x, x),
                        index=default_index,
                        key="reports__inspect_select",
                    )

                    selected_row = row_lookup.get(selected_id)
                    if not selected_row:
                        st.info("Unable to load the selected report details.")
                    else:
                        attrs = selected_row.get("attributes") or {}
                        player = selected_row.get("player") or {}

                        def _display_field(col, label: str, value: Optional[Any]) -> None:
                            if value is None:
                                display_value = "—"
                            elif isinstance(value, str):
                                display_value = value.strip() or "—"
                            else:
                                display_value = str(value)
                            col.markdown(f"**{label}**\n\n{display_value}")

                        meta_cols_top = st.columns(3)
                        _display_field(meta_cols_top[0], "Player", player.get("name") or selected_row.get("player_name"))
                        _display_field(meta_cols_top[1], "Club", player.get("current_club"))
                        _display_field(meta_cols_top[2], "Report date", selected_row.get("report_date"))

                        meta_cols_bottom = st.columns(3)
                        _display_field(meta_cols_bottom[0], "Competition", selected_row.get("competition"))
                        _display_field(meta_cols_bottom[1], "Opponent", selected_row.get("opponent"))
                        _display_field(
                            meta_cols_bottom[2],
                            "Position",
                            attrs.get("position") or selected_row.get("position_played"),
                        )

                        rating_cols = st.columns(4)

                        def _fmt_rating(value: Any) -> str:
                            try:
                                num = float(value)
                            except (TypeError, ValueError):
                                return "—"
                            if pd.isna(num):
                                return "—"
                            return f"{num:.1f}"

                        rating_map = [
                            ("Technique", attrs.get("technique")),
                            ("Game intelligence", attrs.get("game_intelligence")),
                            ("Mental", attrs.get("mental")),
                            ("Athletic", attrs.get("athletic")),
                        ]

                        for col, (label, value) in zip(rating_cols, rating_map):
                            col.metric(label, _fmt_rating(value))

                        comment = attrs.get("comments")
                        if comment:
                            st.markdown("**Comments**")
                            st.write(comment)
                        else:
                            st.caption("No comments recorded for this report.")

                        with st.expander("Show raw attributes", expanded=False):
                            st.json(attrs)
    else:
        st.caption("No reports yet.")
