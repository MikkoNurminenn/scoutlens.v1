import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from pathlib import Path

from app_paths import file_path, DATA_DIR
from data_utils import list_teams, load_master

# ---------- JSON-polut ----------
PLAYERS_FP    = file_path("players.json")
SHORTLISTS_FP = file_path("shortlists.json")

# ---------- apurit ----------
def _load_json(fp: Path, default):
    try:
        if Path(fp).exists():
            return json.loads(Path(fp).read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def list_shortlists_json():
    return sorted(_load_json(SHORTLISTS_FP, {}).keys())

def get_shortlist_members_json(name: str):
    sl = _load_json(SHORTLISTS_FP, {})
    return [str(x) for x in sl.get(name, [])]

def get_all_players_map_id_to_name():
    """Palauttaa dictin: {player_id(str): name(str)} players.jsonista."""
    players = _load_json(PLAYERS_FP, [])
    out = {}
    for p in players:
        pid = str(p.get("id") or p.get("PlayerID") or "")
        nm = p.get("name") or p.get("Name") or ""
        if pid and nm:
            out[pid] = nm
    return out

# ---------- värit ----------
OPTIMAL_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
    "#bcbd22", "#17becf",
]

# ---------- tyyli ----------
def tag_style():
    st.markdown(
        """
        <style>
        .tag-button { background-color: #ff4d4d; color: white; border-radius: 1rem;
            padding: 0.4rem 0.8rem; margin: 0.2rem; display: inline-block;
            font-weight: bold; font-size: 0.9rem; }
        </style>
        """, unsafe_allow_html=True
    )

def format_label(name: str) -> str:
    parts = (name or "").split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {parts[-1]}"
    return name or ""

# ---------- päänäkymä ----------
def show_visual_analytics():
    st.title("📊 Visual Analytics")
    tag_style()

    view = st.selectbox("View", ["Team Analytics", "Player Analytics"])
    scope = st.selectbox("Stats Source", ["Master", "Seasonal"], help="Master = overall; Seasonal = per season")

    def load_base():
        source = st.radio("Data Source", ["Team", "Shortlist"], horizontal=True)

        if source == "Team":
            teams = list_teams()
            if not teams:
                st.warning("No teams available.")
                return None
            team = st.selectbox("Team", teams)
            if not team:
                return None
            df = load_master(team)
            if df is None or df.empty:
                st.info("No data for selected team.")
                return None
            df = df.loc[:, ~df.columns.duplicated()]  # poista tuplat
            # Varmista CurrentClub (joissain mestreissä sarake voi olla 'Team')
            if "CurrentClub" not in df.columns and "Team" in df.columns:
                df["CurrentClub"] = df["Team"]
            return df

        # Shortlist mode (JSON)
        sl_names = list_shortlists_json()
        if not sl_names:
            st.info("No shortlists available.")
            return None
        sel = st.selectbox("Shortlist", sl_names)
        if not sel:
            return None
        pids = set(get_shortlist_members_json(sel))
        if not pids:
            st.info("Selected shortlist is empty.")
            return None

        # id -> name map players.jsonista
        id_to_name = get_all_players_map_id_to_name()
        names = [id_to_name.get(str(pid)) for pid in pids if str(pid) in id_to_name and id_to_name.get(str(pid))]
        if not names:
            st.info("No matching players for this shortlist in players.json.")
            return None

        # Kerää mastereista ne rivit, joiden Name osuu shortlist-nimiin
        filtered = []
        for team in list_teams():
            df_t = load_master(team)
            if df_t is None or df_t.empty:
                continue
            df_t = df_t.loc[:, ~df_t.columns.duplicated()]
            subset = df_t[df_t.get('Name', pd.Series(dtype=str)).isin(names)]
            if not subset.empty:
                filtered.append(subset.reset_index(drop=True))

        if not filtered:
            st.info("No data for selected players.")
            return None

        combined = pd.concat(filtered, ignore_index=True)
        combined = combined.loc[:, ~combined.columns.duplicated()]
        if "CurrentClub" not in combined.columns and "Team" in combined.columns:
            combined["CurrentClub"] = combined["Team"]
        return combined.drop_duplicates('Name')

    df = load_base()
    if df is None:
        return

    # Seasonal vs Master käsittely
    if scope == "Seasonal":
        if 'SeasonalStats' not in df.columns:
            st.info("No seasonal stats present.")
            return
        records = []
        for _, row in df.iterrows():
            stats = row['SeasonalStats']
            if isinstance(stats, str):
                try:
                    stats = json.loads(stats)
                except Exception:
                    continue
            if isinstance(stats, list):
                for s in stats:
                    if isinstance(s, dict):
                        rec = {'Name': row.get('Name', ''), 'CurrentClub': row.get('CurrentClub', row.get('Team', ''))}
                        rec.update(s)
                        records.append(rec)
        sd = pd.DataFrame(records)
        if sd.empty:
            st.info("Empty seasonal data.")
            return
        if 'Season' not in sd.columns or sd['Season'].isnull().all():
            st.info("Season column missing/empty in seasonal data.")
            return
        season = st.selectbox("Season", sorted(sd['Season'].dropna().unique()))
        df_scope = sd[sd['Season'] == season]
    else:
        df_scope = df.copy()

    # Varmista peruskentät
    if "Name" not in df_scope.columns:
        st.warning("Dataset missing 'Name' column.")
        return
    if "CurrentClub" not in df_scope.columns and "Team" in df_scope.columns:
        df_scope["CurrentClub"] = df_scope["Team"]

    df_scope['Label'] = df_scope['Name'].apply(format_label)

    # Numeriset sarakkeet valintoihin
    num_cols = df_scope.select_dtypes(include='number').columns.tolist()
    if not num_cols:
        st.info("No numeric columns to visualize.")
        return

    if view == "Team Analytics":
        st.subheader(f"{view} ({scope})")
        x = st.selectbox("X-axis", num_cols)
        y = st.selectbox("Y-axis", [c for c in num_cols if c != x] or num_cols)
        ptype = st.selectbox("Plot Type", ["Scatter", "Bar", "Box", "Line"])
        show_labels = st.checkbox("Show Labels", False)

        st.markdown("**Select Players to Display:**")
        all_labels = df_scope['Label'].tolist()
        selected = st.multiselect("Players", options=all_labels, default=all_labels)
        name_map = dict(zip(df_scope['Label'], df_scope['Name']))
        to_disp = [name_map[l] for l in selected if l in name_map]
        plot_df = df_scope[df_scope['Name'].isin(to_disp)]

        plot_args = dict(x=x, y=y, color='CurrentClub',
                         color_discrete_sequence=OPTIMAL_COLORS, hover_name='Name')
        if show_labels:
            plot_args['text'] = 'Label'

        if ptype == "Scatter":
            fig = px.scatter(plot_df, **plot_args)
        elif ptype == "Bar":
            fig = px.bar(plot_df, **plot_args)
        elif ptype == "Box":
            fig = px.box(plot_df, **plot_args)
        else:
            fig = px.line(plot_df, **plot_args)

        if ptype == "Scatter" and not show_labels:
            fig.update_traces(text=None)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Players Displayed:**")
        disp_names = [format_label(n) for n in plot_df['Name']]
        st.write(", ".join(disp_names))

    else:
        st.subheader(f"{view} ({scope})")
        players = df_scope['Name'].dropna().unique().tolist()
        attrs = st.multiselect("Attributes", num_cols, default=num_cols[:3])
        sels = st.multiselect("Players", players, default=players[:2])
        ctype = st.selectbox("Chart Type", ["Radar", "Bar", "Line"])
        if not attrs or not sels:
            st.warning("Select players and attributes.")
            return
        sub = df_scope[df_scope['Name'].isin(sels)]

        if ctype == "Radar":
            fig = go.Figure()
            for i, p in enumerate(sels):
                row = sub[sub['Name'] == p]
                if not row.empty:
                    v = row[attrs].iloc[0].tolist()
                    v += v[:1]
                    theta = attrs + [attrs[0]]
                    fig.add_trace(go.Scatterpolar(
                        r=v, theta=theta, fill='toself', name=p,
                        line=dict(color=OPTIMAL_COLORS[i % len(OPTIMAL_COLORS)])
                    ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True)), template='plotly_dark')
            st.plotly_chart(fig, use_container_width=True)

        elif ctype == "Bar":
            long = sub.melt(id_vars=['Name'], value_vars=attrs, var_name='Attribute', value_name='Value')
            fig = px.bar(long, x='Name', y='Value', color='Attribute',
                         barmode='group', color_discrete_sequence=OPTIMAL_COLORS)
            st.plotly_chart(fig, use_container_width=True)

        else:  # Line
            long = sub.melt(id_vars=['Name'], value_vars=attrs, var_name='Attribute', value_name='Value')
            fig = px.line(long, x='Attribute', y='Value', color='Name', markers=True,
                          color_discrete_sequence=OPTIMAL_COLORS)
            st.plotly_chart(fig, use_container_width=True)

if __name__ == '__main__':
    show_visual_analytics()
