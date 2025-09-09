from __future__ import annotations
import streamlit as st
from app.ui.backgrounds import inject_login_background_css


def login() -> None:
    """Simple username/password gate using Streamlit session_state."""
    if st.session_state.get("authenticated"):
        return

    inject_login_background_css(st, "login_bg.png")

    st.markdown('<div class="scoutlens-login-card">', unsafe_allow_html=True)
    st.title("ScoutLens")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "Santeri" and password == "Volotinen":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()
