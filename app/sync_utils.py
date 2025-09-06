from __future__ import annotations
from pathlib import Path
import streamlit as st
from supabase import create_client


def _client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
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
