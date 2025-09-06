# player_editor.py — Optimized Player Editor (Create Team + safe team select + NaT-safe dates + Storage backend)
from __future__ import annotations
import json, math, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import date, datetime

import pandas as pd
import streamlit as st

# --- storage (Supabase jos secrets, muuten JSON) ---
from storage import Storage
storage = Storage()

# --- projektin apurit ---
from app_paths import DATA_DIR, PLAYERS_FP, SHORTLISTS_FP, PLAYER_PHOTOS_DIR
from data_utils import (
    list_teams, load_master, save_master,
    load_seasonal_stats, save_seasonal_stats, BASE_DIR,
    initialize_team_folder
)

# -------------------------------------------------------
# Polut
# -------------------------------------------------------
# Huom: PLAYERS_FP ei ole enää välttämätön storagen kanssa, mutta pidetään polut yhtenäisinä

# -------------------------------------------------------
# Yleiset apurit
# -------------------------------------------------------
DEFAULT_COLUMNS = [
    "PlayerID","Name","Nationality","DateOfBirth","PreferredFoot",
    "ClubNumber","Position","ScoutRating","TransfermarktURL"
]

TM_RX = re.compile(r"^https?://(www\.)?transfermarkt\.[^/\s]+/.*", re.IGNORECASE)

def _load_json(fp: Path, default):
    try:
        if fp.exists():
            return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def _save_json(fp: Path, data):
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _normalize_nationality(val) -> str:
    if val is None:
        return ""
    if isinstance(val, (list, tuple, set)):
        return ", ".join([str(x).strip() for x in val if str(x).strip()])
    return str(val).strip()

def _as_str(x: object, default: str = "") -> str:
    if x is None:
        return default
    if isinstance(x, float) and math.isnan(x):
        return default
    s = str(x).strip()
    if s.lower() in {"nan", "none", "null"}:
        return default
    return s

def _as_int(x: object, default: int = 0) -> int:
    try:
        if x is None:
            return default
        if isinstance(x, float) and math.isnan(x):
            return default
        if isinstance(x, str) and x.strip().lower() in {"", "nan", "none", "null"}:
            return default
        return int(float(x))
    except Exception:
        return default

# ---------- DOB: salli 1900 ... tänään ----------
BIRTHDATE_MIN = date(1900, 1, 1)
BIRTHDATE_MAX = date.today()

def _clamp_date(d: date, lo: date, hi: date) -> date:
    try:
        if d < lo: return lo
        if d > hi: return hi
        return d
    except Exception:
        return lo

# ---------- NaT-safe päivämäärät ----------
def _to_date(x) -> Optional[date]:
    """Palauttaa python date-olion tai None. Kestää str, date/datetime,
    pd.Timestamp, np.datetime64, pd.NaT."""
    if x is None:
        return None

    # Pandas: NaT / NA / NaN
    try:
        if pd.isna(x):  # True myös pd.NaT:lle
            return None
    except Exception:
        pass

    # Pandas Timestamp
    try:
        if isinstance(x, pd.Timestamp):
            if pd.isna(x):
                return None
            return x.to_pydatetime().date()
    except Exception:
        pass

    # Numpy datetime64
    try:
        import numpy as np  # noqa
        if isinstance(x, np.datetime64):
            dt = pd.to_datetime(x, errors="coerce")
            return dt.date() if pd.notna(dt) else None
    except Exception:
        pass

    # Python datetime/date
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x

    # String tms.
    s = _as_str(x)
    if not s:
        return None
    dt = pd.to_datetime(s, errors="coerce")
    return dt.date() if pd.notna(dt) else None

def _as_date_str(x) -> str:
    """Palauttaa YYYY-MM-DD tai tyhjän."""
    # Suora normalisointi pd.NaT/None/tyhjään
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    if isinstance(x, date) and not isinstance(x, datetime):
        return x.isoformat()
    if isinstance(x, datetime):
        return x.date().isoformat()
    s = _as_str(x)
    if not s:
        return ""
    dt = pd.to_datetime(s, errors="coerce")
    return dt.date().isoformat() if pd.notna(dt) else ""

