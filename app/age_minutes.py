from __future__ import annotations

import pandas as pd
import streamlit as st

from app.data_utils import list_teams, load_data, save_data, validate_player_input
from app.metrics import add_minutes_per_match, calculate_summary
from app.visuals import create_minutes_age_plot


def show_age_minutes() -> None:
    controls_col, content_col = st.columns([1, 3], gap="large")

    with controls_col:
        st.markdown("### ⚽ Team Selection")
        existing_teams = list_teams()
        team_options = existing_teams + ["Create new team..."]
        selected_team = st.selectbox(
            "Select Team",
            options=team_options,
            key="age_minutes_team_select",
        )

        if selected_team == "Create new team...":
            new_team = st.text_input("New team name", key="age_minutes_new_team")
            if st.button("Create Team", type="primary", key="age_minutes_create_team"):
                if new_team.strip():
                    selected_team = new_team.strip()
                    st.session_state["selected_team"] = selected_team
                    st.success(f"Team '{selected_team}' created!")
                else:
                    st.error("Team name cannot be empty")
        elif selected_team:
            st.session_state["selected_team"] = selected_team

        if "selected_team" not in st.session_state:
            st.warning("Please select or create a team to continue.")
            st.stop()

        team_name = st.session_state["selected_team"]
        df = load_data(team_name)
        df = add_minutes_per_match(df)

        st.markdown("### Add or Update Player")
        with st.form("player_form"):
            name = st.text_input("Name", key="age_minutes_player_name")
            age = st.number_input("Age", min_value=15, max_value=45, key="age_minutes_age")
            position = st.text_input("Position", key="age_minutes_position")
            nationality = st.text_input("Nationality", key="age_minutes_nationality")
            contract_start = st.date_input("Contract Start", key="age_minutes_contract_start")
            contract_end = st.date_input("Contract End", key="age_minutes_contract_end")
            loan = st.checkbox("On Loan", key="age_minutes_loan")
            minutes = st.number_input("Minutes Played", min_value=0, key="age_minutes_minutes")
            matches = st.number_input("Matches Played", min_value=0, key="age_minutes_matches")
            submitted = st.form_submit_button("Add / Update Player", type="primary")

            if submitted:
                is_valid, msg = validate_player_input(name, df)
                if is_valid:
                    df = df[df["Name"] != name]
                    new_row = pd.DataFrame(
                        [
                            {
                                "Name": name.title(),
                                "Age": age,
                                "Position": position,
                                "Nationality": nationality,
                                "ContractStart": contract_start,
                                "ContractEnd": contract_end,
                                "Loan": loan,
                                "Minutes": minutes,
                                "Matches": matches,
                            }
                        ]
                    )
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_data(df, team_name)
                    st.success(f"Player '{name}' added/updated!")
                else:
                    st.error(msg)

        df_sorted = df.sort_values("Name")
        st.markdown("### Remove Player")
        remove_name = st.selectbox(
            "Select player to remove",
            options=["-"] + df_sorted["Name"].tolist(),
            key="age_minutes_remove_name",
        )
        if st.button("Remove", type="secondary", key="age_minutes_remove") and remove_name != "-":
            df = df[df["Name"] != remove_name]
            save_data(df, team_name)
            st.success(f"Removed player: {remove_name}")

    with content_col:
        team_name = st.session_state.get("selected_team")
        if not team_name:
            st.info("Select a team to view metrics.")
            return

        st.subheader(f"📊 Summary for team: {team_name}")
        df = load_data(team_name)
        df = add_minutes_per_match(df)

        metrics = calculate_summary(df)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Average Age", metrics["avg_age"])
        col2.metric("Avg. Minutes", metrics["avg_minutes"])
        col3.metric("Total Matches", metrics["total_matches"])
        col4.metric("Minutes/Match", metrics["avg_minutes_per_match"])

        df = df.copy()
        df["ContractStart"] = pd.to_datetime(df["ContractStart"], errors="coerce")
        df["ContractEnd"] = pd.to_datetime(df["ContractEnd"], errors="coerce")
        fig = create_minutes_age_plot(df)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 View Raw Player Data"):
            st.dataframe(df.reset_index(drop=True))
