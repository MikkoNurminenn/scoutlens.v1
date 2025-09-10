"""Tiny navigation helper for ScoutLens pages."""

import streamlit as st


def go(page: str) -> None:
    """Switch to the given page and trigger a rerun."""
    st.session_state["current_page"] = page
    st.rerun()


__all__ = ["go"]

