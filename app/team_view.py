# app/team_view.py
# ScoutLens — Team View (all-in enhanced)
# -------------------------------------------------------
# - Namespaced session_state keys (no collisions)
# - Quick stats, saved views, visible columns
# - Persistent shortlist (JSON), prepare-only actions (NO navigation)
# - Robust age filter (handles min==max), filter chips
# - Fast table fallback, optional position guessing

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, date

import pandas as pd
import streamlit as st

from app_paths import file_path, DATA_DIR
from storage import load_json, save_json

# -------------------- CONFIG / STATE KEYS --------------------
STATE_TEAM_KEY        = "team_view__selected_team"
STATE_SHORTLIST_KEY   = "team_view__shortlist_ids"
STATE_SAVED_VIEWS_KEY = "team_view__saved_views"
STATE_VISIBLE_COLS_KEY= "team_view__visible_cols"
STATE_Q_KEY           = "team_view__q"
STATE_POS_KEY         = "team_view__pos"
STATE_FOOT_KEY        = "team_view__foot"
STATE_CLUB_KEY        = "team_view__club"
STATE_AGE_KEY         = "team_view__age"
STATE_CACHE_BUSTER    = "team_view__cache_buster"

# Threshold for switching cards -> table
CARD_THRESHOLD = 80

# Data files
PLAYERS_FP   = file_path("players.json")
SHORTLIST_FP = file_path("shortlist.json")

# External (optional) teams source
try:
    from data_utils import list_teams
except Exception:
    list_teams = None  # fallback players.jsonista

# ===================== Utils & IO =====================

def _safe_str(v: Any) -> str:
    return "" if v is None else str(v)

@st.cache_data(show_spinner=False)
def _load_json(fp: Path, default, cache_buster: int = 0):
    """Cached JSON loader with a manual cache-buster."""
    return load_json(fp, default)

def _save_json(fp: Path, data: Any) -> None:
    try:
        save_json(fp, data)
    except Exception:
        pass

def _load_shortlist() -> set:
    data = load_json(SHORTLIST_FP, [])
    return set(data) if isinstance(data, list) else set()

def _save_shortlist(s: set) -> None:
    _save_json(SHORTLIST_FP, sorted(list(s)))

def _norm_team(p: Dict[str, Any]) -> str:
    return (
        p.get("team_name")
        or p.get("Team")
        or p.get("team")
        or p.get("current_club")
        or p.get("CurrentClub")
        or ""
    ).strip()

def _norm_name(p: Dict[str, Any]) -> str:
    return (p.get("name") or p.get("Name") or "").strip()

def _parse_birthdate_to_age(v: Any) -> Optional[int]:
    if not v:
        return None
    try:
        if isinstance(v, (datetime, date)):
            b = v
        else:
            s = str(v).strip()
            if len(s) == 4 and s.isdigit():
                b = date(int(s), 7, 1)                  # YYYY
            elif "-" in s:
                b = datetime.strptime(s[:10], "%Y-%m-%d").date()  # YYYY-MM-DD
            elif "/" in s:
                b = datetime.strptime(s[:10], "%d/%m/%Y").date()  # DD/MM/YYYY
            else:
                return None
        today = date.today()
        return max(0, today.year - b.year - ((today.month, today.day) < (b.month, b.day)))
    except Exception:
        return None

def _derive_age(p: Dict[str, Any]) -> Optional[int]:
    for k in ("BirthDate", "birthdate", "Birthdate", "DOB", "date_of_birth", "YOB", "BirthYear", "birthyear"):
        if k in p and p[k]:
            age = _parse_birthdate_to_age(p[k])
            if age is None and str(p[k]).isdigit() and len(str(p[k])) == 4:
                age = _parse_birthdate_to_age(str(p[k]))
            if age is not None:
                return age
    for k in ("Age", "age"):
        if k in p and str(p[k]).isdigit():
            return int(p[k])
    return None

def _guess_position(text: str) -> str:
    """Tiny heuristic to guess a position from free text."""
    t = (text or "").lower()
    if any(k in t for k in ["gk", "keeper", "goal"]): return "GK"
    if any(k in t for k in ["left back", "lb", "lwb"]): return "LB"
    if any(k in t for k in ["right back", "rb", "rwb"]): return "RB"
    if any(k in t for k in ["center back", "centre back", "cb"]): return "CB"
    if any(k in t for k in ["dm", "volante", "pivot"]): return "DM"
    if any(k in t for k in ["cm", "mezzala", "interior"]): return "CM"
    if any(k in t for k in ["am", "enganche", "no.10", "10 "]): return "AM"
    if any(k in t for k in ["lw", "left wing"]): return "LW"
    if any(k in t for k in ["rw", "right wing"]): return "RW"
    if any(k in t for k in ["st", "cf", "9 "]): return "ST"
    return ""

