from pathlib import Path
import streamlit as st


def use_theme(page_title: str = "ScoutLens") -> None:
    """Apply page config and inject global CSS theme once per run."""
    st.set_page_config(page_title=page_title, layout="wide")
    css_path = Path(__file__).with_name("theme.css")
    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )

