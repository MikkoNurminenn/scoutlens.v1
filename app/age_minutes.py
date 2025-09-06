import streamlit as st
import pandas as pd
from data_utils import load_data, save_data, validate_player_input, list_teams
from metrics import add_minutes_per_match, calculate_summary
from visuals import create_minutes_age_plot

def show_age_minutes():
    st.sidebar.header("⚽ Team Selection")
    existing_teams = list_teams()
    selected_team = st.sidebar.selectbox("Select Team", options=existing_teams + ["Create new team..."])

    if selected_team == "Create new team...":
        new_team = st.sidebar.text_input("New team name")
        if st.sidebar.button("Create Team"):
            if new_team.strip():
                selected_team = new_team.strip()
                st.session_state["selected_team"] = selected_team
                st.sidebar.success(f"Team '{selected_team}' created!")
            else:
                st.sidebar.error("Team name cannot be empty")
    else:
        st.session_state["selected_team"] = selected_team

    if "selected_team" not in st.session_state:
        st.warning("Please select or create a team to continue.")
        st.stop()

    team_name = st.session_state["selected_team"]
    df = load_data(team_name)
    df = add_minutes_per_match(df)

    st.sidebar.header("Add or Update Player")
    with st.sidebar.form("player_form"):
        name = st.text_input("Name")
        age = st.number_input("Age", min_value=15, max_value=45)
        position = st.text_input("Position")
        nationality = st.text_input("Nationality")
        contract_start = st.date_input("Contract Start")
        contract_end = st.date_input("Contract End")
        loan = st.checkbox("On Loan")
        minutes = st.number_input("Minutes Played", min_value=0)
        matches = st.number_input("Matches Played", min_value=0)
        submitted = st.form_submit_button("Add / Update Player")

        if submitted:
            is_valid, msg = validate_player_input(name, df)
            if is_valid:
                df = df[df["Name"] != name]
                new_row = pd.DataFrame([{ 
                    "Name": name.title(),
                    "Age": age,
                    "Position": position,
                    "Nationality": nationality,
                    "ContractStart": contract_start,
                    "ContractEnd": contract_end,
                    "Loan": loan,
                    "Minutes": minutes,
                    "Matches": matches
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df, team_name)
                st.success(f"Player '{name}' added/updated!")
            else:
                st.error(msg)

    df_sorted = df.sort_values("Name")
    st.sidebar.header("Remove Player")
    remove_name = st.sidebar.selectbox("Select player to remove", options=["-"] + df_sorted["Name"].tolist())
    if st.sidebar.button("Remove") and remove_name != "-":
        df = df[df["Name"] != remove_name]
        save_data(df, team_name)
        st.sidebar.success(f"Removed player: {remove_name}")

    st.subheader(f"📊 Summary for team: {team_name}")
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
