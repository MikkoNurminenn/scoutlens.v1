from pathlib import Path

import streamlit as st


def use_theme() -> None:
    """Inject global ScoutLens theme CSS."""
    css_path = Path(__file__).with_name("theme.css")
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


__all__ = ["use_theme"]

