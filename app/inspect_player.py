import streamlit as st
from postgrest.exceptions import APIError
from app.services.players import get_player, list_reports_by_player


def show_inspect_player():
    st.header("🔎 Inspect Player")

    q = st.query_params
    player_id = q.get("player_id", [None])[0]

    if not player_id:
        st.info("Pick a player to inspect.")
        return

    try:
        p = get_player(player_id)
    except APIError as e:
        st.error(f"Failed to load player: {e}")
        return

    col1, col2 = st.columns([1, 2], gap="large")

    with col1:
        st.subheader(p["name"])
        st.caption(
            f"{p.get('position','—')} • {p.get('nationality','—')} • {p.get('preferred_foot','—')}"
        )
        st.text(f"Current club: {p.get('current_club','—')}")
        if p.get("transfermarkt_url"):
            st.link_button("Transfermarkt profile", p["transfermarkt_url"])
        st.divider()
        if st.button("📝 New report for this player", use_container_width=True):
            st.query_params.update({"page": "Reports", "player_id": p["id"]})
            st.rerun()

    with col2:
        st.subheader("Reports")
        try:
            reps = list_reports_by_player(player_id)
        except APIError as e:
            st.error(f"Failed to load reports: {e}")
            reps = []

        if not reps:
            st.info("No reports for this player yet.")
        else:
            import pandas as pd

            df = pd.DataFrame(
                reps,
                columns=[
                    "report_date",
                    "competition",
                    "opponent",
                    "location",
                    "position_played",
                    "minutes",
                    "rating",
                    "scout_name",
                    "notes",
                ],
            )
            df["notes"] = df["notes"].fillna("").str.slice(0, 120).mask(
                df["notes"].str.len() > 120, lambda s: s + "…"
            )
            st.dataframe(df, use_container_width=True, hide_index=True)

            with st.expander("Open report actions"):
                for r in reps:
                    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
                    c1.write(
                        f"**{r['report_date']}** {r.get('competition','—')} vs {r.get('opponent','—')}"
                    )
                    c2.write(f"Rating: **{r.get('rating','—')}**")
                    if c3.button("View", key=f"view_{r['id']}"):
                        st.query_params.update(
                            {"page": "Reports", "report_id": r["id"], "mode": "view"}
                        )
                        st.rerun()
                    if c4.button("Edit", key=f"edit_{r['id']}"):
                        st.query_params.update(
                            {"page": "Reports", "report_id": r["id"], "mode": "edit"}
                        )
                        st.rerun()
