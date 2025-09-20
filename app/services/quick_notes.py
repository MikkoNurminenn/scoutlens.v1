"""Helpers for interacting with quick notes."""
from __future__ import annotations

from typing import Dict, List

import streamlit as st
from postgrest.exceptions import APIError

from app.supabase_client import get_client


__all__ = [
    "list_quick_notes",
    "add_quick_note",
    "delete_quick_note",
    "fetch_note_counts_by_player",
]


def list_quick_notes(player_id: str) -> List[Dict]:
    """Return quick notes for a player ordered by newest first."""
    if not player_id:
        return []
    sb = get_client()
    try:
        resp = (
            sb.table("quick_notes")
            .select("id,content,created_at,updated_at")
            .eq("player_id", player_id)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []
    except APIError as exc:  # pragma: no cover - network interaction
        st.error(f"Failed to load notes: {exc}")
        return []


def add_quick_note(player_id: str, content: str) -> bool:
    """Insert a quick note for a player."""
    if not player_id:
        st.warning("Select a player before adding notes.")
        return False
    if not content or not content.strip():
        st.warning("Note is empty.")
        return False
    sb = get_client()
    try:
        sb.table("quick_notes").insert(
            {"player_id": player_id, "content": content.strip()}
        ).execute()
        return True
    except APIError as exc:  # pragma: no cover - network interaction
        st.error(f"Failed to add note: {exc}")
        return False


def delete_quick_note(note_id: str) -> bool:
    """Delete a quick note by id."""
    if not note_id:
        return False
    sb = get_client()
    try:
        sb.table("quick_notes").delete().eq("id", note_id).execute()
        return True
    except APIError as exc:  # pragma: no cover - network interaction
        st.error(f"Failed to delete note: {exc}")
        return False


def fetch_note_counts_by_player() -> Dict[str, int]:
    """Fetch quick note counts grouped by player id."""
    sb = get_client()
    try:
        data = (
            sb.table("quick_note_counts")
            .select("player_id,note_count")
            .execute()
            .data
        )
        return {row["player_id"]: row["note_count"] for row in (data or [])}
    except APIError as exc:  # pragma: no cover - network interaction
        st.error(f"Failed to load note counts: {exc}")
        return {}
