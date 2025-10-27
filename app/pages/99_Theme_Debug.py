from __future__ import annotations

import streamlit as st

from app.ui import init  # noqa: F401  # ensure global UI bootstrap runs

from app.theme.codex_theme import DATAVIZ_10, DATAVIZ_OKABE_ITO, PALETTE, apply_theme

st.set_page_config(page_title="Codex Theme Debug", page_icon="🎨", layout="wide")
apply_theme()
st.title("Theme Debug • Codex")

st.subheader("UI tokens")
cols = st.columns(4)
for i, (k, v) in enumerate(PALETTE.items()):
    with cols[i % 4]:
        st.markdown(
            f"""
            <div style="border:1px solid #333;border-radius:8px;overflow:hidden;margin-bottom:8px">
              <div style="height:48px;background:{v}"></div>
              <div style="padding:6px 8px;font-size:12px">{k}<br><code>{v}</code></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.subheader("Dataviz • Okabe–Ito")
cols = st.columns(len(DATAVIZ_OKABE_ITO))
for i, color in enumerate(DATAVIZ_OKABE_ITO):
    with cols[i]:
        st.markdown(
            f"<div style='height:48px;background:{color}'></div><code>{color}</code>",
            unsafe_allow_html=True,
        )

st.subheader("Dataviz • 10-color")
cols = st.columns(len(DATAVIZ_10))
for i, color in enumerate(DATAVIZ_10):
    with cols[i]:
        st.markdown(
            f"<div style='height:48px;background:{color}'></div><code>{color}</code>",
            unsafe_allow_html=True,
        )
