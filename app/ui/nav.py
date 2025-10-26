"""Tiny navigation helper for ScoutLens pages."""

import streamlit as st


def go(page: str) -> None:
    """Switch to the given page by updating session state and forcing a rerun."""
    st.session_state["sidebar_nav"] = page
    st.session_state["current_page"] = page
    # why: without an explicit rerun Streamlit finishes the current render with the
    # previous page value, causing the sidebar to look "stuck" when users click
    # navigation items quickly.
    rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun:
        rerun()


__all__ = ["go"]