# ===================== Data shaping =====================

def _collect_players_for_team(team: str, cache_buster: int) -> List[Dict[str, Any]]:
    team = (team or "").strip()
    players = _load_json(PLAYERS_FP, [], cache_buster)
    out: List[Dict[str, Any]] = []
    for p in players:
        if _norm_team(p) == team:
            pid = _safe_str(p.get("id") or p.get("PlayerID") or p.get("player_id") or "")
            name = _norm_name(p)
            tname = _norm_team(p)
            row = {**p, "id": pid, "name": name, "team_name": tname}
            if "Age" not in row or row.get("Age") in (None, "", 0):
                age = _derive_age(p)
                if age is not None:
                    row["Age"] = age
            row["CurrentClub"] = row.get("CurrentClub") or row.get("current_club") or tname
            out.append(row)
    return out

def _teams_from_players_json(cache_buster: int) -> List[str]:
    players = _load_json(PLAYERS_FP, [], cache_buster)
    teams = sorted({_norm_team(p) for p in players if _norm_team(p)})
    return teams

def _rows_to_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["id", "name", "team_name"])

    cols = set()
    for r in rows:
        cols.update(r.keys())
    df = pd.DataFrame([{c: r.get(c, None) for c in cols} for r in rows])

    # Standard names
    if "name" not in df.columns and "Name" in df.columns:
        df.rename(columns={"Name": "name"}, inplace=True)
    if "team_name" not in df.columns:
        for c in ["team", "Team", "current_club", "CurrentClub"]:
            if c in df.columns:
                df["team_name"] = df[c]
                break
        if "team_name" not in df.columns:
            df["team_name"] = ""

    if "CurrentClub" not in df.columns:
        df["CurrentClub"] = df["team_name"]

    # Unify Position
    if "Position" not in df.columns:
        for c in ["Position", "position", "Role", "role", "Pos", "pos"]:
            if c in df.columns:
                df.rename(columns={c: "Position"}, inplace=True)
                break
    if "Position" not in df.columns:
        src = None
        for c in ["role","Role","Notes","notes","profile","Profile","description","Desc"]:
            if c in df.columns:
                src = c
                break
        if src:
            df["Position"] = df[src].astype(str).map(_guess_position)

    # Unify Foot
    if "Foot" not in df.columns:
        for c in ["Foot", "PreferredFoot", "foot", "preferred_foot"]:
            if c in df.columns:
                df.rename(columns={c: "Foot"}, inplace=True)
                break

    if "Age" not in df.columns:
        df["Age"] = None

    # Best-effort numeric casting
    for c in df.columns:
        if df[c].dtype == object:
            try:
                df[c] = pd.to_numeric(df[c], errors="ignore")
            except Exception:
                pass

    # Ensure id is string
    if "id" in df.columns:
        df["id"] = df["id"].astype(str)

    return df

# ===================== UI =====================

