from pathlib import Path
import streamlit as st


def use_theme() -> None:
    """Inject global CSS theme once per run."""
    css_path = Path(__file__).with_name("theme.css")
    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )

