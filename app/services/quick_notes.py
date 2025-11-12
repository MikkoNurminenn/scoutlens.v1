"""Service layer for the Quick Notes feature.

All direct Supabase interactions for the Quick Notes page live here so the
Streamlit view can stay focused on UI rendering.  The helper functions in this
module expose a small, well defined API that mirrors the operations available in
the UI (listing, creating, updating and deleting notes as well as loading
player metadata).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from postgrest.exceptions import APIError

from app.supabase_client import get_client

__all__ = [
    "list_quick_notes",
    "create_quick_note",
    "update_quick_note",
    "delete_quick_note",
    "list_players",
    "get_player_note_counts",
    "get_quick_note",
]

_TABLE = "quick_notes"
_PLAYERS_TABLE = "players"
_COUNTS_VIEW = "quick_note_counts"


def _client():
    client = get_client()
    if client is None:  # pragma: no cover - defensive
        raise RuntimeError("Supabase client not configured")
    return client


def _ensure_iso(dt_val: Optional[datetime]) -> Optional[str]:
    if not dt_val:
        return None
    value = dt_val
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return value.astimezone().isoformat()


def list_quick_notes(
    q: str,
    player_id: Optional[str],
    tags: Iterable[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    limit: int,
    offset: int,
) -> Tuple[List[Dict[str, Any]], int]:
    """Return paginated quick notes filtered by the provided parameters."""

    client = _client()
    query = (
        client.table(_TABLE)
        .select(
            "id, player_id, title, content, tags, created_at, updated_at",
            count="exact",
        )
        .order("updated_at", desc=True)
    )

    if q:
        term = q.strip()
        if term:
            query = query.or_(
                f"title.ilike.%{term}%,content.ilike.%{term}%",
            )

    if player_id:
        query = query.eq("player_id", player_id)

    tag_list = [tag for tag in tags if tag]
    if tag_list:
        query = query.contains("tags", tag_list)

    iso_from = _ensure_iso(date_from)
    if iso_from:
        query = query.gte("updated_at", iso_from)

    iso_to = _ensure_iso(date_to)
    if iso_to:
        query = query.lte("updated_at", iso_to)

    range_start = max(offset, 0)
    range_end = max(range_start + limit - 1, range_start)

    try:
        response = query.range(range_start, range_end).execute()
    except APIError as exc:  # pragma: no cover - direct Supabase call
        raise RuntimeError(_format_api_error("list_quick_notes", exc)) from exc

    data = response.data or []
    total = getattr(response, "count", None)
    return data, int(total) if total is not None else len(data)


def create_quick_note(payload: Dict[str, Any]) -> Dict[str, Any]:
    client = _client()
    clean_payload = _clean_payload(payload)
    try:
        response = client.table(_TABLE).insert(clean_payload).execute()
    except APIError as exc:  # pragma: no cover - direct Supabase call
        raise RuntimeError(_format_api_error("create_quick_note", exc)) from exc

    rows = response.data or []
    if not rows:
        raise RuntimeError("Supabase did not return the created quick note")
    return rows[0]


def update_quick_note(note_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    if not note_id:
        raise ValueError("note_id is required")

    client = _client()
    clean_patch = _clean_payload(patch, allow_partial=True)
    try:
        response = (
            client.table(_TABLE)
            .update(clean_patch)
            .eq("id", note_id)
            .select("*")
            .execute()
        )
    except APIError as exc:  # pragma: no cover - direct Supabase call
        raise RuntimeError(_format_api_error("update_quick_note", exc)) from exc

    rows = response.data or []
    if not rows:
        raise RuntimeError("Quick note not found for update")
    return rows[0]


def delete_quick_note(note_id: str) -> None:
    if not note_id:
        raise ValueError("note_id is required")
    client = _client()
    try:
        client.table(_TABLE).delete().eq("id", note_id).execute()
    except APIError as exc:  # pragma: no cover - direct Supabase call
        raise RuntimeError(_format_api_error("delete_quick_note", exc)) from exc


def list_players() -> List[Dict[str, Any]]:
    client = _client()
    try:
        response = (
            client.table(_PLAYERS_TABLE)
            .select("id, name")
            .order("name")
            .execute()
        )
    except APIError as exc:  # pragma: no cover - direct Supabase call
        raise RuntimeError(_format_api_error("list_players", exc)) from exc
    return response.data or []


def get_player_note_counts() -> Dict[str, int]:
    client = _client()
    try:
        response = client.table(_COUNTS_VIEW).select("player_id, note_count").execute()
    except APIError as exc:  # pragma: no cover - direct Supabase call
        raise RuntimeError(_format_api_error("get_player_note_counts", exc)) from exc
    return {row["player_id"]: row["note_count"] for row in (response.data or [])}


def get_quick_note(note_id: str) -> Optional[Dict[str, Any]]:
    if not note_id:
        return None
    client = _client()
    try:
        response = (
            client.table(_TABLE)
            .select("id, player_id, title, content, tags, created_at, updated_at")
            .eq("id", note_id)
            .limit(1)
            .execute()
        )
    except APIError as exc:  # pragma: no cover - direct Supabase call
        raise RuntimeError(_format_api_error("get_quick_note", exc)) from exc
    rows = response.data or []
    return rows[0] if rows else None


def _clean_payload(
    payload: Dict[str, Any], *, allow_partial: bool = False
) -> Dict[str, Any]:
    allowed_keys = {"title", "content", "player_id", "tags"}
    keys: Iterable[str]
    if allow_partial:
        keys = [key for key in payload.keys() if key in allowed_keys]
    else:
        keys = allowed_keys

    clean: Dict[str, Any] = {}
    for key in keys:
        value = payload.get(key)
        if key == "title":
            clean[key] = (value or "").strip() or None
        elif key == "content":
            clean[key] = (value or "").strip()
        elif key == "tags":
            clean[key] = _normalize_tags(value)
        else:
            clean[key] = value

    if not allow_partial:
        if not clean.get("content"):
            raise ValueError("content is required")
        if not clean.get("player_id"):
            raise ValueError("player_id is required")

    return clean


def _normalize_tags(tags: Any) -> List[str]:
    if not tags:
        return []
    if isinstance(tags, str):
        raw = tags.split(",")
    else:
        raw = list(tags)
    seen = set()
    result: List[str] = []
    for tag in raw:
        text = (str(tag) or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text[:48])
    return result


def _format_api_error(context: str, exc: APIError) -> str:
    message = getattr(exc, "message", str(exc))
    hint = getattr(exc, "hint", "")
    details = getattr(exc, "details", "")
    parts = [f"{context}: {message}"]
    if details:
        parts.append(str(details))
    if hint:
        parts.append(str(hint))
    return " | ".join(parts)
