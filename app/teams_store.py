# file: app/teams_store.py
"""Minimal team store shim backed by Supabase."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import threading
import uuid

try:  # pragma: no cover - optional UI feedback when Streamlit available
    import streamlit as st
except Exception:  # pragma: no cover - running headless
    st = None  # type: ignore

from postgrest.exceptions import APIError

from app.supabase_client import get_client

_LOCK = threading.Lock()


def _notify_error(msg: str) -> None:
    if st is not None:
        st.error(msg)
    else:
        print(msg)


def _sanitize_team_payload(team: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key, value in team.items():
        if value in (None, ""):
            continue
        payload[key] = value
    return payload


def list_teams() -> List[Dict[str, Any]]:
    """Return all teams stored in Supabase ordered by name."""
    client = get_client()
    if not client:
        return []
    try:
        res = client.table("teams").select("*").order("name").execute()
    except APIError as err:  # pragma: no cover - UI feedback
        _notify_error(f"Failed to load teams: {getattr(err, 'message', str(err))}")
        return []
    return [dict(row) for row in (res.data or [])]


def add_team(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Add or upsert a team row in Supabase."""

    if len(args) == 1 and isinstance(args[0], dict):
        team: Dict[str, Any] = dict(args[0])
    else:
        team = dict(kwargs)

    name: Optional[str] = team.get("name")
    if not name or not isinstance(name, str):
        raise ValueError("add_team requires a 'name' string field")

    payload = _sanitize_team_payload(team)
    payload["name"] = name.strip()
    payload.setdefault("id", str(team.get("id") or uuid.uuid4()))

    client = get_client()
    if not client:
        raise RuntimeError("Supabase client is not configured")

    with _LOCK:
        try:
            try:
                client.table("teams").upsert(payload, on_conflict="name").execute()
            except TypeError:
                client.table("teams").upsert(payload).execute()
        except APIError as err:
            _notify_error(f"Failed to save team: {getattr(err, 'message', str(err))}")
            raise

        try:
            res = (
                client.table("teams")
                .select("*")
                .eq("name", payload["name"])
                .limit(1)
                .execute()
            )
            stored = dict(res.data[0]) if res.data else payload
        except APIError as err:  # pragma: no cover - fallback to payload
            _notify_error(f"Failed to load saved team: {getattr(err, 'message', str(err))}")
            stored = payload

    if st is not None:
        st.cache_data.clear()
    return stored


__all__ = ["add_team", "list_teams"]
