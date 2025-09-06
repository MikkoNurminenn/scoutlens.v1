from __future__ import annotations
from pathlib import Path
import os
import streamlit as st
from supabase import create_client


def _client():
    """Supabase client authenticated with the service role key."""
    url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_SERVICE_ROLE") or os.environ.get("SUPABASE_SERVICE_ROLE")
    if not url or not key:
        raise RuntimeError("Supabase service role credentials missing")
    return create_client(url, key)


def push_json(bucket: str, key: str, local_fp: Path) -> tuple[bool, str]:
    try:
        sb = _client()
        data_bytes = local_fp.read_bytes()
        sb.storage.from_(bucket).upload(
            path=key,
            file=data_bytes,
            file_options={"content-type": "application/json", "upsert": True},
        )
        return True, f"Uploaded {key}"
    except Exception as e:
        return False, str(e)


def pull_json(bucket: str, key: str, local_fp: Path) -> tuple[bool, str]:
    try:
        sb = _client()
        res = sb.storage.from_(bucket).download(key)
        local_fp.parent.mkdir(parents=True, exist_ok=True)
        local_fp.write_bytes(res)
        return True, f"Downloaded {key}"
    except Exception as e:
        return False, str(e)
