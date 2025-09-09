from __future__ import annotations
import base64
from pathlib import Path
import streamlit as st
from app.paths import assets_dir


def _set_login_background() -> None:
    img_path: Path = assets_dir() / "login_bg.png"
    if not img_path.exists():
        return  # fail silently if image missing

    with img_path.open("rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: url("data:image/png;base64,{b64}") center center / cover no-repeat fixed;
        }}
        /* soft vignette for readability of form elements */
        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            background: radial-gradient(ellipse at 50% 40%, rgba(0,0,0,0.25), rgba(0,0,0,0.55) 70%);
            pointer-events: none;
            z-index: 0;
        }}
        /* bring content above overlay */
        .block-container {{ z-index: 1; position: relative; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def login() -> None:
    """Simple username/password gate using Streamlit session_state."""
    if st.session_state.get("authenticated"):
        return

    _set_login_background()
    st.title("ScoutLens")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "Santeri" and password == "Volotinen":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()
