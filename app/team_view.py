# app/team_view.py — ScoutLens Team View (Supabase, features preserved)
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError

from supabase_client import get_client

# -------------------- CONFIG / STATE KEYS --------------------
STATE_TEAM_KEY         = "team_view__selected_team"
STATE_SHORTLIST_KEY    = "team_view__shortlist_ids"
STATE_SAVED_VIEWS_KEY  = "team_view__saved_views"
STATE_VISIBLE_COLS_KEY = "team_view__visible_cols"
STATE_Q_KEY            = "team_view__q"
STATE_POS_KEY          = "team_view__pos"
STATE_FOOT_KEY         = "team_view__foot"
STATE_CLUB_KEY         = "team_view__club"
STATE_AGE_KEY          = "team_view__age"
STATE_CACHE_BUSTER     = "team_view__cache_buster"

CARD_THRESHOLD = 80  # korttinäkymän raja

# ========= Helpers =========
def _dbg(e: APIError, title="🔧 Supabase PostgREST -virhe"):
    with st.expander(title, expanded=True):
        st.code(
            f"code: {getattr(e,'code',None)}\n"
            f"message: {getattr(e,'message',str(e))}\n"
            f"details: {getattr(e,'details',None)}\n"
            f"hint: {getattr(e,'hint',None)}",
            "text",
        )

def _safe_str(v: Any) -> str:
    return "" if v is None else str(v)

def _col(df: pd.DataFrame, name: str, dtype="object") -> pd.Series:
    return df[name] if name in df.columns else pd.Series(dtype=dtype)

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
            b = v if isinstance(v, date) else v.date()
        else:
            s = str(v).strip()
            if len(s) == 4 and s.isdigit():
                b = date(int(s), 7, 1)
            elif "-" in s:
                b = datetime.strptime(s[:10], "%Y-%m-%d").date()
            elif "/" in s:
                b = datetime.strptime(s[:10], "%d/%m/%Y").date()
            else:
                return None
        today = date.today()
        return max(0, today.year - b.year - ((today.month, today.day) < (b.month, b.day)))
    except Exception:
        return None

def _derive_age(p: Dict[str, Any]) -> Optional[int]:
    keys = ("BirthDate","birthdate","Birthdate","DOB","date_of_birth","YOB","BirthYear","birthyear")
    for k in keys:
        if k in p and p[k]:
            age = _parse_birthdate_to_age(p[k])
            if age is None and str(p[k]).isdigit() and len(str(p[k])) == 4:
                age = _parse_birthdate_to_age(str(p[k]))
            if age is not None:
                return age
    for k in ("Age","age"):
        if k in p and str(p[k]).isdigit():
            return int(p[k])
    return None

def _guess_position(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["gk","keeper","goal"]): return "GK"
    if any(k in t for k in ["left back","lb","lwb"]): return "LB"
    if any(k in t for k in ["right back","rb","rwb"]): return "RB"
    if any(k in t for k in ["center back","centre back","cb"]): return "CB"
    if any(k in t for k in ["dm","volante","pivot"]): return "DM"
    if any(k in t for k in ["cm","mezzala","interior"]): return "CM"
    if any(k in t for k in ["am","enganche","no.10","10 "]): return "AM"
    if any(k in t for k in ["lw","left wing"]): return "LW"
    if any(k in t for k in ["rw","right wing"]): return "RW"
    if any(k in t for k in ["st","cf","9 "]): return "ST"
    return ""

# ========= Supabase IO =========
@st.cache_data(show_spinner=False, ttl=10)
def _load_team_names(cache_buster: int) -> List[str]:
    sb = get_client()
    try:
        # ensisijaisesti teams-taulusta
        res = sb.table("teams").select("name").order("name").execute()
        data = res.data if res.data is not None else []
        names = [ (t.get("name") or "").strip() for t in data if (t.get("name") or "").strip() ]
        if names:
            return names
        # fallback: pelaajista
        pres = sb.table("players").select("team_name").execute()
        pdata = pres.data if pres.data is not None else []
        return sorted({ (p.get("team_name") or "").strip() for p in pdata if (p.get("team_name") or "").strip() })
    except APIError as e:
        _dbg(e)
        return []
    except Exception:
        return []