def _date_input(label: str, value, key: str) -> Optional[date]:
    """Streamlit date_input kovalla varmistuksella ja selkeillä rajoilla (1900 → tänään).
    Palauttaa None jos arvo puuttuu."""
    raw = _to_date(value)
    missing = raw is None
    safe = _clamp_date(raw or BIRTHDATE_MIN, BIRTHDATE_MIN, BIRTHDATE_MAX)
    try:
        picked = st.date_input(
            label,
            value=safe,
            min_value=BIRTHDATE_MIN,
            max_value=BIRTHDATE_MAX,
            format="YYYY-MM-DD",
            key=key,
            help="Select birth date (1900 → today)"
        )
    except TypeError:
        picked = st.date_input(
            label,
            value=safe,
            min_value=BIRTHDATE_MIN,
            max_value=BIRTHDATE_MAX,
            key=key
        )
    return None if (missing and picked == BIRTHDATE_MIN) else picked

def _next_free_id(existing_ids):
    existing = set(int(x) for x in existing_ids if pd.notna(x))
    idx = 1
    while idx in existing:
        idx += 1
    return idx

def _ensure_player_id(df: pd.DataFrame):
    if "PlayerID" not in df.columns or df["PlayerID"].isnull().all():
        df["PlayerID"] = [i + 1 for i in range(len(df))]
    return df

def _ensure_min_columns(df: pd.DataFrame):
    for col in DEFAULT_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col not in ("ClubNumber","ScoutRating","PlayerID") else 0
    return df

def _valid_tm_url(url: str) -> bool:
    if not url:
        return True
    return bool(TM_RX.match(url.strip()))

# -------------------------------------------------------
# Selectbox-suoja joukkuevalinnalle
# -------------------------------------------------------
TEAM_PLACEHOLDER = "— Select team —"

def _safe_team_name_ui(name: str) -> str:
    return (name or "").strip().replace("  ", " ").replace(" ", "_").upper()

def _resolve_team_selection(value, teams: List[str]) -> str:
    if not value:
        return TEAM_PLACEHOLDER
    if value in teams:
        return value
    val_safe = _safe_team_name_ui(str(value))
    for t in teams:
        if t == value:
            return t
        if _safe_team_name_ui(t) == str(value):
            return t
        if _safe_team_name_ui(t) == val_safe:
            return t
    return TEAM_PLACEHOLDER

# -------------------------------------------------------
# Storage-ohjatut apurit
# -------------------------------------------------------
def upsert_player_storage(player: dict) -> str:
    return storage.upsert_player(player)

def remove_from_players_storage_by_ids(ids: List[str]) -> int:
    return storage.remove_by_ids([str(x) for x in ids])

def _save_photo_and_link_storage(player_id: str, filename: str, content: bytes) -> Path:
    PLAYER_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() or ".png"
    safe_name = Path(filename).stem.replace(" ", "-")
    out = PLAYER_PHOTOS_DIR / f"{safe_name}-{player_id[:6]}{ext}"
    out.write_bytes(content)
    storage.set_photo_path(player_id, str(out))
    return out

# -------------------------------------------------------
# Shortlist apurit (säilytetään JSONissa toistaiseksi)
# -------------------------------------------------------
def _load_shortlists() -> Dict[str, List[Any]]:
    raw = _load_json(SHORTLISTS_FP, {})
    if isinstance(raw, dict) and "lists" in raw and isinstance(raw["lists"], list):
        out: Dict[str, List[Any]] = {}
        for lst in raw["lists"]:
            name = lst.get("name") or lst.get("title") or "default"
            items = lst.get("items") or lst.get("players") or []
            out[name] = items if isinstance(items, list) else []
        return out
    if isinstance(raw, dict):
        return {k: (v if isinstance(v, list) else []) for k, v in raw.items()}
    if isinstance(raw, list):
        return {"default": raw}
    return {}

def _save_shortlists(data: Dict[str, List[Any]]):
    _save_json(SHORTLISTS_FP, data)

def _players_index_by_id() -> Dict[str, Dict[str, Any]]:
    # LUETAAN PELAAJAT STORAGESTA (ei enää players.jsonista)
    players = storage.list_players()
    out = {}
    for p in players:
        pid = str(p.get("id") or "")
        if pid:
            out[pid] = p
    return out

def _resolve_shortlist_items(items: List[Any]) -> List[Dict[str, Any]]:
    idx = _players_index_by_id()
    out = []
    for it in items:
        rec = {"id": "", "name": "", "team_name": "", "source": "unknown"}
        if isinstance(it, (str, int)):
            pid = str(it); base = idx.get(pid, {})
            rec.update({"id": pid, "name": base.get("name",""), "team_name": base.get("team_name",""), "source": "id"})
        elif isinstance(it, dict):
            pid = str(it.get("id") or "")
            nm  = _as_str(it.get("name",""))
            tm  = _as_str(it.get("team") or it.get("team_name",""))
            if pid and pid in idx:
                base = idx[pid]; nm = nm or base.get("name",""); tm = tm or base.get("team_name","")
            rec.update({"id": pid, "name": nm, "team_name": tm, "source": "dict"})
        elif isinstance(it, (list, tuple)) and len(it) == 2:
            nm = _as_str(it[0]); tm = _as_str(it[1])
            pid_guess = ""
            for pid, p in idx.items():
                if p.get("name","") == nm and p.get("team_name","") == tm:
                    pid_guess = pid; break
            rec.update({"id": pid_guess, "name": nm, "team_name": tm, "source": "pair"})
        else:
            continue
        out.append(rec)
    # dedup
    seen = set(); deduped = []
    for r in out:
        key = r["id"] or (r["name"], r["team_name"])
        if key in seen:
            continue
        seen.add(key); deduped.append(r)
    return deduped

def _is_member(items: List[Any], pid: str, name: str, team: str) -> Tuple[bool, int]:
    for i, it in enumerate(items):
        if isinstance(it, (str, int)) and str(it) == pid:
            return True, i
        if isinstance(it, dict):
            if (str(it.get("id") or "") == pid) or (
                it.get("name","") == name and (it.get("team") or it.get("team_name","")) == team
            ):
                return True, i
        if isinstance(it, (list, tuple)) and len(it) == 2:
            if it[0] == name and it[1] == team:
                return True, i
    return False, -1

def _add_to_shortlist(shortlists: Dict[str, List[Any]], list_name: str, pid: str, name: str, team: str):
    items = shortlists.setdefault(list_name, [])
    present, _ = _is_member(items, pid, name, team)
    if not present:
        items.append(pid if pid else [name, team])

def _remove_from_shortlist(shortlists: Dict[str, List[Any]], list_name: str, pid: str, name: str, team: str):
    items = shortlists.get(list_name, [])
    present, idx = _is_member(items, pid, name, team)
    if present and idx >= 0:
        items.pop(idx)

# -------------------------------------------------------
# UI — päätoiminto
# -------------------------------------------------------
def show_player_editor():
    st.header("💼 Player Editor")
    st.caption(f"Data folder → {DATA_DIR}")

    # segmented_control jos löytyy, muuten radio
    seg = getattr(st, "segmented_control", None)
    if callable(seg):
        source = st.segmented_control("Source", options=["Team", "Shortlist"], key="pe_source")
    else:
        source = st.radio("Source", options=["Team", "Shortlist"], horizontal=True, key="pe_source")

    if source == "Shortlist":
        return _render_shortlist_flow()

    # --- TEAM FLOW ---
    with st.expander("🆕 Create Team", expanded=False):
        new_team = st.text_input("Team name", key="pe_new_team_name", placeholder="Club Atlético Example")
        if st.button("Create team", key="pe_create_team_btn"):
            pretty = (new_team or "").strip()
            if not pretty:
                st.warning("Anna joukkueelle nimi.")
            else:
                existing = list_teams()
                if any(pretty.lower() == t.lower() for t in existing):
                    st.info("Joukkue on jo olemassa. Valitse se alta.")
                else:
                    initialize_team_folder(pretty)
                    st.success(f"Team '{pretty}' created.")
                    teams_after = list_teams()
                    st.session_state["pe_team_select"] = _resolve_team_selection(pretty, teams_after)
                    st.rerun()

    teams = list_teams()
    # Normalisoi olemassa oleva arvo ennen selectboxin piirtämistä
    st.session_state["pe_team_select"] = _resolve_team_selection(st.session_state.get("pe_team_select"), teams)

    selected_label = st.selectbox(
        "Select Team",
        ["— Select team —"] + teams,
        key="pe_team_select"
    )
    selected_team = "" if selected_label == "— Select team —" else selected_label
    if not selected_team:
        return

    _render_team_editor_flow(selected_team, preselected_name=None)

