from typing import Dict, Any, List

from postgrest.exceptions import APIError
from supabase_client import get_client


def insert_player(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a player and return the inserted row.
    Uses returning="representation" to avoid a follow-up select.
    Raises APIError on failure.
    """
    sb = get_client()
    try:
        resp = sb.table("players").insert(payload, returning="representation").execute()
        rows: List[Dict[str, Any]] = resp.data or []
        if not rows:
            raise RuntimeError("Insert returned no rows")
        return rows[0]
    except APIError as e:
        raise
