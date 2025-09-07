from __future__ import annotations
from typing import Dict, Any

from postgrest.exceptions import APIError
from app.utils.supa import get_client, first_row


def insert_player(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a player and return the inserted row.

    The Supabase client returns the affected rows in ``res.data`` so no
    chained ``select`` call is required.
    """
    sb = get_client()
    try:
        resp = sb.table("players").insert(payload).execute()
        row = first_row(resp)
        if not row:
            raise RuntimeError("Insert returned no rows")
        return row
    except APIError as e:
        raise