@st.cache_data(show_spinner=False, ttl=10)
def _collect_players_for_team(team: str, cache_buster: int) -> List[Dict[str, Any]]:
    sb = get_client()
    try:
        res = sb.table("players").select("*").eq("team_name", team).execute()
        players = res.data if res.data is not None else []
    except APIError as e:
        _dbg(e)
        return []
    except Exception:
        return []

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

@st.cache_data(show_spinner=False, ttl=10)
def _load_shortlist() -> set:
    sb = get_client()
    try:
        res = (
            sb.table("shortlists")
            .select("player_id")
            .eq("name", "Default")
            .execute()
        )
        data = res.data if res.data is not None else []
        return {str(r["player_id"]) for r in data if r.get("player_id")}
    except APIError as e:
        # Taulu puuttuu → näytä ohje, mutta älä kaadu
        _dbg(e, "ℹ️ Shortlist-taulu puuttuu? (debug)")
        st.info("Shortlist on pois käytöstä, koska taulua `public.shortlists` ei löytynyt.")
        return set()
    except Exception:
        return set()

def _save_shortlist(s: set) -> None:
    sb = get_client()
    try:
        # yksinkertainen "replace" strategia: tyhjennä ja lisää uudelleen
        sb.table("shortlists").delete().eq("name", "Default").execute()
        if s:
            rows = [{"name": "Default", "player_id": str(pid)} for pid in s]
            sb.table("shortlists").insert(rows).execute()
    except APIError as e:
        _dbg(e, "ℹ️ Shortlist-talennus epäonnistui (debug)")
        st.error("Shortlistin tallennus epäonnistui. Luo taulu `public.shortlists` (katso SQL-ohje alla).")
    except Exception:
        pass

# ========= Data shaping =========
def _teams_from_players_json(cache_buster: int) -> List[str]:
    sb = get_client()
    try:
        res = sb.table("players").select("team_name").execute()
        data = res.data if res.data is not None else []
        return sorted({(p.get("team_name") or '').strip() for p in data if (p.get("team_name") or '').strip()})
    except Exception:
        return []

def _rows_to_df(rows) -> pd.DataFrame:
    import pandas as pd
    if rows is None:
        return pd.DataFrame()
    if isinstance(rows, list):
        return pd.DataFrame(rows)
    if isinstance(rows, dict):
        return pd.DataFrame([rows])
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame()

# ========= UI =========
def show_team_view():
    st.header("🏟️ Team View")

    # Reload
    col_reload, _ = st.columns([0.22, 0.78])
    with col_reload:
        if st.button("↻ Reload data", help="Clear caches and reload"):
            st.cache_data.clear()
            st.session_state[STATE_CACHE_BUSTER] = st.session_state.get(STATE_CACHE_BUSTER, 0) + 1
            st.rerun()

    cache_buster = st.session_state.get(STATE_CACHE_BUSTER, 0)

    # Teams
    preselected = st.session_state.get(STATE_TEAM_KEY)
    teams: List[str] = _load_team_names(cache_buster)
    if not teams:
        teams = _teams_from_players_json(cache_buster)

    if not teams:
        st.info("No teams available. Add players first.")
        # Shortlist-taulun ohje tarvittaessa
        with st.expander("SQL: create public.shortlists (valinnainen)"):
            st.code(
                "create table if not exists public.shortlists (\n"
                "  player_id uuid primary key\n"
                ");\n"
                "alter table public.shortlists enable row level security;\n"
                "create policy if not exists read_shortlists on public.shortlists for select using (true);\n"
                "create policy if not exists write_shortlists on public.shortlists for insert with check (true);\n"
                "create policy if not exists del_shortlists on public.shortlists for delete using (true);\n"
                "notify pgrst, 'reload schema';",
                language="sql",
            )
        return

    selected_idx = teams.index(preselected) if preselected in teams else 0
    team = st.selectbox("Select Team", teams, index=selected_idx, key=STATE_TEAM_KEY)

    # Players for team
    rows = _collect_players_for_team(team, cache_buster)
    df = _rows_to_df(rows)
    if df.empty:
        st.info(f"No players found for team {team}.")
        return

    # KPI:t
    st.subheader(f"Players — {team}")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Players", len(df))
    with c2:
        pos_s = _col(df, "Position")
        pos_counts = pos_s.fillna("—").astype(str).value_counts()
        st.metric("Unique positions", len(pos_counts))
    with c3:
        rating_s = pd.to_numeric(_col(df, "scout_rating"), errors="coerce")
        avg = round(rating_s.dropna().mean(), 1) if len(df) else 0
        st.metric("Avg rating", avg if avg == avg else "–")  # NaN check

    # Pieni jakauma
    pos_chart_s = _col(df, "Position")
    if pos_chart_s.notna().any():
        st.caption("Position distribution")
        st.bar_chart(pos_chart_s.fillna("—").astype(str).value_counts())

    # --------- Filters ----------
    with st.container():
        c1, c2, c3, c4, c5, c6 = st.columns([1.6, 1.1, 1.1, 1.2, 1.2, 0.7], gap="small")
        with c1:
            q = st.text_input("Search name", key=STATE_Q_KEY, placeholder="e.g. Díaz, González").strip()
        with c2:
            pos_vals = sorted([v for v in _col(df, "Position").dropna().astype(str).unique() if v])
            pos_sel = st.multiselect("Position", pos_vals, default=st.session_state.get(STATE_POS_KEY, []), key=STATE_POS_KEY)
        with c3:
            foot_vals = sorted([v for v in _col(df, "Foot").dropna().astype(str).unique() if v])
            foot_sel = st.multiselect("Foot", foot_vals, default=st.session_state.get(STATE_FOOT_KEY, []), key=STATE_FOOT_KEY)
        with c4:
            age_min = age_max = None
            if "Age" in df.columns:
                ages = pd.to_numeric(df["Age"], errors="coerce").dropna()
                if not ages.empty:
                    amin, amax = int(ages.min()), int(ages.max())
                    amin_c, amax_c = max(14, amin), min(45, amax)
                    if amin_c >= amax_c:
                        st.caption(f"Age range: {amin_c} only")
                        st.session_state.pop(STATE_AGE_KEY, None)
                    else:
                        default_age = st.session_state.get(STATE_AGE_KEY, (amin_c, amax_c))
                        d0 = max(amin_c, min(default_age[0], amax_c))
                        d1 = max(amin_c, min(default_age[1], amax_c))
                        if d0 > d1: d0, d1 = d1, d0
                        age_min, age_max = st.slider("Age", min_value=amin_c, max_value=amax_c, value=(d0, d1), key=STATE_AGE_KEY)
                else:
                    st.caption("No age data")
        with c5:
            club_vals = sorted([v for v in _col(df, "CurrentClub").dropna().astype(str).unique() if v])
            club_sel = st.multiselect("Current club", club_vals, default=st.session_state.get(STATE_CLUB_KEY, []), key=STATE_CLUB_KEY)
        with c6:
            if st.button("Reset", help="Clear all filters"):
                st.session_state[STATE_Q_KEY] = ""
                st.session_state[STATE_POS_KEY] = []
                st.session_state[STATE_FOOT_KEY] = []
                st.session_state[STATE_CLUB_KEY] = []
                st.session_state.pop(STATE_AGE_KEY, None)
                st.rerun()

    # Chips
    chips = []
    if q: chips.append(f"🔎 {q}")
    if pos_sel: chips.append("📍 " + "/".join(pos_sel))
    if foot_sel: chips.append("🦶 " + "/".join(foot_sel))
    if (STATE_AGE_KEY in st.session_state) or (age_min is not None and age_max is not None):
        lo, hi = (st.session_state.get(STATE_AGE_KEY, (age_min, age_max)))
        if lo is not None and hi is not None: chips.append(f"🎂 {lo}-{hi}")
    if club_sel: chips.append("🏟️ " + "/".join(club_sel))
    if chips:
        st.markdown(" ".join(f"<span class='sl-chip'>{c}</span>" for c in chips), unsafe_allow_html=True)

    # --------- Saved Views ----------
    st.session_state.setdefault(STATE_SAVED_VIEWS_KEY, {})
    st.divider()
    st.caption("Saved Views")
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
            if v.get("age") is not None: st.session_state[STATE_AGE_KEY] = tuple(v["age"])
            else: st.session_state.pop(STATE_AGE_KEY, None)
            st.rerun()

    # --------- Apply filters ----------
    df_show = df.copy()
    if q: df_show = df_show[df_show["name"].astype(str).str.contains(q, case=False, na=False)]
    if pos_sel: df_show = df_show[_col(df_show, "Position").astype(str).isin(pos_sel)]
    if foot_sel: df_show = df_show[_col(df_show, "Foot").astype(str).isin(foot_sel)]
    if (STATE_AGE_KEY in st.session_state) or (age_min is not None and age_max is not None):
        lo, hi = st.session_state.get(STATE_AGE_KEY, (age_min, age_max))
        if lo is not None and hi is not None and "Age" in df_show.columns:
            df_show = df_show[pd.to_numeric(df_show["Age"], errors="coerce").between(lo, hi, inclusive="both")]
    if club_sel:
        df_show = df_show[_col(df_show, "CurrentClub").astype(str).isin(club_sel)]

    st.markdown(f"**Results:** {len(df_show)} / {len(df)}  •  Columns: {len(df_show.columns)}")

    # Visible columns & sorting
    preferred_cols = ["id","name","Position","Age","CurrentClub","Foot","team_name"]
    rating_like = [c for c in df_show.columns if c not in preferred_cols and pd.api.types.is_numeric_dtype(df_show[c])]
    if st.session_state.get(STATE_VISIBLE_COLS_KEY):
        preferred_cols = [c for c in st.session_state[STATE_VISIBLE_COLS_KEY] if c in df_show.columns]
    else:
        preferred_cols = [c for c in preferred_cols if c in df_show.columns] + rating_like[:6]

    use_cards = len(df_show) <= CARD_THRESHOLD

    # --------- Render ----------
    if len(df_show) == 0:
        st.info("No matches with current filters.")
    elif use_cards and "id" in df_show.columns:
        st.write("Click ☆ to add to shortlist.")
        # init shortlist state
        if STATE_SHORTLIST_KEY not in st.session_state:
            st.session_state[STATE_SHORTLIST_KEY] = _load_shortlist()

        def _shortlist_toggle(pid: str):
            if not pid: return
            s = st.session_state[STATE_SHORTLIST_KEY]
            if pid in s: s.remove(pid)
            else: s.add(pid)
            _save_shortlist(s)

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
                    n = r.get("name",""); pos = r.get("Position",""); age = r.get("Age",""); club = r.get("CurrentClub","")
                    st.markdown(f"**{_safe_str(n)}**  \n{_safe_str(pos)} • Age {age} • {club}")
                with c2:
                    if top_numeric:
                        kv = " • ".join(f"{c}: {r[c] if pd.notna(r.get(c)) else ''}" for c in top_numeric if c in r)
                        if kv: st.caption(kv)
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
        show_cols = preferred_cols if preferred_cols else list(df_show.columns)
        st.markdown("<div class='sl-table'>", unsafe_allow_html=True)
        st.dataframe(df_show[show_cols].reset_index(drop=True), use_container_width=True, height=520)
        st.markdown("</div>", unsafe_allow_html=True)

    # --------- Export ----------
    st.markdown("### Export")
    df_export = df_show.reset_index(drop=True)
    st.download_button("⬇️ Download CSV", df_export.to_csv(index=False).encode("utf-8"),
                       file_name=f"{team.replace(' ', '_')}_players.csv", mime="text/csv")
    st.download_button("⬇️ Download JSON",
                       df_export.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8"),
                       file_name=f"{team.replace(' ', '_')}_players.json", mime="application/json")

# Suora ajo
if __name__ == "__main__":
    show_team_view()
