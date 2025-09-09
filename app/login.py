from __future__ import annotations
import streamlit as st
from app.utils.assets import get_asset_path, set_page_bg


def login() -> None:
    """Simple username/password gate using Streamlit session_state."""
    if st.session_state.get("authenticated"):
        return

    set_page_bg(get_asset_path("login_bg.png"))

    st.markdown(
        """
        <style>
        .login-card {
            max-width: 420px; margin: 10vh auto; padding: 24px 22px;
            background: rgba(15, 23, 42, 0.55); backdrop-filter: blur(6px);
            border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.header("ScoutLens", anchor=False)

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
