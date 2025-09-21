"""Streamlit multipage entry for the Notes view."""
from __future__ import annotations

import streamlit as st

from app.quick_notes_page import show_quick_notes_page


st.set_page_config(page_title="Quick notes")


def main() -> None:
    show_quick_notes_page()


if __name__ == "__main__":  # pragma: no cover
    main()
