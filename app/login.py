import streamlit as st


def login():
    """Simple username/password gate using Streamlit session_state."""
    if st.session_state.get("authenticated"):
        return

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "Santeri" and password == "Volotinen":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()
