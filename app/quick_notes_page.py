# app/pages/quick_notes.py
"""
Streamlit page for managing player quick notes.

Requires:
- .streamlit/component.css  (global styles)
- app/supabase_client.get_client()
- app/services/quick_notes.{add_quick_note, delete_quick_note, list_quick_notes, update_quick_note}
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Dict, List, Optional, Union

import streamlit as st
from postgrest.exceptions import APIError

from app.supabase_client import get_client
from app.services.quick_notes import (
    add_quick_note,
    delete_quick_note,
    list_quick_notes,
    update_quick_note,
)
from app.ui.sidebar_toggle_patch import sl_fix_sidebar_toggle

PAGE_KEY = "quick_notes__"
THEME_CSS_PATH = Path(".streamlit") / "component.css"  # ← your filename

LOCAL_TZ = datetime.now().astimezone().tzinfo or timezone.utc
HIGHLIGHT_OPEN = "__SL_NOTE_MATCH_OPEN__"
HIGHLIGHT_CLOSE = "__SL_NOTE_MATCH_CLOSE__"


def _sb():
    return get_client()


def load_css() -> None:
    """
    Inject global CSS once per session.
    Why: Avoid duplicate <style> blocks and keep render lightweight.
    """
    flag = PAGE_KEY + "css_loaded"
    if st.session_state.get(flag):
        return
    try:
        css_text = THEME_CSS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        st.caption("⚠️ .streamlit/component.css not found; using default styles.")
        return
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)
    st.session_state[flag] = True


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


def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    ts = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _timestamp_labels(ts: Optional[Union[str, datetime]]) -> tuple[str, str]:
    dt: Optional[datetime]
    if isinstance(ts, datetime):
        dt = ts
    else:
        dt = _parse_timestamp(ts)
    if not dt:
        return ("—", "")
    local_dt = dt.astimezone(LOCAL_TZ)
    utc_dt = dt.astimezone(timezone.utc)
    local_name = local_dt.tzname() or str(local_dt.tzinfo or "")
    local_label = local_dt.strftime("%Y-%m-%d %H:%M")
    if local_name:
        local_label = f"{local_label} {local_name}"
    return (local_label, utc_dt.strftime("%Y-%m-%d %H:%M UTC"))


def _format_timestamp(ts: Optional[Union[str, datetime]]) -> str:
    local_label, utc_label = _timestamp_labels(ts)
    return f"{local_label} · {utc_label}" if utc_label else local_label


def _format_note_body(content: Optional[str], highlight: str) -> str:
    text = (content or "").strip()
    query = (highlight or "").strip()
    if query:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        text = pattern.sub(
            lambda match: f"{HIGHLIGHT_OPEN}{match.group(0)}{HIGHLIGHT_CLOSE}",
            text,
        )
    safe = escape(text)
    safe = safe.replace("\n", "<br>")
    if query:
        safe = safe.replace(
            HIGHLIGHT_OPEN,
            '<mark class="sl-note-highlight">',
        ).replace(HIGHLIGHT_CLOSE, "</mark>")
    return safe or '<span class="sl-note-empty">(empty note)</span>'


def _meta_block(title: str, local_label: str, utc_label: str) -> str:
    title_html = escape(title)
    local_html = escape(local_label) if local_label else "—"
    utc_html = escape(utc_label)
    utc_block = f'<span class="sl-note-meta-sub">{utc_html}</span>' if utc_label else ""
    return (
        f"<div class=\"sl-note-meta-block\">"
        f"<span class=\"sl-note-meta-label\">{title_html}</span>"
        f"<span class=\"sl-note-meta-value\">{local_html}</span>"
        f"{utc_block}"
        f"</div>"
    )


def _render_summary(notes: List[Dict]) -> None:
    if not notes:
        return
    latest_dt: Optional[datetime] = None
    for note in notes:
        candidate = _parse_timestamp(note.get("updated_at")) or _parse_timestamp(
            note.get("created_at")
        )
        if candidate and (latest_dt is None or candidate > latest_dt):
            latest_dt = candidate
    latest_label = _format_timestamp(latest_dt) if latest_dt else "—"
    st.markdown(
        """
        <div class="sl-note-summary">
          <div class="sl-stat-card">
            <span class="sl-stat-label">Notes saved</span>
            <span class="sl-stat-value">{count}</span>
          </div>
          <div class="sl-stat-card">
            <span class="sl-stat-label">Last updated</span>
            <span class="sl-stat-value">{latest}</span>
          </div>
        </div>
        """.format(count=len(notes), latest=escape(latest_label)),
        unsafe_allow_html=True,
    )


def show_quick_notes_page() -> None:
    load_css()
    st.title("📝 Notes")

    sel_id_key = PAGE_KEY + "player_id"
    sel_label_key = PAGE_KEY + "player_label"
    pending_search_key = PAGE_KEY + "pending_search"
    filter_key = PAGE_KEY + "note_filter"
    sort_key = PAGE_KEY + "note_sort"
    add_modal_key = PAGE_KEY + "add_player_modal_open"
    st.session_state.setdefault(sel_id_key, None)
    st.session_state.setdefault(sel_label_key, None)
    st.session_state.setdefault(pending_search_key, None)
    st.session_state.setdefault(filter_key, "")
    st.session_state.setdefault(sort_key, "Newest update")
    st.session_state.setdefault(add_modal_key, False)

    try:
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
            default_index = options.index(default_label) if default_label in labels else 0

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
            st.markdown('<div class="sl-add-player-cta">', unsafe_allow_html=True)
            if st.button(
                "＋ New Player",
                key=PAGE_KEY + "open_add_player",
                type="primary",
                use_container_width=True,
            ):
                st.session_state[add_modal_key] = True
            st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.get(add_modal_key):
                with st.container():
                    st.markdown(
                        '<div class="sl-add-player-panel"><div class="sl-form-variant">',
                        unsafe_allow_html=True,
                    )
                    with st.form(PAGE_KEY + "add_player_form", clear_on_submit=True):
                        name = st.text_input(
                            "Name*", value="", autocomplete="off", placeholder="Full name"
                        )
                        colp = st.columns(2)
                        position = colp[0].text_input(
                            "Position", value="", autocomplete="off", placeholder="e.g. CM"
                        )
                        current_club = colp[1].text_input(
                            "Current club", value="", autocomplete="off", placeholder="e.g. Ajax"
                        )
                        coln = st.columns(2)
                        nationality = coln[0].text_input(
                            "Nationality",
                            value="",
                            autocomplete="off",
                            placeholder="e.g. Finland",
                        )
                        preferred_foot = coln[1].selectbox(
                            "Preferred foot", ["", "Right", "Left", "Both"]
                        )

                        action_cols = st.columns([1, 1])
                        create_clicked = action_cols[0].form_submit_button(
                            "Create", type="primary"
                        )
                        cancel_clicked = action_cols[1].form_submit_button(
                            "Cancel", type="secondary"
                        )

                        if cancel_clicked:
                            st.session_state[add_modal_key] = False
                            st.rerun()

                        if create_clicked:
                            if not name.strip():
                                st.warning("Name is required")
                            else:
                                new_id = _create_player_minimal(
                                    name, position, current_club, nationality, preferred_foot
                                )
                                if new_id:
                                    st.toast(f"Player '{name}' created", icon="✅")
                                    st.session_state[sel_id_key] = new_id
                                    st.session_state[sel_label_key] = (
                                        f"{name} ({current_club or '—'})"
                                    )
                                    st.session_state[pending_search_key] = name
                                    st.session_state[add_modal_key] = False
                                    st.rerun()
                    st.markdown("</div></div>", unsafe_allow_html=True)

        player_id = st.session_state.get(sel_id_key)
        if not player_id:
            st.info("Search and select a player, or create a new one to start taking notes.")
            return

        st.divider()
        st.subheader("Quick Notes")

        with st.form(PAGE_KEY + f"add_note_form_{player_id}", clear_on_submit=True):
            note_text = st.text_area(
                "Add a quick note",
                height=110,
                placeholder="Short observation…",
            )
            submitted = st.form_submit_button("Save Note")
            if submitted:
                trimmed = note_text.strip()
                if trimmed:
                    if add_quick_note(player_id, trimmed):
                        st.toast("Note saved", icon="✅")
                        st.rerun()
                else:
                    st.warning("Note is empty.")

        notes = list_quick_notes(player_id)
        if not notes:
            st.caption("No notes yet for this player.")
            return

        _render_summary(notes)

        search_col, sort_col, reset_col = st.columns([3.2, 1.4, 0.8])
        with search_col:
            note_query = st.text_input(
                "Search notes",
                key=filter_key,
                placeholder="Keyword or phrase…",
                autocomplete="off",
            )
        with sort_col:
            st.selectbox(
                "Sort by",
                ["Newest update", "Oldest update"],
                key=sort_key,
            )
        with reset_col:
            if st.button(
                "Reset",
                key=PAGE_KEY + "note_reset",
                type="secondary",
                use_container_width=True,
            ):
                st.session_state[filter_key] = ""
                st.session_state[sort_key] = "Newest update"
                st.rerun()

        query = (note_query or "").strip()
        if query:
            lowered = query.lower()
            filtered_notes = [
                note
                for note in notes
                if lowered in (note.get("content") or "").lower()
            ]
        else:
            filtered_notes = list(notes)

        reverse = st.session_state.get(sort_key) == "Newest update"

        def _sort_key(note: Dict) -> datetime:
            return (
                _parse_timestamp(note.get("updated_at"))
                or _parse_timestamp(note.get("created_at"))
                or datetime.min.replace(tzinfo=timezone.utc)
            )

        filtered_notes.sort(key=_sort_key, reverse=reverse)

        total = len(notes)
        shown = len(filtered_notes)
        if query:
            st.caption(f"{shown} of {total} notes match the search.")
        else:
            st.caption(f"Showing all {total} notes.")

        if not filtered_notes:
            st.info("No notes matched the current search.")
            return

        for note in filtered_notes:
            note_id = str(note.get("id"))
            note_id_short = note_id[:8] if note_id else "—"
            content_html = _format_note_body(note.get("content"), query)
            created_local, created_utc = _timestamp_labels(note.get("created_at"))
            updated_local, updated_utc = _timestamp_labels(note.get("updated_at"))
            word_count = len([w for w in (note.get("content") or "").split() if w])
            header_meta = (
                f"{word_count} word{'s' if word_count != 1 else ''}" if word_count else "No content yet"
            )
            header_meta_html = escape(header_meta)
            st.markdown(
                """
                <div class="sl-note-card">
                  <div class="sl-note-card__header">
                    <span class="sl-note-pill">#{note_id}</span>
                    <span class="sl-note-header-meta">{meta}</span>
                  </div>
                  <div class="sl-note-card__body">{body}</div>
                  <div class="sl-note-card__meta">
                    {created_block}
                    {updated_block}
                  </div>
                </div>
                """.format(
                    note_id=escape(note_id_short),
                    meta=header_meta_html,
                    body=content_html,
                    created_block=_meta_block("Created", created_local, created_utc),
                    updated_block=_meta_block("Updated", updated_local, updated_utc),
                ),
                unsafe_allow_html=True,
            )

            action_cols = st.columns([5, 1.5, 1.5])
            with action_cols[1]:
                st.markdown('<div class="sl-note-card__actions">', unsafe_allow_html=True)
                with st.popover("✏️ Edit", key=PAGE_KEY + f"edit_{note_id}"):
                    st.markdown('<div class="sl-form-variant">', unsafe_allow_html=True)
                    with st.form(PAGE_KEY + f"edit_form_{note_id}"):
                        updated_text = st.text_area(
                            "Edit note",
                            value=note.get("content", ""),
                            height=120,
                        )
                        submitted_edit = st.form_submit_button("Save changes")
                        if submitted_edit:
                            trimmed_edit = updated_text.strip()
                            current_value = (note.get("content") or "").strip()
                            if not trimmed_edit:
                                st.warning("Note cannot be empty.")
                            elif trimmed_edit == current_value:
                                st.info("No changes to save.")
                            elif update_quick_note(note_id, trimmed_edit):
                                st.toast("Note updated", icon="✏️")
                                st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with action_cols[2]:
                st.markdown('<div class="sl-note-card__actions">', unsafe_allow_html=True)
                if st.button(
                    "🗑️ Delete",
                    key=PAGE_KEY + f"del_{note_id}",
                    type="secondary",
                    use_container_width=True,
                ):
                    if delete_quick_note(note_id):
                        st.toast("Note deleted", icon="🗑️")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    finally:
        sl_fix_sidebar_toggle()
