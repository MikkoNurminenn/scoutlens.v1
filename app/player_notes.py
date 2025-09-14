from __future__ import annotations
from typing import List, Optional, Dict, Any

import streamlit as st
from postgrest.exceptions import APIError

from app.supabase_client import get_client


TABLE = "notes"


def get_player_notes(player_id: str) -> List[Dict[str, Any]]:
    """Return notes for a player ordered by created_at descending."""
    client = get_client()
    if not client or not player_id:
        return []
    try:
        res = (
            client.table(TABLE)
            .select("*")
            .eq("player_id", player_id)
            .order("created_at", desc=True)
            .execute()
        )
        data = res.data or []
        return data if isinstance(data, list) else []
    except APIError as e:  # pragma: no cover - network
        st.error("Failed to load notes")
        print(e)
        return []


def add_player_note(player_id: str, text: str, tags: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Insert a new note for a player."""
    client = get_client()
    if not client or not player_id or not text:
        return None
    payload: Dict[str, Any] = {"player_id": player_id, "text": text.strip()}
    if tags:
        payload["tags"] = tags
    try:
        res = client.table(TABLE).insert(payload).execute()
        data = res.data or []
        if isinstance(data, list) and data:
            return data[0]
    except APIError as e:  # pragma: no cover - network
        st.error("Failed to add note")
        print(e)
    return None


def delete_player_note(note_id: str) -> bool:
    """Delete a note by id."""
    client = get_client()
    if not client or not note_id:
        return False
    try:
        client.table(TABLE).delete().eq("id", note_id).execute()
        return True
    except APIError as e:  # pragma: no cover - network
        st.error("Failed to delete note")
        print(e)
        return False