def show_team_view():
    st.header("🏟️ Team View")
    st.caption(f"Data folder → `{DATA_DIR}`")

    # Reload button
    col_reload, _ = st.columns([0.2, 0.8])
    with col_reload:
        if st.button("↻ Reload data", help="Clear caches and reload"):
            st.cache_data.clear()
            st.session_state[STATE_CACHE_BUSTER] = st.session_state.get(STATE_CACHE_BUSTER, 0) + 1
            st.rerun()

    cache_buster = st.session_state.get(STATE_CACHE_BUSTER, 0)

    # Migration from old key (yksisuuntainen kopio vain jos ei ole asetettu)
    if "selected_team" in st.session_state and STATE_TEAM_KEY not in st.session_state:
        st.session_state[STATE_TEAM_KEY] = st.session_state["selected_team"]

    # Teams source
    preselected = st.session_state.get(STATE_TEAM_KEY)
    teams: List[str] = []
    if callable(list_teams):
        try:
            teams = list_teams() or []
        except Exception:
            teams = []
    if not teams:
        teams = _teams_from_players_json(cache_buster)

    if not teams:
        st.info("No teams available. Add players first.")
        return

    selected_idx = teams.index(preselected) if preselected in teams else 0
    # ⚠️ Uniikki key tälle näkymälle – EI "selected_team" (se on sivupalkissa)
    team = st.selectbox("Select Team", teams, index=selected_idx, key=STATE_TEAM_KEY)

    # Load players for team
    rows = _collect_players_for_team(team, cache_buster)
    if not rows:
        st.info(f"No players found for team {team}.")
        return

    df = _rows_to_df(rows)

    # --------- Quick stats ----------
    st.subheader(f"Players — {team}  ")
    with st.container():
        left, mid, right = st.columns(3)
        ages_series = pd.to_numeric(df["Age"], errors="coerce").dropna()
        avg_age = round(ages_series.mean(), 1) if not ages_series.empty else "–"
        with left:
            st.metric("Players", len(df))
        with mid:
            st.metric("Average age", avg_age)
        with right:
            pos_counts = df.get("Position", pd.Series(dtype=object)).fillna("—").astype(str).value_counts()
            top_pos = ", ".join([f"{k} {v}" for k, v in pos_counts.head(2).items()]) if len(pos_counts) else "–"
            st.metric("Top positions", top_pos)

    # Small distribution chart (optional)
    if "Position" in df.columns and df["Position"].notna().any():
        st.caption("Position distribution")
        st.bar_chart(df["Position"].fillna("—").astype(str).value_counts())

    # --------- Filters ----------
    with st.container():
        c1, c2, c3, c4, c5, c6 = st.columns([1.6, 1.1, 1.1, 1.2, 1.2, 0.7], gap="small")
        with c1:
            q = st.text_input("Search name", key=STATE_Q_KEY, placeholder="e.g. Díaz, González").strip()
        with c2:
            pos_vals = sorted([v for v in df.get("Position", pd.Series(dtype=object)).dropna().astype(str).unique() if v])
            pos_sel = st.multiselect("Position", pos_vals, default=st.session_state.get(STATE_POS_KEY, []), key=STATE_POS_KEY)
        with c3:
            foot_vals = sorted([v for v in df.get("Foot", pd.Series(dtype=object)).dropna().astype(str).unique() if v])
            foot_sel = st.multiselect("Foot", foot_vals, default=st.session_state.get(STATE_FOOT_KEY, []), key=STATE_FOOT_KEY)
        with c4:
            # Robust age filter (slider only when min<max)
            age_min, age_max = None, None
            if "Age" in df.columns:
                ages = pd.to_numeric(df["Age"], errors="coerce").dropna()
                if not ages.empty:
                    amin = int(ages.min()); amax = int(ages.max())
                    amin_c = max(14, amin); amax_c = min(45, amax)
                    if amin_c >= amax_c:
                        st.caption(f"Age range: {amin_c} only")
                        # poista mahdollinen vanha slider-arvo
                        st.session_state.pop(STATE_AGE_KEY, None)
                    else:
                        default_age = st.session_state.get(STATE_AGE_KEY, (amin_c, amax_c))
                        # clamp default to current bounds
                        d0 = max(amin_c, min(default_age[0], amax_c))
                        d1 = max(amin_c, min(default_age[1], amax_c))
                        if d0 > d1: d0, d1 = d1, d0
                        age_min, age_max = st.slider("Age", min_value=amin_c, max_value=amax_c,
                                                     value=(d0, d1), key=STATE_AGE_KEY)
                else:
                    st.caption("No age data")
        with c5:
            club_vals = sorted([v for v in df.get("CurrentClub", pd.Series(dtype=object)).dropna().astype(str).unique() if v])
            club_sel = st.multiselect("Current club", club_vals, default=st.session_state.get(STATE_CLUB_KEY, []), key=STATE_CLUB_KEY)
        with c6:
            if st.button("Reset", help="Clear all filters"):
                st.session_state[STATE_Q_KEY] = ""
                st.session_state[STATE_POS_KEY] = []
                st.session_state[STATE_FOOT_KEY] = []
                st.session_state[STATE_CLUB_KEY] = []
                st.session_state.pop(STATE_AGE_KEY, None)
                st.rerun()

    # Active filter chips
    chips = []
    if q: chips.append(f"🔎 {q}")
    if pos_sel: chips.append("📍 " + "/".join(pos_sel))
    if foot_sel: chips.append("🦶 " + "/".join(foot_sel))
    if (STATE_AGE_KEY in st.session_state) or (age_min is not None and age_max is not None):
        lo, hi = (st.session_state.get(STATE_AGE_KEY, (age_min, age_max)))
        if lo is not None and hi is not None:
            chips.append(f"🎂 {lo}-{hi}")
    if club_sel: chips.append("🏟️ " + "/".join(club_sel))
    if chips:
        st.caption("Active filters: " + "   •   ".join(chips))

    # --------- Advanced: sort + visible columns + starters + shortlist toggle ----------
    with st.expander("Advanced", expanded=False):
        cA, cB, cC = st.columns([1.3, 1.2, 1.5])
        with cA:
            numeric_candidates = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            sort_by = st.selectbox("Sort by (numeric)", numeric_candidates, index=0 if numeric_candidates else None)
            sort_desc = st.toggle("Sort descending", value=True)
        with cB:
            starters_flag = None
            for k in ("Starter", "starter", "IsStarter", "is_starter", "XI"):
                if k in df.columns:
                    starters_flag = k
                    break
            only_starters = st.checkbox("Only starters", value=False, disabled=starters_flag is None)
        with cC:
            all_cols = list(df.columns)
            default_visible = st.session_state.get(STATE_VISIBLE_COLS_KEY) or ["name","Position","Age","CurrentClub","Foot"]
            visible_cols = st.multiselect("Visible columns", all_cols, default=default_visible)
            st.session_state[STATE_VISIBLE_COLS_KEY] = visible_cols

    # Persistent shortlist init
    if STATE_SHORTLIST_KEY not in st.session_state:
        st.session_state[STATE_SHORTLIST_KEY] = _load_shortlist()

    # --------- Apply filters ----------
    df_show = df.copy()
    if q:
        df_show = df_show[df_show["name"].astype(str).str.contains(q, case=False, na=False)]
    if pos_sel:
        df_show = df_show[df_show.get("Position", pd.Series(dtype=object)).astype(str).isin(pos_sel)]
    if foot_sel:
        df_show = df_show[df_show.get("Foot", pd.Series(dtype=object)).astype(str).isin(foot_sel)]
    if (STATE_AGE_KEY in st.session_state) or (age_min is not None and age_max is not None):
        lo, hi = st.session_state.get(STATE_AGE_KEY, (age_min, age_max))
        if lo is not None and hi is not None and "Age" in df_show.columns:
            df_show = df_show[pd.to_numeric(df_show["Age"], errors="coerce").between(lo, hi, inclusive="both")]
    if club_sel:
        df_show = df_show[df_show.get("CurrentClub", pd.Series(dtype=object)).astype(str).isin(club_sel)]
    if 'starters_flag' in locals() and starters_flag and only_starters:
        df_show = df_show[df_show[starters_flag] == True]  # noqa: E712
    # Sorting
    if sort_by:
        df_show = df_show.sort_values(by=sort_by, ascending=not sort_desc, kind="mergesort")

    st.markdown(f"**Results:** {len(df_show)} / {len(df)}  •  Columns: {len(df_show.columns)}")

    # Preferred + rating-like columns
    preferred_cols = ["id", "name", "Position", "Age", "Foot", "team_name", "CurrentClub"]
    rating_like = [c for c in df_show.columns if c not in preferred_cols and pd.api.types.is_numeric_dtype(df_show[c])]
    # User visible columns take precedence if defined
    if st.session_state.get(STATE_VISIBLE_COLS_KEY):
        preferred_cols = [c for c in st.session_state[STATE_VISIBLE_COLS_KEY] if c in df_show.columns]
    else:
        preferred_cols = [c for c in preferred_cols if c in df_show.columns] + rating_like[:6]

    # --------- Saved Views (store & apply) ----------
    st.divider()
    st.caption("Saved Views")
    st.session_state.setdefault(STATE_SAVED_VIEWS_KEY, {})

    sv_c1, sv_c2 = st.columns([1.3, 2])
    with sv_c1:
        view_name = st.text_input("New view name", "", placeholder="e.g. U23 left-footed")
    with sv_c2:
        if st.button("💾 Save current view", use_container_width=True, disabled=not view_name):
            current_view = {
                "q": st.session_state.get(STATE_Q_KEY, ""),
                "pos_sel": st.session_state.get(STATE_POS_KEY, []),
                "foot_sel": st.session_state.get(STATE_FOOT_KEY, []),
                "club_sel": st.session_state.get(STATE_CLUB_KEY, []),
                "age": st.session_state.get(STATE_AGE_KEY, None),
            }
            st.session_state[STATE_SAVED_VIEWS_KEY][view_name] = current_view
            st.success(f"Saved view: {view_name}")

    if st.session_state[STATE_SAVED_VIEWS_KEY]:
        pick = st.selectbox("Apply saved view", ["—"] + list(st.session_state[STATE_SAVED_VIEWS_KEY].keys()))
        if pick != "—":
            v = st.session_state[STATE_SAVED_VIEWS_KEY][pick]
            st.session_state[STATE_Q_KEY] = v.get("q", "")
            st.session_state[STATE_POS_KEY] = v.get("pos_sel", [])
            st.session_state[STATE_FOOT_KEY] = v.get("foot_sel", [])
            st.session_state[STATE_CLUB_KEY] = v.get("club_sel", [])
            if v.get("age") is not None:
                st.session_state[STATE_AGE_KEY] = tuple(v["age"])
            else:
                st.session_state.pop(STATE_AGE_KEY, None)
            st.rerun()

    # --------- Render list/table ----------
    def _shortlist_toggle(pid: str):
        if not pid:
            return
        s = st.session_state[STATE_SHORTLIST_KEY]
        if pid in s:
            s.remove(pid)
        else:
            s.add(pid)
        _save_shortlist(s)

    def _fmt_num(v):
        try:
            f = float(v)
            return str(int(f)) if f.is_integer() else f"{f:.1f}"
        except Exception:
            return str(v)

    use_cards = len(df_show) <= CARD_THRESHOLD

    if len(df_show) == 0:
        st.info("No matches with current filters.")
    elif use_cards and "id" in df_show.columns:
        st.write("Click ☆ to add to shortlist.")
        # Choose top-3 numeric columns for quick glance
        top_numeric = [c for c in rating_like if c in df_show.columns][:3]
        for _, r in df_show.reset_index(drop=True).iterrows():
            with st.container(border=True):
                c0, c1, c2 = st.columns([0.14, 2.2, 1.6])
                with c0:
                    pid = str(r.get("id") or "")
                    is_in = pid in st.session_state[STATE_SHORTLIST_KEY]
                    label = "★" if is_in else "☆"
                    if st.button(label, key=f"team_view__short_{pid}", help="Toggle shortlist"):
                        _shortlist_toggle(pid)
                with c1:
                    n = r.get("name", "")
                    pos = r.get("Position", "")
                    age = r.get("Age", "")
                    club = r.get("CurrentClub", "")
                    st.markdown(f"**{_safe_str(n)}**  \n{_safe_str(pos)} • Age {age} • {club}")
                with c2:
                    if top_numeric:
                        kv = " • ".join(f"{c}: {_fmt_num(r[c])}" for c in top_numeric if pd.notna(r.get(c)))
                        if kv: st.caption(kv)
                    # Action buttons (PREPARE ONLY — no navigation)
                    pid = str(r.get("id",""))
                    bb1, bb2 = st.columns(2)
                    with bb1:
                        if st.button("✍️ Prepare Editor", key=f"team_view__prep_editor_{pid}"):
                            st.session_state["editor__selected_player_id"] = pid
                            st.success("✅ Player Editor prepared. Open it from the sidebar.")
                    with bb2:
                        if st.button("📝 Prepare Reporter", key=f"team_view__prep_report_{pid}"):
                            st.session_state["report__selected_player_id"] = pid
                            st.success("✅ Scout Match Reporter prepared. Open it from the sidebar.")
            st.divider()
    else:
        # Fast table view
        show_cols = preferred_cols if preferred_cols else list(df_show.columns)
        st.dataframe(df_show[show_cols].reset_index(drop=True), use_container_width=True, height=520)

    # --------- Export ----------
    st.markdown("### Export")
    df_export = df_show.reset_index(drop=True)
    csv = df_export.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, file_name=f"{team.replace(' ', '_')}_players.csv", mime="text/csv")

    json_bytes = df_export.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")
    st.download_button("⬇️ Download JSON", json_bytes, file_name=f"{team.replace(' ', '_')}_players.json", mime="application/json")

    # Export shortlist (for current team rows if id present)
    if "id" in df.columns and st.session_state[STATE_SHORTLIST_KEY]:
        ids = list(st.session_state[STATE_SHORTLIST_KEY])
        df_short = df[df["id"].astype(str).isin(ids)]
        if len(df_short):
            csv_s = df_short.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Shortlist CSV", csv_s, file_name=f"{team.replace(' ','_')}_shortlist.csv", mime="text/csv")

# Suora ajo
if __name__ == "__main__":
    show_team_view()
