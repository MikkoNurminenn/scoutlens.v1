from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from app.supabase_client import get_client, session_value


def _ensure_authenticated_session(client: Any) -> None:
    """Ensure the Supabase client has an authenticated session before writes."""
    auth = getattr(client, "auth", None)
    if auth is None:
        raise PermissionError("Supabase client auth not initialised; sign in required.")

    session = None
    get_session = getattr(auth, "get_session", None)
    if callable(get_session):
        session = get_session()
    else:  # pragma: no cover - defensive for older client versions
        session = getattr(auth, "session", None)

    if not session or session_value(session, "access_token") in (None, ""):
        raise PermissionError("Supabase session missing. Sign in before syncing.")


def push_json(table: str, local_fp: Path) -> tuple[bool, str]:
    """Read a local JSON file and upsert rows into a Supabase table."""
    try:
        sb = get_client()
        _ensure_authenticated_session(sb)
        payload = json.loads(local_fp.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = [payload]
        sb.table(table).upsert(payload).execute()
        return True, f"Upserted {len(payload)} rows into {table}"
    except Exception as e:  # pragma: no cover - supabase network issues
        return False, str(e)


def pull_json(table: str, local_fp: Path) -> tuple[bool, str]:
    """Fetch rows from a Supabase table and write them to a local JSON file."""
    try:
        sb = get_client()
        res = sb.table(table).select("*").execute()
        data = res.data if hasattr(res, "data") else res
        local_fp.parent.mkdir(parents=True, exist_ok=True)
        local_fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True, f"Downloaded {len(data)} rows from {table}"
    except Exception as e:  # pragma: no cover - supabase network issues
        return False, str(e)
