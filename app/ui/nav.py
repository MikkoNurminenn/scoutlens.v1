import streamlit as st


def go(page: str) -> None:
    """Switch to given page and trigger a single rerun."""
    st.session_state["current_page"] = page
    try:
        st.query_params = {"p": page}
    except Exception:
        pass
    st.rerun()


__all__ = ["go"]
