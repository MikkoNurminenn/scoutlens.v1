"""Data export page.

Provides a simple CSV export of reports joined with player name and club. The
CSV is generated in-memory and offered as a download button. No local files are
written and Supabase remains the source of truth.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError
from app.ui import bootstrap_sidebar_auto_collapse

from app.supabase_client import get_client
from app.db_tables import REPORTS


bootstrap_sidebar_auto_collapse()


def _fetch_export_rows():
    client = get_client()
    try:
        res = (
            client.table(REPORTS)
            .select("*,player:player_id(name,current_club)")
            .execute()
        )
        return res.data or []
    except APIError as e:
        st.error("Failed to fetch reports for export from Supabase.")
        st.exception(e)
        return []


def show_export_page() -> None:
    st.markdown("## ⬇️ Export")

    rows = _fetch_export_rows()
    if not rows:
        st.caption("No reports available.")
        return

    df = pd.DataFrame(rows)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        csv,
        file_name="reports.csv",
        mime="text/csv",
        key="export__download",
    )