# -------------------------------------------------------
# Shortlist-selailu ja ohjaus editoriin
# -------------------------------------------------------
def _render_shortlist_flow():
    shortlists = _load_shortlists()
    if not shortlists:
        st.info("Ei shortlisteja vielä. Luo listat Home/Team View -sivuilla tai luo uusi tässä.")
        new_name = st.text_input("Uuden shortlistin nimi", value="default", key="pe_new_shortlist_name")
        if st.button("Luo shortlist"):
            if new_name.strip():
                shortlists[new_name.strip()] = []
                _save_shortlists(shortlists)
                st.success(f"Shortlist '{new_name.strip()}' luotu.")
        return

    sl_names = sorted(shortlists.keys())
    chosen_list = st.selectbox("Valitse shortlist", sl_names, key="pe_sl_select")

    resolved = _resolve_shortlist_items(shortlists.get(chosen_list, []))
    if not resolved:
        st.warning("Tämä shortlist on tyhjä.")
    else:
        df_view = pd.DataFrame(resolved)[["name","team_name","id","source"]]
        st.dataframe(df_view, use_container_width=True, hide_index=True)

    names_for_pick = [f"{r['name']} — {r['team_name']} [{r['id'] or 'no-id'}]" for r in resolved]
    pick = st.selectbox("Muokkaa pelaajaa", [""] + names_for_pick, index=0, key="pe_sl_pick")
    if not pick:
        return

    idx = names_for_pick.index(pick)
    sel = resolved[idx]
    sel_team = sel.get("team_name","").strip()
    sel_name = sel.get("name","").strip()
    if not sel_team or not sel_name:
        st.error("Shortlist-kohteelta puuttuu nimi tai seura.")
        return

    # pikajäsenyys
    is_in, _ = _is_member(shortlists.get(chosen_list, []), str(sel.get("id") or ""), sel_name, sel_team)
    new_status = st.checkbox(f"'{chosen_list}' shortlistissa", value=is_in, key="pe_sl_checkbox")
    if new_status != is_in:
        if new_status:
            _add_to_shortlist(shortlists, chosen_list, str(sel.get("id") or ""), sel_name, sel_team)
        else:
            _remove_from_shortlist(shortlists, chosen_list, str(sel.get("id") or ""), sel_name, sel_team)
        _save_shortlists(shortlists)
        st.success("Shortlist päivitetty.")

    st.divider()
    _render_team_editor_flow(sel_team, preselected_name=sel_name)

# -------------------------------------------------------
# Tiimi-editorin varsinainen virta
# -------------------------------------------------------
def _render_team_editor_flow(selected_team: str, preselected_name: Optional[str]):
    df_master = load_master(selected_team)

    # jos tyhjä, älä poistu vaan luo UI ekaa riviä varten
    empty_state = (df_master is None or df_master.empty)
    if empty_state:
        st.warning("No player data for the selected team. Create the first row below.")
        df_master = pd.DataFrame(columns=DEFAULT_COLUMNS)

    df_master = _ensure_player_id(_ensure_min_columns(df_master))

    # ---------- Lisää ensimmäinen rivi, jos rosteri on tyhjä ----------
    if empty_state:
        if st.button("➕ Create first player row", key=f"pe_first_row__{selected_team}"):
            new_id = _next_free_id(df_master["PlayerID"].dropna().astype(int).tolist()) if "PlayerID" in df_master.columns else 1
            new_row = {col: "" for col in df_master.columns}
            new_row.update({"PlayerID": new_id, "Name": "New Player"})
            df_master = pd.concat([df_master, pd.DataFrame([new_row])], ignore_index=True)
            save_master(df_master, selected_team)
            st.success("First player row created.")
            st.rerun()

    # ---------- Full table editor ----------
    with st.expander("🧩 Full table editor (whole roster)", expanded=False):
        edit_cols = [c for c in DEFAULT_COLUMNS if c in df_master.columns]
        table_edit = st.data_editor(
            df_master[edit_cols],
            use_container_width=True,
            num_rows="dynamic",
            key=f"pe_full_editor__{selected_team}"
        )
        if st.button("💾 Save table", key=f"pe_save_table__{selected_team}"):
            df_master.loc[:, edit_cols] = table_edit.loc[:, edit_cols].values

            # numerot
            for num_col in ("PlayerID","ClubNumber","ScoutRating"):
                if num_col in df_master.columns:
                    df_master[num_col] = pd.to_numeric(df_master[num_col], errors="coerce").fillna(0).astype(int)

            # stringit + päivämäärä normalisointi
            for text_col in ("Name","Nationality","PreferredFoot","Position","TransfermarktURL"):
                if text_col in df_master.columns:
                    df_master[text_col] = df_master[text_col].apply(_as_str)
            if "DateOfBirth" in df_master.columns:
                df_master["DateOfBirth"] = df_master["DateOfBirth"].apply(_as_date_str)

            # täytä puuttuvat PlayerID:t
            if (df_master["PlayerID"] == 0).any():
                used = [x for x in df_master["PlayerID"].tolist() if x > 0]
                for _, idx in enumerate(df_master.index[df_master["PlayerID"] == 0], start=1):
                    df_master.at[idx, "PlayerID"] = _next_free_id(used)
                    used.append(df_master.at[idx, "PlayerID"])

            save_master(df_master, selected_team)
            st.success("Table saved.")

    # ---------- Lisää uusi rivi aina näkyvissä ----------
    with st.expander("➕ Add New Player", expanded=False):
        if st.button("Add row", key=f"pe_add_row__{selected_team}"):
            existing_ids = df_master["PlayerID"].dropna().astype(int).tolist()
            new_id = _next_free_id(existing_ids)
            new_row = {col: "" for col in df_master.columns}
            new_row.update({"PlayerID": new_id, "Name": "New Player"})
            df_master = pd.concat([df_master, pd.DataFrame([new_row])], ignore_index=True)
            save_master(df_master, selected_team)
            st.success("New player row added.")
            st.rerun()
        st.caption("Vinkki: käytä yläpuolen 'Full table editor' -osiota massamuokkaukseen.")

    # ---------- Haku + yhden rivin editori ----------
    st.subheader("🔍 Find Player (single-row editor)")
    c_s1, c_s2 = st.columns([3, 1])
    with c_s1:
        search_term = st.text_input("Search by name", key=f"pe_search__{selected_team}")
    with c_s2:
        sort_by = st.selectbox("Sort by", options=[col for col in ["Name", "ScoutRating"] if col in df_master.columns], key=f"pe_sort__{selected_team}")

    df_sorted = df_master.sort_values(by=sort_by) if sort_by in df_master.columns else df_master
    df_filtered = df_sorted
    if search_term and "Name" in df_sorted.columns:
        df_filtered = df_sorted[df_sorted["Name"].str.contains(search_term, case=False, na=False)]

    names = df_filtered["Name"].dropna().unique().tolist() if "Name" in df_filtered.columns else []
    if not names:
        st.info("Roster is empty. Add a player with the buttons above.")
        return

    default_idx = names.index(preselected_name) if preselected_name and preselected_name in names else 0
    selected_name = st.selectbox("Select Player to Edit", names, index=(default_idx if names else 0), key=f"pe_pick__{selected_team}")

    if not selected_name:
        return

    selected_row_df = df_master[df_master["Name"] == selected_name].copy()
    if selected_row_df.empty:
        st.warning("Selected player not found in master after filtering.")
        return
    row = selected_row_df.iloc[0].to_dict()
    pid_int = _as_int(row.get("PlayerID"), 0)
    pid_str = str(pid_int or uuid4().hex)

    # ---------- Välilehdet ----------
    tabs = st.tabs(["✏️ Basic Info", "🔗 Links", "🖼️ Photo & Tags", "📅 Season Stats", "⭐ Shortlist", "🗑️ Actions"])

    # ✏️ Basic Info
    with tabs[0]:
        st.markdown(f"### Editing Player: {selected_name}")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("PlayerID", value=str(pid_int or ""), disabled=True)
        with c2:
            name_val = st.text_input("Name", value=_as_str(row.get("Name","")), key=f"pe_name__{selected_team}_{pid_int}")
        with c3:
            st.text_input("Team (master file)", value=str(selected_team), disabled=True)

        c4, c5, c6 = st.columns(3)
        with c4:
            dob_date = _date_input("DateOfBirth", value=row.get("DateOfBirth"), key=f"pe_dob__{selected_team}_{pid_int}")
        with c5:
            nat_val = st.text_input("Nationality (A, B)", value=_normalize_nationality(_as_str(row.get("Nationality",""))), key=f"pe_nat__{selected_team}_{pid_int}")
        with c6:
            pos_val = st.text_input("Position", value=_as_str(row.get("Position","")), key=f"pe_pos__{selected_team}_{pid_int}")

        c7, c8, c9 = st.columns(3)
        pref_options = ["", "Right", "Left", "Both"]
        current_pref = _as_str(row.get("PreferredFoot",""))
        pref_index   = pref_options.index(current_pref) if current_pref in pref_options else 0
        with c7:
            pref_foot = st.selectbox("PreferredFoot", pref_options, index=pref_index, key=f"pe_pref__{selected_team}_{pid_int}")
        with c8:
            club_num = st.number_input("ClubNumber", min_value=0, max_value=999, value=_as_int(row.get("ClubNumber"), 0), key=f"pe_clubnum__{selected_team}_{pid_int}")
        with c9:
            scout_rating = st.number_input("ScoutRating (0–100)", min_value=0, max_value=100, value=_as_int(row.get("ScoutRating"), 0), key=f"pe_rating__{selected_team}_{pid_int}")

        tm_url_val = st.text_input("Transfermarkt URL", value=_as_str(row.get("TransfermarktURL","")), placeholder="https://www.transfermarkt.com/...", key=f"pe_tmurl__{selected_team}_{pid_int}")
        if tm_url_val and not _valid_tm_url(tm_url_val):
            st.warning("URL ei näytä Transfermarkt-osoitteelta.")

        problems = []
        if not name_val.strip(): problems.append("Name is required.")
        if not selected_team.strip(): problems.append("Team is required.")
        if problems:
            st.info(" | ".join(problems))

        if st.button("💾 Save Basic Info", key=f"pe_save_basic__{selected_team}_{pid_int}"):
            idxs = df_master[df_master["PlayerID"] == pid_int].index
            if not idxs.empty:
                idx = idxs[0]
                df_master.at[idx, "Name"]            = name_val.strip()
                df_master.at[idx, "Nationality"]     = _as_str(nat_val)
                df_master.at[idx, "DateOfBirth"]     = _as_date_str(dob_date)
                df_master.at[idx, "PreferredFoot"]   = _as_str(pref_foot)
                df_master.at[idx, "ClubNumber"]      = _as_int(club_num, 0)
                df_master.at[idx, "Position"]        = _as_str(pos_val)
                df_master.at[idx, "ScoutRating"]     = _as_int(scout_rating, 0)
                df_master.at[idx, "TransfermarktURL"]= _as_str(tm_url_val)
                save_master(df_master, selected_team)
                st.success("Basic info saved.")
            else:
                st.error("Could not locate row to update.")

        st.markdown("---")
        st.markdown("### 📄 Save THIS player to storage")
        if st.button("⬇️ Save THIS player", key=f"pe_push_this__{selected_team}_{pid_int}"):
            player_data = {
                "id": pid_str,
                "name": _as_str(name_val),
                "date_of_birth": _as_date_str(dob_date),
                "nationality": _normalize_nationality(_as_str(nat_val)),
                "preferred_foot": _as_str(pref_foot),
                "club_number": _as_int(club_num, 0),
                "team_name": _as_str(selected_team),
                "position": _as_str(pos_val),
                "scout_rating": _as_int(scout_rating, 0),
                "transfermarkt_url": _as_str(tm_url_val),
            }
            if not _valid_tm_url(player_data["transfermarkt_url"]):
                st.error("Transfermarkt URL näyttää virheelliseltä.")
            else:
                pid_out = upsert_player_storage(player_data)
                st.success(f"✅ Saved (id={pid_out})")

    # 🔗 Links
    with tabs[1]:
        st.subheader("🔗 Links")
        tm_url = ""
        try:
            if "TransfermarktURL" in df_master.columns:
                tm_url = _as_str(df_master.loc[df_master["PlayerID"]==pid_int, "TransfermarktURL"].values[0])
        except Exception:
            tm_url = ""
        st.write("Transfermarkt:", tm_url or "—")
        if tm_url:
            try:
                st.link_button("Open Transfermarkt", tm_url, help="Avaa pelaajan Transfermarkt-sivu")
            except Exception:
                st.markdown(f"[Open Transfermarkt]({tm_url})")

    # 🖼️ Photo & Tags
    with tabs[2]:
        st.subheader("🖼️ Photo & Tags")
        up = st.file_uploader("Upload player photo (PNG/JPG)", type=["png","jpg","jpeg"], key=f"pe_photo__{selected_team}_{pid_int}")
        if up is not None:
            out = _save_photo_and_link_storage(pid_str, up.name, up.read())
            st.success(f"Photo saved: {out}")

        tags_key = f"tags_{pid_str}"
        current_tags = st.session_state.get(tags_key, "")
        tag_str = st.text_input("Tags (comma-separated)", value=current_tags, key=f"pe_tags__{selected_team}_{pid_int}")
        st.session_state[tags_key] = tag_str
        st.caption("Vinkki: muutama iskevä tagi (esim. 'Press-resistance, Pace, Leader').")

        if st.button("💾 Save tags", key=f"pe_save_tags__{selected_team}_{pid_int}"):
            tags = [t.strip() for t in tag_str.split(",") if t.strip()]
            storage.set_tags(pid_str, tags)
            st.success("Tags saved.")

    # 📅 Season Stats
    with tabs[3]:
        st.subheader(f"📅 Season-Specific Stats — {selected_name}")
        stats_df = load_seasonal_stats(selected_team)
        if stats_df is None or stats_df.empty:
            st.info("No seasonal stats defined for this team yet.")
        else:
            name_col = None
            for c in stats_df.columns:
                if c.lower() == "name":
                    name_col = c
                    break

            if not name_col:
                st.warning("Cannot edit: no 'Name' column in seasonal_stats.csv.")
            else:
                player_stats = stats_df[stats_df[name_col] == selected_name]
                if player_stats.empty:
                    st.info("No stats for this player. Create new entry:")
                    new_stats = {name_col: selected_name}
                    for col in stats_df.columns:
                        if col != name_col:
                            new_stats[col] = 0
                    df_new = pd.DataFrame([new_stats])
                    edited_stats = st.data_editor(
                        df_new,
                        num_rows="fixed",
                        use_container_width=True,
                        key=f"pe_stats_new__{selected_team}_{pid_int}"
                    )
                    if st.button("💾 Create Season Stats", key=f"pe_stats_create__{selected_team}_{pid_int}"):
                        merged = pd.concat([stats_df, edited_stats], ignore_index=True)
                        save_seasonal_stats(merged, selected_team)
                        st.success("Season stats created.")
                else:
                    edited_stats = st.data_editor(
                        player_stats,
                        num_rows="fixed",
                        use_container_width=True,
                        key=f"pe_stats_edit__{selected_team}_{pid_int}"
                    )
                    if st.button("💾 Save Season Stats", key=f"pe_stats_save__{selected_team}_{pid_int}"):
                        mask = stats_df[name_col] == selected_name
                        stats_df.loc[mask, :] = edited_stats.values
                        save_seasonal_stats(stats_df, selected_team)
                        st.success("Season stats saved.")

    # ⭐ Shortlist
    with tabs[4]:
        st.subheader("⭐ Shortlist membership")
        shortlists = _load_shortlists()
        if not shortlists:
            st.info("Ei shortlisteja vielä.")
        else:
            current_name = selected_name
            for sl_name in sorted(shortlists.keys()):
                items = shortlists.get(sl_name, [])
                on_list, _ = _is_member(items, pid_str, current_name, _as_str(selected_team))
                new_val = st.checkbox(sl_name, value=on_list, key=f"pe_sl_mem__{sl_name}_{selected_team}_{pid_int}")
                if new_val != on_list:
                    if new_val:
                        _add_to_shortlist(shortlists, sl_name, pid_str, current_name, _as_str(selected_team))
                    else:
                        _remove_from_shortlist(shortlists, sl_name, pid_str, current_name, _as_str(selected_team))
                    _save_shortlists(shortlists)
                    st.success(f"Shortlist '{sl_name}' päivitetty.")

    # 🗑️ Actions
    with tabs[5]:
        st.subheader("🗑️ Actions")
        a1, a2, a3 = st.columns(3)
        with a1:
            if st.button("Duplicate row", key=f"pe_dup__{selected_team}_{pid_int}"):
                copy = df_master[df_master["PlayerID"]==pid_int].iloc[0].copy()
                copy["PlayerID"] = _next_free_id(df_master["PlayerID"].dropna().astype(int).tolist())
                copy["Name"] = f"{copy.get('Name','')} (copy)"
                df_master = pd.concat([df_master, pd.DataFrame([copy])], ignore_index=True)
                save_master(df_master, selected_team)
                st.success("Row duplicated.")
        with a2:
            new_team = st.selectbox("Move to team", options=[""] + list_teams(), index=0, key=f"pe_move_team__{selected_team}_{pid_int}")
            if new_team and st.button("Move now", key=f"pe_move_now__{selected_team}_{pid_int}"):
                if new_team == selected_team:
                    st.warning("Same team selected.")
                else:
                    src = df_master.copy()
                    row_to_move = src[src["PlayerID"] == pid_int]
                    src = src[src["PlayerID"] != pid_int]
                    save_master(src, selected_team)
                    if not row_to_move.empty:
                        target_master = load_master(new_team)
                        if target_master is None:
                            target_master = pd.DataFrame(columns=DEFAULT_COLUMNS)
                        target_master = _ensure_player_id(_ensure_min_columns(target_master))
                        new_pid = _next_free_id(target_master["PlayerID"].dropna().astype(int).tolist())
                        row_to_move = row_to_move.copy()
                        row_to_move.loc[:, "PlayerID"] = new_pid
                        target_master = pd.concat([target_master, row_to_move], ignore_index=True)
                        save_master(target_master, new_team)
                        st.success(f"Player moved to {new_team}.")
        with a3:
            st.warning("Type DELETE to confirm deletion from master file", icon="⚠️")
            conf = st.text_input("Confirmation", key=f"pe_del_conf__{selected_team}_{pid_int}", placeholder="DELETE")
            if st.button("Delete row from master", key=f"pe_del_row__{selected_team}_{pid_int}", disabled=(conf != "DELETE")):
                df_master = df_master[df_master["PlayerID"] != pid_int]
                save_master(df_master, selected_team)
                st.success("Row deleted from master.")

        st.markdown("---")
        st.subheader("Remove from storage")
        st.caption("Siivoa taustavarastoa sotkematta master-tiedostoa.")
        conf2 = st.text_input("Type REMOVE to confirm", key=f"pe_del_json_conf__{selected_team}_{pid_int}", placeholder="REMOVE")
        if st.button("Remove by PlayerID", key=f"pe_del_json_byid__{selected_team}_{pid_int}", disabled=(conf2 != "REMOVE")):
            n = remove_from_players_storage_by_ids([str(pid_str)])
            st.success(f"Removed {n} record(s) by id.")

        # (name, team) -poisto: etsitään id:t storagesta ja poistetaan ne
        if st.button("Remove by (name, team) pair", key=f"pe_del_json_bykey__{selected_team}_{pid_int}", disabled=(conf2 != "REMOVE")):
            nm = selected_name.strip()
            tm = _as_str(selected_team)
            ids = []
            for p in storage.list_players():
                if (p.get("name","").strip() == nm) and (p.get("team_name","").strip() == tm):
                    ids.append(str(p.get("id")))
            if ids:
                n = remove_from_players_storage_by_ids(ids)
                st.success(f"Removed {n} record(s) by (name, team).")
            else:
                st.info("No records matched (name, team) in storage.")
