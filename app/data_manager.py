import streamlit as st
import pandas as pd
import json
from pathlib import Path
from uuid import uuid4
from app.storage import load_json, save_json

from app.app_paths import file_path, DATA_DIR

# yritetään käyttää list_teams(), mutta ei ole pakollinen
try:
    from app.data_utils import list_teams
except Exception:
    list_teams = None  # fallback players.jsonista

PLAYERS_FP = file_path("players.json")

# ---------- JSON apurit ----------
def _load_players():
    try:
        if PLAYERS_FP.exists():
            return json.loads(PLAYERS_FP.read_text(encoding="utf-8"))
    except Exception as e:
        st.error(f"Failed to read players.json: {e}")
    return []

def _save_players(players):
    try:
        PLAYERS_FP.write_text(json.dumps(players, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        st.error(f"Failed to write players.json: {e}")

def _norm_team(p: dict) -> str:
    return (
        p.get("team_name")
        or p.get("Team")
        or p.get("team")
        or p.get("current_club")
        or p.get("CurrentClub")
        or ""
    ).strip()

def _to_df(players_for_team: list) -> pd.DataFrame:
    if not players_for_team:
        return pd.DataFrame(columns=["id", "name", "team_name"])

    # kerää kaikki kentät, jotta editori näyttää kaiken
    cols = set()
    for p in players_for_team:
        cols.update(p.keys())
    if not cols:
        cols = {"id", "name", "team_name"}

    rows = []
    for p in players_for_team:
        rows.append({c: p.get(c, None) for c in cols})
    df = pd.DataFrame(rows)

    # varmista id/name/team_name
    if "id" not in df.columns:
        if "PlayerID" in df.columns:
            df.rename(columns={"PlayerID": "id"}, inplace=True)
        else:
            df["id"] = ""
    if "name" not in df.columns and "Name" in df.columns:
        df.rename(columns={"Name": "name"}, inplace=True)
    if "team_name" not in df.columns:
        for c in ["team", "Team", "current_club", "CurrentClub"]:
            if c in df.columns:
                df["team_name"] = df[c]
                break
        if "team_name" not in df.columns:
            df["team_name"] = ""
    return df

def _clean_val(v):
    if pd.isna(v):
        return ""
    # pandas/np tyypit -> perus Python
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    try:
        import numpy as np
        if isinstance(v, np.integer):
            return int(v)
        if isinstance(v, np.floating):
            return float(v)
    except Exception:
        pass
    return v

# ---------- UI ----------
def show_data_manager():
    st.title("🛠️ ScoutLens Data Manager (JSON)")

    # 1) Valitse joukkue
    team = st.session_state.get("selected_team")
    if not team:
        # yritä ensin data_utils.list_teams(), muuten päättele players.jsonista
        teams = []
        if callable(list_teams):
            try:
                teams = list_teams() or []
            except Exception:
                teams = []
        if not teams:
            all_players = _load_players()
            teams = sorted({_norm_team(p) for p in all_players if _norm_team(p)})
        team = st.selectbox("Select a team to manage:", teams) if teams else None
        if team:
            # Kirjoita stateen vain jos arvo muuttuu (vältetään turhat rerunit)
            if team != st.session_state.get("selected_team"):
                st.session_state["selected_team"] = team

    if not team:
        st.warning("Please select a team to manage.")
        return

    # 2) Lataa ja suodata joukkueen pelaajat
    players_all = _load_players()
    team_players = [p for p in players_all if _norm_team(p) == team]
    df = _to_df(team_players)

    st.subheader(f"Players for {team}")
    try:
        edited = st.data_editor(
            df,
            key="dm_players_editor",
            num_rows="dynamic",
            use_container_width=True,
        )
    except AttributeError:
        st.error("Editable data grid not available in this Streamlit version.")
        st.dataframe(df)
        return

    # 3) Tallenna muutokset players.jsoniin (korvaa valitun joukkueen rivit)
    if st.button("Save Changes", key="dm_save_players"):
        try:
            kept = [p for p in players_all if _norm_team(p) != team]
            new_rows = []
            for _, row in edited.iterrows():
                rec = {col: _clean_val(row[col]) for col in edited.columns}
                # pakota minimit
                if not rec.get("id"):
                    rec["id"] = uuid4().hex
                if "name" not in rec and "Name" in rec:
                    rec["name"] = rec["Name"]
                if not rec.get("team_name"):
                    rec["team_name"] = team
                new_rows.append(rec)

            _save_players(kept + new_rows)
            st.success(f"Player data for {team} saved to players.json!")
        except Exception as e:
            st.error(f"Error saving data: {e}")

    # 4) Esikatselu
    st.markdown("### Preview Updated Data")
    st.dataframe(edited.reset_index(drop=True))
