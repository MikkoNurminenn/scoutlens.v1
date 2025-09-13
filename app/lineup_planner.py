import streamlit as st
import pandas as pd
import json
from pathlib import Path
from app.data_utils import BASE_DIR, list_teams, load_master

# Attempt mplsoccer import
try:
    from mplsoccer.pitch import Pitch
except ImportError:
    Pitch = None
import matplotlib.pyplot as plt

# Directory for saving lineups
LINEUP_DIR = BASE_DIR / "lineups"

# Only 4-3-3 formation settings\ nFORMATION = "4-3-3"
POSITIONS = ["GK", "LB", "CB", "CB2", "RB", "CDM", "CM", "CAM", "LW", "ST", "RW"]

# Coordinates for 4-3-3 on 120x80 pitch
FORMATION_COORDS = {
    "GK": (5, 40),
    "LB": (25, 70),
    "CB": (25, 30),
    "CB2": (25, 50),
    "RB": (25, 10),
    "CDM": (60, 40),
    "CM": (75, 25),
    "CAM": (75, 55),
    "LW": (95, 70),
    "ST": (105, 40),
    "RW": (95, 10)
}

# Color mapping for positions
group_color = {'GK': '#2ecc71', 'DEF': '#3498db', 'MID': '#9b59b6', 'FWD': '#e74c3c'}
def get_color(pos):
    if pos == 'GK': return group_color['GK']
    if pos in ['LB','CB','CB2','RB']: return group_color['DEF']
    if pos in ['CDM','CM','CAM','LW','RW']: return group_color['MID']
    return group_color['FWD']

# Save lineup to JSON file
def save_lineup(lineup, key):
    LINEUP_DIR.mkdir(exist_ok=True)
    path = LINEUP_DIR / f"{key}_lineup.json"
    with open(path, 'w') as f:
        json.dump(lineup, f)

# Load lineup from JSON file
def load_lineup(key):
    path = LINEUP_DIR / f"{key}_lineup.json"
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Draw 4-3-3 lineup on pitch using mplsoccer
def draw_lineup(lineup):
    if Pitch is None:
        st.error("`mplsoccer` not installed. Install via `pip install mplsoccer`.")
        return
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#111111', line_color='#888888')
    fig, ax = pitch.draw(figsize=(7, 10))
    for pos, player in lineup.items():
        if pos not in FORMATION_COORDS or not player:
            continue
        x, y_raw = FORMATION_COORDS[pos]
        y = 80 - y_raw
        parts = player.split()
        abbrev = ''.join(p[0] for p in parts)
        pitch.scatter(x, y, ax=ax, s=400, c=get_color(pos), edgecolors='k', linewidth=1.5, zorder=3)
        ax.text(x, y, abbrev, ha='center', va='center', color='white', fontsize=8,
                bbox=dict(facecolor='black', alpha=0.7, boxstyle='round,pad=0.2'), zorder=4)
    return fig

# Streamlit UI for 4-3-3 lineup planner with Team/Shortlist source
def show_lineup_planner():
    st.title("⚽ 4-3-3 Lineup Planner")

    # Select source: Team or Shortlist
    source = st.selectbox("Player Source", ["Team", "Shortlist"])
    df = pd.DataFrame()
    key = None

    if source == "Team":
        teams = list_teams()
        key = st.selectbox("Select Team", teams)
        if not key:
            st.warning("No team selected.")
            return
        df = load_master(key)
    else:
        # Load shortlist data
        sl_file = BASE_DIR / "shortlists.json"
        try:
            raw = json.loads(sl_file.read_text())
            shortlists = raw if isinstance(raw, dict) else {}
        except:
            shortlists = {}
        sl_names = list(shortlists.keys())
        key = st.selectbox("Select Shortlist", sl_names)
        if not key:
            st.warning("No shortlist selected.")
            return
        players = shortlists.get(key, [])
        # Aggregate players from all teams, resetting index
        dfs = []
        for team in list_teams():
            dft = load_master(team)
            if 'Name' in dft.columns:
                df_sel = dft[dft['Name'].isin(players)].reset_index(drop=True)
                if not df_sel.empty:
                    dfs.append(df_sel)
        df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    if df.empty:
        st.info("No players available.")
        return

    # Session key for storing lineup
    session_key = key
    if "lineup" not in st.session_state or st.session_state.get("session_key") != session_key:
        st.session_state.lineup = load_lineup(session_key)
        st.session_state.session_key = session_key

    st.subheader("Add Player to Formation")
    available_positions = [p for p in POSITIONS if p not in st.session_state.lineup]
    available_players = [n for n in df['Name'] if n not in st.session_state.lineup.values()]
    with st.form("add_form", clear_on_submit=True):
        pos = st.selectbox("Position", available_positions)
        player = st.selectbox("Player", available_players)
        if st.form_submit_button("Add to Lineup", type="primary"):
            st.session_state.lineup[pos] = player
            save_lineup(st.session_state.lineup, session_key)
            st.success(f"Added {player} at {pos}")

    st.subheader("Current Lineup")
    lineup_df = pd.DataFrame.from_dict(st.session_state.lineup, orient='index', columns=['Player'])
    st.table(lineup_df)

    if st.button("Visualize on Pitch", type="primary"):
        fig = draw_lineup(st.session_state.lineup)
        if fig:
            st.pyplot(fig)

    if st.button("Clear Lineup", type="secondary"):
        st.session_state.lineup = {}
        save_lineup({}, session_key)
        st.success("Lineup cleared.")

if __name__ == '__main__':
    show_lineup_planner()