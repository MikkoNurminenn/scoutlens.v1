import streamlit as st
from app.supabase_client import get_client


def safe_get(p: dict, key: str, default: str = "—") -> str:
    """Safely get a value from ``p`` with fallback ``default``."""
    return p.get(key, default)


def show_player_inspect() -> None:
    """Render the Inspect Player page."""
    st.title("🔍 Inspect Player")
    sb = get_client()
    try:
        res = sb.table("players").select("id,name").order("name").execute()
        players = res.data or []
    except Exception as e:
        st.error(f"Failed to load players: {e}")
        return

    if not players:
        st.info("No players available.")
        return

    options = {p["name"]: p["id"] for p in players}
    selected_name = st.selectbox("Select a player", list(options.keys()))
    player_id = options[selected_name]

    show_inspect_player(player_id)


def show_inspect_player(player_id: str) -> None:
    sb = get_client()
    try:
        res = sb.table("players").select(
            "id,name,position,nationality,current_club,preferred_foot,transfermarkt_url,date_of_birth"
        ).eq("id", player_id).execute()

        if not res.data:
            st.error("Player not found.")
            return

        player = res.data[0]

        st.subheader(safe_get(player, "name"))
        st.markdown(f"**Position:** {safe_get(player, 'position')}")
        st.markdown(f"**Nationality:** {safe_get(player, 'nationality')}")
        st.markdown(f"**Current Club:** {safe_get(player, 'current_club')}")
        st.markdown(f"**Preferred Foot:** {safe_get(player, 'preferred_foot')}")
        st.markdown(f"**Date of Birth:** {safe_get(player, 'date_of_birth')}")
        if player.get("transfermarkt_url"):
            st.markdown(f"[Transfermarkt Profile]({player['transfermarkt_url']})")

    except Exception as e:
        st.error(f"Failed to load player details: {e}")
