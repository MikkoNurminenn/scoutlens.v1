"""Helpers for building and sanitizing report payloads."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional


def serialize_report_attributes(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure report attributes only contain JSON-serializable primitives."""

    if not isinstance(attrs, dict):
        return {}

    def _fallback(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)

    clean: Dict[str, Any] = {}
    for key, value in attrs.items():
        if isinstance(value, str):
            value = value.strip()
        clean[key] = _fallback(value)
    return clean


def build_report_payload(
    *,
    player_id: str,
    player_name: Optional[str],
    report_date: date,
    competition: Optional[str],
    opponent: Optional[str],
    location: Optional[str],
    attrs: Dict[str, Any],
    match_id: Optional[str] = None,
    include_player_name: bool = True,
) -> Dict[str, Any]:
    """Compose the Supabase payload for a new report with sanitized values."""

    payload: Dict[str, Any] = {
        "player_id": player_id,
        "report_date": report_date.isoformat(),
        "competition": (competition or "").strip() or None,
        "opponent": (opponent or "").strip() or None,
        "location": (location or "").strip() or None,
        "attributes": serialize_report_attributes(attrs),
    }

    if include_player_name:
        player_name_clean = (player_name or "").strip()
        if player_name_clean:
            payload["player_name"] = player_name_clean

    if match_id:
        payload["match_id"] = match_id

    return payload
