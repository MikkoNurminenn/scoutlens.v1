from __future__ import annotations
from typing import Dict, Any, List
import json

from postgrest.exceptions import APIError
from app.supabase_client import get_client
from app.utils.supa import first_row

sb = get_client()

PLAYER_FIELDS = "id,name,position,nationality,preferred_foot,current_club,transfermarkt_url"


def get_player(player_id: str) -> Dict[str, Any]:
    res = sb.table("players").select(PLAYER_FIELDS).eq("id", player_id).single().execute()
    return res.data


def list_reports_by_player(player_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    res = (
        sb.table("reports")
        .select("id,report_date,competition,opponent,location,attributes")
        .eq("player_id", player_id)
        .order("report_date", desc=True)
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    for r in rows:
        attrs = r.get("attributes")
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except Exception:
                attrs = {}
        if not isinstance(attrs, dict):
            attrs = {}
        r["attributes"] = attrs
    return rows


def insert_player(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a player and return the inserted row.

    The Supabase client returns the affected rows in ``res.data`` so no
    chained ``select`` call is required.
    """
    try:
        resp = sb.table("players").insert(payload).execute()
        row = first_row(resp)
        if not row:
            raise RuntimeError("Insert returned no rows")
        return row
    except APIError as e:
        raise
