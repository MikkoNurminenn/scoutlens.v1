from __future__ import annotations
import json
import os
from pathlib import Path

import streamlit as st
from supabase import create_client


def _client():
    """Create a Supabase client using service role credentials."""
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE") or st.secrets.get(
        "SUPABASE_SERVICE_ROLE"
    )
    if not url or not key:
        raise RuntimeError("Supabase credentials not configured")
    return create_client(url, key)


def push_json(table: str, local_fp: Path) -> tuple[bool, str]:
    """Read a local JSON file and upsert rows into a Supabase table."""
    try:
        sb = _client()
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
        sb = _client()
        res = sb.table(table).select("*").execute()
        data = res.data if hasattr(res, "data") else res
        local_fp.parent.mkdir(parents=True, exist_ok=True)
        local_fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True, f"Downloaded {len(data)} rows from {table}"
    except Exception as e:  # pragma: no cover - supabase network issues
        return False, str(e)
