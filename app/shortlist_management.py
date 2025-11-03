"""Shortlist management page allowing deletion of shortlists."""

from __future__ import annotations

import streamlit as st
from postgrest.exceptions import APIError

try:
    from app.ui import bootstrap_sidebar_auto_collapse
except ImportError:  # pragma: no cover - compatibility shim for legacy packages
    from app.ui.sidebar import bootstrap_sidebar_auto_collapse
from app.supabase_client import get_client
from app.shortlists_page import list_shortlists, list_shortlist_items


bootstrap_sidebar_auto_collapse()


def show_shortlist_management_page() -> None:
    st.title("🗑️ Manage Shortlists")

    auth = st.session_state.get("auth", {})
    if not auth.get("authenticated"):
        st.info("Sign in to delete shortlists.")
        return

    try:
        shortlists = list_shortlists()
    except APIError as e:  # pragma: no cover - UI error handling
        st.error(f"Failed to load shortlists: {e}")
        return

    if not shortlists:
        st.info("No shortlists available.")
        return

    label_by_id = {s["id"]: s["name"] for s in shortlists}
    selected_ids = st.multiselect(
        "Shortlists to delete",
        options=list(label_by_id.keys()),
        format_func=lambda x: label_by_id[x],
        key="shortlist_mgmt__ids",
    )

    sb = get_client()

    if st.button("Delete selected", type="secondary", disabled=not selected_ids):
        try:
            sb.table("shortlist_items").delete().in_("shortlist_id", selected_ids).execute()
            sb.table("shortlists").delete().in_("id", selected_ids).execute()
            list_shortlists.clear()
            list_shortlist_items.clear()
            st.success("Deleted selected shortlists.")
            st.rerun()
        except APIError as e:  # pragma: no cover - UI error handling
            st.error(f"Failed to delete shortlists: {e}")


__all__ = ["show_shortlist_management_page"]
