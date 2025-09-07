# scout_reporter.py — Supabase-backed Scout Match Reporter (clean)
from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Tuple, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import plotly.express as px

from supabase_client import get_client
from data_utils import list_teams, list_players_by_team  # käyttää Supabasea
from time_utils import to_tz
from data_sanitize import clean_jsonable

REQUIRED_COLS = [
    "id",
    "created_at",
    "home_team",
    "away_team",
    "competition",
    "location",
    "kickoff_at",
    "notes",
    "targets",
    "scout",
    "rating",
]


def ensure_columns(df: pd.DataFrame | None) -> pd.DataFrame:
    """Ensure df has all REQUIRED_COLS with safe defaults and consistent order."""
    if df is None or isinstance(df, list):
        df = pd.DataFrame()
    if df.empty:
        return pd.DataFrame({c: [] for c in REQUIRED_COLS})
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = [] if col in ("targets",) else ""
    return df[
        [c for c in REQUIRED_COLS if c in df.columns]
        + [c for c in df.columns if c not in REQUIRED_COLS]
    ]


def safe_unique(df: pd.DataFrame | None, col: str) -> list[str]:
    """Return sorted unique non-empty string values for df[col]; [] if df/col missing."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or col not in df.columns:
        return []
    s = df[col].dropna()
    vals = {str(v).strip() for v in s if str(v).strip()}
    return sorted(vals)

# ---------------- Mini CSS helper ----------------
def _inject_css_once(key: str, css_html: str):
    sskey = f"__css_injected__{key}"
    if not st.session_state.get(sskey):
        st.markdown(css_html, unsafe_allow_html=True)
        st.session_state[sskey] = True

# ---------------- Supabase: shortlistit ----------------
def list_shortlists() -> List[str]:
    client = get_client()
    if not client:
        return []
    res = client.table("shortlists").select("name").execute()
    names = [r.get("name") for r in (res.data or []) if r.get("name")]
    return sorted(set(names))

def get_shortlist_members(shortlist_name: str) -> List[str]:
    client = get_client()
    if not client:
        return []
    res = (
        client.table("shortlists")
        .select("player_id")
        .eq("name", shortlist_name)
        .execute()
    )
    return [str(r.get("player_id")) for r in (res.data or []) if r.get("player_id")]

# ---------------- Pelaajadata koosteeksi ----------------
def _normalize_player_record(p: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(p.get("id") or p.get("PlayerID") or p.get("player_id") or "").strip(),
        "name": str(p.get("name") or p.get("Name") or "").strip(),
        "team_name": str(p.get("team_name") or p.get("Team") or p.get("team") or "").strip(),
        "position": str(p.get("position") or p.get("Position") or "").strip(),
    }

def get_all_players() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for t in list_teams() or []:
        try:
            players = list_players_by_team(t) or []
        except Exception:
            players = []
        if isinstance(players, pd.DataFrame):
            for _, row in players.iterrows():
                out.append(_normalize_player_record(row.to_dict()))
        else:
            for p in players:
                out.append(_normalize_player_record(p))
    # dedup id:n mukaan
    seen = set(); uniq = []
    for p in out:
        pid = p.get("id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        uniq.append(p)
    return uniq

# ---------------- Ottelut & raportit (Supabase) ----------------
from postgrest.exceptions import APIError


def list_matches() -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
    try:
        res = (
            client.table("matches")
            .select("*")
            .order("kickoff_at", desc=True)
            .execute()
        )
        return res.data or []
    except APIError as e:
        st.error("Supabase SELECT epäonnistui. Varmista taulu, sarake 'kickoff_at' ja RLS.")
        st.exception(e)
        return []

def insert_match(m: Dict[str, Any]) -> None:
    client = get_client()
    if not client:
        return
    new_item = {
        "id": uuid.uuid4().hex,
        "home_team": m["home_team"],
        "away_team": m["away_team"],
        "location": m.get("location", ""),
        "competition": m.get("competition", ""),
        "kickoff_at": m["kickoff_at"],
        "notes": m.get("notes", ""),
    }
    client.table("matches").insert(new_item).execute()

def list_reports(match_id: str | None = None) -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
    q = client.table("reports").select("*").order("created_at", desc=True)
    if match_id:
        q = q.eq("match_id", match_id)
    reps = q.execute().data or []
    match_map = {m["id"]: m for m in list_matches()}
    out = []
    for r in reps:
        m = match_map.get(r.get("match_id"), {})
        out.append(
            {
                **r,
                "home_team": m.get("home_team", "?"),
                "away_team": m.get("away_team", "?"),
                "kickoff_at": m.get("kickoff_at", ""),
            }
        )
    return out


def save_report(records: List[Dict[str, Any]]) -> None:
    client = get_client()
    if not client or not records:
        return
    payload = clean_jsonable(records)
    client.table("reports").upsert(payload, on_conflict="id").execute()


def delete_reports(ids: List[str]) -> None:
    client = get_client()
    if not client:
        return
    client.table("reports").delete().in_("id", [str(i) for i in ids]).execute()

# ---------------- UI helpers ----------------
def _fmt_match(r: Dict[str, Any]) -> str:
    latam_tz = st.session_state.get("latam_tz", "America/Bogota")
    user_tz = st.session_state.get("user_tz", "Europe/Helsinki")
    ko = r.get("kickoff_at")
    when = ""
    if ko:
        try:
            dt_latam = to_tz(ko, latam_tz)
            dt_user = to_tz(ko, user_tz)
            when = f" {dt_latam:%Y-%m-%d %H:%M} ({latam_tz}) • {dt_user:%H:%M} ({user_tz})"
        except Exception:
            pass
    return f"{r.get('home_team','?')} vs {r.get('away_team','?')}{when}"

FOOT_OPTIONS = ["Right","Left","Both"]
POSITION_OPTIONS = ["GK","RB","RWB","CB","LB","LWB","DM","CM","AM","RW","LW","ST","Other / free text"]

CORE_AREAS = [
    ("Technique",        "technique"),
    ("Game Intelligence","game_intelligence"),
    ("GRIT / Mental",    "mental"),
    ("Athletic Ability", "athletic"),
]

BADGE_CSS = """
<style>
.badges { display:flex; gap:.5rem; flex-wrap:wrap; }
.badge  { padding:.25rem .6rem; border-radius:999px; font-size:.85rem; font-weight:600;
          background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15); }
.kpi    { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08);
          padding:12px 14px; border-radius:12px; }
.kpi h4 { margin:0 0 6px 0; font-size:.9rem; opacity:.8; }
.kpi .val{ font-size:1.6rem; font-weight:700; }
.small  { opacity:.8; font-size:.9rem; }
</style>
"""

def _ratings_to_df(ratings) -> pd.DataFrame:
    """
    Palauttaa DataFramen sarakkeilla ['attribute','rating','comment'].
    Tukee sekä uutta 1–5 asteikkoa että vanhoja 1–20 arvoja, jotka
    migroidaan 1–5 asteikolle kaavalla: ceil(old/4).
    """
    if isinstance(ratings, str):
        try:
            ratings = json.loads(ratings)
        except Exception:
            ratings = []
    if not isinstance(ratings, list):
        ratings = []
    df = pd.DataFrame(ratings)
    if not {"attribute", "rating"}.issubset(df.columns):
        return pd.DataFrame(columns=["attribute", "rating", "comment"])

    s = pd.to_numeric(df["rating"], errors="coerce").fillna(1)
    if s.max() > 5:  # 1–20 → 1–5
        s = ((s - 1) // 4 + 1).clip(1, 5)
    df["rating"] = s.round().clip(1, 5).astype(int)
    if "comment" not in df.columns:
        df["comment"] = ""
    return df[["attribute","rating","comment"]]

# ---------------- Main ----------------
def show_scout_match_reporter():
    st.header("📋 Scout Match Reporter")
    _inject_css_once("BADGE_CSS_scout_reporter", BADGE_CSS)

    # 1) Create/Select Match
    st.subheader("1️⃣ Create/Select Match")
    matches = list_matches()
    with st.expander("➕ Add Match", expanded=False):
        c1, c2 = st.columns(2)
        home = c1.text_input("Home Team", key="scout_reporter__home")
        away = c2.text_input("Away Team", key="scout_reporter__away")
        mdate = st.date_input("Match Date", date.today(), key="scout_reporter__mdate")
        mtime = st.time_input(
            "Kickoff Time",
            datetime.now().replace(hour=12, minute=0, second=0, microsecond=0).time(),
            key="scout_reporter__mtime",
        )
        latam_tz = st.text_input(
            "Kickoff timezone",
            st.session_state.get("latam_tz", "America/Bogota"),
            key="scout_reporter__tz",
        )
        comp = st.text_input("Competition (optional)", key="scout_reporter__comp")
        loc = st.text_input("Location (optional)", key="scout_reporter__loc")
        if st.button("Add Match", key="scout_reporter__add_match_btn"):
            if home and away:
                local_dt = datetime.combine(mdate, mtime).replace(tzinfo=ZoneInfo(latam_tz))
                kickoff_at = local_dt.isoformat()
                insert_match(
                    {
                        "home_team": home.strip(),
                        "away_team": away.strip(),
                        "location": loc.strip(),
                        "competition": comp.strip(),
                        "kickoff_at": kickoff_at,
                    }
                )
                st.success(f"Match {home} vs {away} added.")
                matches = list_matches()
            else:
                st.warning("Home and Away required.")
    if not matches:
        st.info("No matches yet.")
        return

    sel_match = st.selectbox(
        "Select Match",
        matches,
        format_func=_fmt_match,
        key="scout_reporter__select_match"
    )

    # 2) Player Source
    st.subheader("2️⃣ Player Source")
    source = st.radio(
        "Source",
        ["Team","Shortlist"],
        horizontal=True,
        key="scout_reporter__source"
    )

    # Rakennetaan player_opts = List[Tuple[id, label]] ja player_map id→player
    player_opts: List[Tuple[str, str]] = []
    player_map: Dict[str, Dict[str, Any]] = {}

    if source == "Team":
        teams = list_teams()
        if not teams:
            st.warning("No teams found in database.")
            return
        sel_team = st.selectbox("Team", teams, key="scout_reporter__team")
        raw_players = list_players_by_team(sel_team) or []
        if isinstance(raw_players, pd.DataFrame):
            records = [_normalize_player_record(r.to_dict()) for _, r in raw_players.iterrows()]
        else:
            records = [_normalize_player_record(p) for p in raw_players]
        for p in records:
            if not p.get("id") or not p.get("name"):
                continue
            label = (
                f"{p['name']} ({p['position']}) — {p['team_name']}"
                if p.get("position")
                else f"{p['name']} — {p['team_name']}"
            )
            player_opts.append((p["id"], label))
            player_map[p["id"]] = p
    else:
        sls = list_shortlists()
        if not sls:
            st.warning("No shortlists found in database.")
            return
        sel_sl = st.selectbox("Shortlist", sls, key="scout_reporter__shortlist")
        ids = set(get_shortlist_members(sel_sl))
        for p in get_all_players():
            pid = p.get("id")
            if pid and pid in ids:
                label = (
                    f"{p['name']} ({p['position']}) — {p['team_name']}"
                    if p.get("position")
                    else f"{p['name']} — {p['team_name']}"
                )
                player_opts.append((pid, label))
                player_map[pid] = p

    if not player_opts:
        st.warning("No players for this selection.")
        return

    q = st.text_input("Search Player", key="scout_reporter__search")
    if q:
        ql = q.lower().strip()
        player_opts = [p for p in player_opts if ql in p[1].lower()]
    if not player_opts:
        st.warning("No players match the search.")
        return

    opts_dict = dict(player_opts)
    player_id = st.selectbox(
        "Player",
        options=[pid for pid, _ in player_opts],
        format_func=lambda pid: opts_dict.get(pid, pid),
        key="scout_reporter__player",
    )
    pid = str(player_id)
    sel_player = player_map.get(pid, {})

    # 3) Essentials (1–5 scale)
    st.subheader("3️⃣ Essentials")
    c1, c2 = st.columns(2)
    with c1:
        foot = st.selectbox("Foot", FOOT_OPTIONS, index=0, key="scout_reporter__foot")
    with c2:
        try:
            idx = POSITION_OPTIONS.index("ST")
        except ValueError:
            idx = 0
        pos_choice = st.selectbox("Position", POSITION_OPTIONS, index=idx, key="scout_reporter__pos")

    position_final = pos_choice
    if pos_choice == "Other / free text":
        position_free = st.text_input("Position (free text)", key="scout_reporter__pos_free")
        position_final = position_free.strip() if position_free else pos_choice

    st.markdown("#### Core Areas (1–5) + short notes")
    ratings = []
    colA, colB = st.columns(2)
    for i, (label, key) in enumerate(CORE_AREAS):
        with (colA if i % 2 == 0 else colB):
            val = st.slider(label, 1, 5, 3, step=1, key=f"scout_reporter__rt_{key}")
            note = st.text_input(f"Comment – {label}", key=f"scout_reporter__cm_{key}", placeholder="optional")
            ratings.append({"attribute": label, "rating": val, "comment": note})

    # General comment
    st.markdown("#### Conclusion / General comment")
    with st.container(border=True):
        default_text = st.session_state.get("scout_reporter__general_comment_text", "")
        general_text = st.text_area(
            label="General comment",
            value=default_text,
            key="scout_reporter__general_comment_text",
            max_chars=600,
            height=140,
            placeholder="Standouts, projection, role fit, risk.",
            label_visibility="collapsed"
        )
        st.markdown(f"<div style='text-align:right' class='small'>{len(general_text)}/600</div>", unsafe_allow_html=True)
        if general_text.strip():
            st.markdown("**Preview**")
            with st.container(border=True):
                st.write(general_text.strip())
    general = general_text

    if st.button("💾 Save Report", key="scout_reporter__save_report_btn"):
        save_report([
            {
                "id": uuid.uuid4().hex,
                "created_at": datetime.now().isoformat(),
                "match_id": sel_match["id"],
                "player_id": pid,
                "competition": sel_match.get("competition", ""),
                "foot": foot,
                "position": position_final,
                "ratings": json.dumps(ratings, ensure_ascii=False),
                "general_comment": general.strip(),
            }
        ])
        st.success(f"Report saved for {sel_player.get('name','?')}.")

    # FAST DELETE MODE toggle
    st.markdown("---")
    fast_delete = st.checkbox(
        "⚡ Fast delete mode (skip charts & heavy UI)",
        value=True,
        help="Speeds up deleting by skipping per-report charts & tables.",
        key="scout_reporter__fast_delete"
    )

    # 4) Inspect Reports
    st.subheader("4️⃣ Inspect Reports")
    reps = list_reports()
    if not reps:
        st.info("No reports yet.")
        return

    name_map = {str(p.get("id")): p.get("name", "Unknown") for p in get_all_players()}

    if not fast_delete:
        for rep in reps:
            title = _fmt_match(rep) + f" – {name_map.get(str(rep['player_id']),'Unknown')}"
            with st.expander(title, expanded=False):
                st.markdown(
                    f"<div class='badges'>"
                    f"<span class='badge'>Player: {name_map.get(str(rep['player_id']),'Unknown')}</span>"
                    + (f"<span class='badge'>Position: {rep.get('position')}</span>" if rep.get("position") else "")
                    + (f"<span class='badge'>Foot: {rep.get('foot')}</span>"         if rep.get("foot") else "")
                    + (f"<span class='badge'>Competition: {rep.get('competition')}</span>" if rep.get("competition") else "")
                    + "</div>",
                    unsafe_allow_html=True
                )

                if rep.get("general_comment"):
                    st.markdown(f"**General Comment:** {rep.get('general_comment')}")

                df_r = _ratings_to_df(rep.get("ratings"))
                if df_r.empty:
                    st.info("No attribute ratings in this report.")
                    continue

                df_sorted = df_r.sort_values("rating", ascending=False).reset_index(drop=True)
                avg = df_sorted["rating"].mean()
                best_row  = df_sorted.iloc[0]
                worst_row = df_sorted.iloc[-1]

                k1, k2, k3 = st.columns(3)
                with k1:
                    st.markdown("<div class='kpi'><h4>Average</h4><div class='val'>"
                                f"{avg:.1f}</div></div>", unsafe_allow_html=True)
                with k2:
                    st.markdown("<div class='kpi'><h4>Best</h4><div class='val'>"
                                f"{best_row['attribute']} ({int(best_row['rating'])})</div></div>", unsafe_allow_html=True)
                with k3:
                    st.markdown("<div class='kpi'><h4>Needs work</h4><div class='val'>"
                                f"{worst_row['attribute']} ({int(worst_row['rating'])})</div></div>", unsafe_allow_html=True)

                fig = px.bar(
                    df_sorted, x="rating", y="attribute", orientation="h",
                    color="rating", color_continuous_scale="Blues",
                    range_x=[1, 5], title=None, text="rating"
                )
                fig.update_layout(coloraxis_showscale=False, margin=dict(l=10,r=10,t=10,b=10), height=320)
                fig.update_traces(textposition="outside", cliponaxis=False)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Fast mode on — charts & per-report UI skipped.")

    # 5) Delete Reports — improved UX + pagination
    st.subheader("5️⃣ Delete Reports")
    df_all = ensure_columns(pd.DataFrame(reps))

    def _parse_dt(s):
        try:
            return datetime.fromisoformat(str(s))
        except Exception:
            return None

    df_all["player_name"] = (
        df_all.get("player_id", pd.Series(dtype=str)).astype(str).map(name_map)
    )
    df_all["created_dt"] = df_all["created_at"].apply(_parse_dt)
    df_all["date"] = df_all["kickoff_at"].astype(str).str[:10]
    df_all["match"] = df_all.apply(
        lambda r: f"{r.get('home_team','?')} vs {r.get('away_team','?')}", axis=1
    )
    df_all = df_all.sort_values("created_at", ascending=False)
    df_all = ensure_columns(df_all)

    if df_all.empty:
        st.info("No reports found.")
        return

    # Filters
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        text_query = st.text_input(
            "Search (player, match, notes)",
            key="scout_reporter__filter_q",
        )
    with f2:
        player_filter = st.multiselect(
            "Player",
            safe_unique(df_all, "player_name"),
            key="scout_reporter__filter_player",
        )
    with f3:
        competition_filter = st.multiselect(
            "Competition",
            safe_unique(df_all, "competition"),
            key="scout_reporter__filter_comp",
        )

    d1, d2 = st.columns(2)
    with d1:
        start_date = st.date_input("From date", value=None, key="scout_reporter__from")
    with d2:
        end_date   = st.date_input("To date", value=None, key="scout_reporter__to")

    filt = df_all.copy()
    if text_query:
        ql = text_query.lower().strip()
        filt = filt[
            filt["player_name"].fillna("").str.lower().str.contains(ql)
            | filt["match"].fillna("").str.lower().str.contains(ql)
            | filt["general_comment"].fillna("").str.lower().str.contains(ql)
        ]
    if player_filter:
        filt = filt[filt["player_name"].isin(player_filter)]
    if competition_filter:
        filt = filt[filt["competition"].isin(competition_filter)]
    if start_date:
        filt = filt[(filt["created_dt"].notna()) & (filt["created_dt"] >= datetime.combine(start_date, datetime.min.time()))]
    if end_date:
        filt = filt[(filt["created_dt"].notna()) & (filt["created_dt"] <= datetime.combine(end_date, datetime.max.time()))]

    st.caption(f"{len(filt)} / {len(df_all)} reports shown")

    # Pagination
    page_size = st.selectbox("Rows per page", [50, 100, 200, 500], index=1, key="scout_reporter__page_size")
    total = int(len(filt))
    pages = max(1, (total + int(page_size) - 1) // int(page_size))
    page = st.number_input("Page", min_value=1, max_value=int(pages), value=1, key="scout_reporter__page_num")

    start = (int(page) - 1) * int(page_size)
    end = start + int(page_size)
    filt_page = filt.iloc[start:end].copy()

    # Select table with checkbox column
    view_cols = ["id", "date", "player_name", "match", "competition", "created_at"]
    table = filt_page[view_cols].rename(columns={
        "player_name": "Player",
        "match": "Match",
        "competition": "Competition",
        "created_at": "Created"
    }).copy()
    table.insert(0, "Select", False)

    edited = st.data_editor(
        table,
        use_container_width=True,
        hide_index=True,
        disabled=["id","date","Player","Match","Competition","Created"],
        key=f"scout_reporter__del_editor_p{page}"
    )

    selected_ids = edited.loc[edited["Select"] == True, "id"].astype(str).tolist()
    filtered_ids = filt["id"].astype(str).tolist()

    st.markdown("---")
    st.warning("Type **DELETE** to confirm removals.", icon="⚠️")
    confirm = st.text_input("Confirmation", placeholder="DELETE to confirm", key="scout_reporter__confirm")

    cdel1, cdel2, cdel3 = st.columns([1, 1, 3])
    with cdel1:
        if st.button(
            f"Delete selected ({len(selected_ids)})",
            disabled=(len(selected_ids) == 0 or confirm != "DELETE"),
            key="scout_reporter__del_selected_btn"
        ):
            with st.spinner("Deleting selected..."):
                delete_reports(selected_ids)
            st.success(f"Deleted {len(selected_ids)} report(s).")
            st.rerun()
    with cdel2:
        if st.button(
            f"Delete filtered ({len(filtered_ids)})",
            disabled=(len(filtered_ids) == 0 or confirm != "DELETE"),
            key="scout_reporter__del_filtered_btn"
        ):
            with st.spinner("Deleting filtered..."):
                delete_reports(filtered_ids)
            st.success(f"Deleted {len(filtered_ids)} report(s).")
            st.rerun()
    with cdel3:
        st.caption("Selected = rows checked in the table. Filtered = all rows currently visible after filters.")

if __name__ == "__main__":
    show_scout_match_reporter()
