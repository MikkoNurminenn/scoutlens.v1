from postgrest.exceptions import APIError
import streamlit as st
from app.supabase_client import get_client


def players_delete_panel() -> None:
    st.subheader("Delete players")
    st.caption("This action permanently removes players and related data.")

    sb = get_client()

    try:
        resp = sb.table("players").select("id,name,current_club").order("name").execute()
        rows = resp.data or []
    except APIError as e:
        st.error(f"Failed to load players: {e}")
        return

    if not rows:
        st.info("No players found.")
        return

    labels = [f'{r["name"]} ({r.get("current_club") or "—"})' for r in rows]
    id_by_label = {lbl: r["id"] for lbl, r in zip(labels, rows)}

    selected_labels = st.multiselect("Players to delete", options=labels)
    selected_ids = [id_by_label[lbl] for lbl in selected_labels]

    confirm = st.checkbox(
        "Yes, permanently delete selected player(s) and all related data"
    )
    disabled = not (selected_ids and confirm)

    if st.button("🗑️ Delete selected", type="primary", disabled=disabled):
        try:
            sb.rpc("delete_players_cascade", {"p_ids": selected_ids}).execute()
            st.success(f"Deleted {len(selected_ids)} player(s).")
            print(f"Deleted {len(selected_ids)} player(s)")
            st.rerun()
        except APIError as e:
            st.error(f"Delete failed: {getattr(e, 'message', str(e))}")


__all__ = ["players_delete_panel"]
