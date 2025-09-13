"""Tiny navigation helper for ScoutLens pages."""

import streamlit as st


def go(page: str) -> None:
    """Switch to the given page by updating session state."""
    st.session_state["current_page"] = page


__all__ = ["go"]

