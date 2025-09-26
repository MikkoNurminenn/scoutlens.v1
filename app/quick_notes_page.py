"""Streamlit page for managing player quick notes."""
from __future__ import annotations

from typing import Dict, List, Optional

import streamlit as st
from postgrest.exceptions import APIError

from app.supabase_client import get_client
from app.services.quick_notes import (
    add_quick_note,
    delete_quick_note,
    list_quick_notes,
)

PAGE_KEY = "quick_notes__"


def _sb():
    return get_client()


def _search_players(query: str, limit: int = 20) -> List[Dict]:
    client = _sb()
    q = (
        client.table("players")
        .select("id,name,current_club,position,nationality")
        .order("name")
        .limit(limit)
    )
    query = (query or "").strip()
    if query:
        q = q.ilike("name", f"%{query}%")
    try:
        data = q.execute().data
        return data or []
    except APIError as exc:  # pragma: no cover - network interaction
        st.error(f"Failed to search players: {exc}")
        return []


def _create_player_minimal(
    name: str,
    position: Optional[str] = None,
    current_club: Optional[str] = None,
    nationality: Optional[str] = None,
    preferred_foot: Optional[str] = None,
) -> Optional[str]:
    client = _sb()
    payload: Dict[str, Optional[str]] = {
        "name": name.strip(),
        "position": (position or "").strip() or None,
        "current_club": (current_club or "").strip() or None,
        "nationality": (nationality or "").strip() or None,
        "preferred_foot": (preferred_foot or "").strip() or None,
    }
    try:
        rows = client.table("players").insert(payload).execute().data or []
        return rows[0]["id"] if rows else None
    except APIError as exc:  # pragma: no cover - network interaction
        st.error(f"Failed to create player: {exc}")
        return None


def _format_timestamp(ts: Optional[str]) -> str:
    if not ts:
        return "—"
    clean = ts.replace("T", " ")
    clean = clean.split("+")[0]
    return clean[:16]


def show_quick_notes_page() -> None:
    st.title("📝 Notes")

    sel_id_key = PAGE_KEY + "player_id"
    sel_label_key = PAGE_KEY + "player_label"
    pending_search_key = PAGE_KEY + "pending_search"
    st.session_state.setdefault(sel_id_key, None)
    st.session_state.setdefault(sel_label_key, None)
    st.session_state.setdefault(pending_search_key, None)

    st.subheader("Player")
    col_search, col_add = st.columns([3, 1])

    with col_search:
        pending_search = st.session_state.get(pending_search_key)
        if pending_search:
            st.session_state[PAGE_KEY + "search"] = pending_search
            st.session_state[pending_search_key] = None
        query = st.text_input(
            "Search by name",
            key=PAGE_KEY + "search",
            placeholder="Type player name…",
            autocomplete="off",
        )
        results = _search_players(query)
        labels = [f"{p['name']} ({p.get('current_club') or '—'})" for p in results]
        id_by_label = {label: player["id"] for label, player in zip(labels, results)}

        default_label = st.session_state.get(sel_label_key)
        placeholder_label = "— Select a player —"
        options: List[str] = [placeholder_label] + labels
        if default_label and default_label in labels:
            default_index = options.index(default_label)
        else:
            default_index = 0

        selected_option = st.selectbox(
            "Results",
            options,
            index=default_index,
            key=PAGE_KEY + "results",
        )
        if selected_option and selected_option != placeholder_label:
            st.session_state[sel_id_key] = id_by_label[selected_option]
            st.session_state[sel_label_key] = selected_option

    with col_add:
        with st.popover("＋ New Player"):
            with st.form(PAGE_KEY + "add_player_form", clear_on_submit=True):
                name = st.text_input("Name*", value="", autocomplete="off")
                colp = st.columns(2)
                position = colp[0].text_input("Position", value="", autocomplete="off")
                current_club = colp[1].text_input(
                    "Current club", value="", autocomplete="off"
                )
                coln = st.columns(2)
                nationality = coln[0].text_input("Nationality", value="", autocomplete="off")
                preferred_foot = coln[1].selectbox(
                    "Preferred foot",
                    ["", "Right", "Left", "Both"],
                )
                if st.form_submit_button("Create"):
                    if not name.strip():
                        st.warning("Name is required")
                    else:
                        new_id = _create_player_minimal(
                            name,
                            position,
                            current_club,
                            nationality,
                            preferred_foot,
                        )
                        if new_id:
                            st.toast(f"Player '{name}' created", icon="✅")
                            st.session_state[sel_id_key] = new_id
                            st.session_state[sel_label_key] = (
                                f"{name} ({current_club or '—'})"
                            )
                            st.session_state[pending_search_key] = name
                            st.rerun()

    player_id = st.session_state.get(sel_id_key)
    if not player_id:
        st.info(
            "Search and select a player, or create a new one to start taking notes."
        )
        return

    st.divider()
    st.subheader("Quick Notes")

    with st.form(PAGE_KEY + f"add_note_form_{player_id}", clear_on_submit=True):
        note_text = st.text_area(
            "Add a quick note",
            height=90,
            placeholder="Short observation…",
        )
        submitted = st.form_submit_button("Save Note")
        if submitted and note_text.strip():
            if add_quick_note(player_id, note_text):
                st.toast("Note saved", icon="✅")
                st.rerun()
        elif submitted:
            st.warning("Note is empty.")

    notes = list_quick_notes(player_id)

    if not notes:
        st.caption("No notes yet for this player.")
        return

    for note in notes:
        container = st.container()
        with container:
            col_content, col_actions = st.columns([9, 1])
            with col_content:
                st.markdown(note.get("content", ""))
                st.caption(
                    "Created: "
                    + _format_timestamp(note.get("created_at"))
                    + "  •  Updated: "
                    + _format_timestamp(note.get("updated_at"))
                )
            with col_actions:
                if st.button(
                    "🗑️ Delete",
                    key=PAGE_KEY + f"del_{note.get('id')}",
                ):
                    if delete_quick_note(str(note.get("id"))):
                        st.toast("Note deleted", icon="🗑️")
                        st.rerun()
