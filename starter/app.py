"""Streamlit demo app used in the sidebar button debugging kata."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Streamlit Sidebar Buttons",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] .stButton button {
        border-radius: 0.75rem;
        border: 1px solid rgba(255, 255, 255, 0.25);
        background: linear-gradient(120deg, #262730, #464775);
        color: #f6f6f8;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    section[data-testid="stSidebar"] .stButton button:hover,
    section[data-testid="stSidebar"] .stButton button:focus-visible {
        transform: translateY(-1px);
        box-shadow: 0 0.5rem 1.5rem rgba(70, 71, 117, 0.45);
        outline: none;
    }

    section[data-testid="stSidebar"] .stButton button:active {
        transform: translateY(0);
        box-shadow: inset 0 0 0.75rem rgba(0, 0, 0, 0.35);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Sidebar Button Showcase")
st.write(
    "This mini app demonstrates a resilient sidebar button setup. "
    "The sidebar stays visible and the actions remain interactive even "
    "when custom styling is applied."
)

with st.sidebar:
    st.header("Quick actions")
    st.caption("Trigger frequently used tasks from here.")

    if st.button("Refresh data", key="refresh", use_container_width=True):
        st.toast("Data refresh triggered!", icon="♻️")

    if st.button("Run analysis", key="analyze", type="primary", use_container_width=True):
        st.toast("Analysis started.", icon="🧠")

    st.divider()
    st.write("Buttons stay visible thanks to careful CSS scoping.")

st.success("Sidebar is ready. Buttons are rendered and styled without hiding them.")
