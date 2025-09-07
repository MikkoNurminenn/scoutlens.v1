from __future__ import annotations
from typing import Any, Dict, Optional
import os

try:
    import streamlit as st
except Exception:
    st = None  # allow headless usage (tests / CLI)

from supabase import create_client, Client


def _read_supabase_config() -> Dict[str, str]:
    """
    Prefer Streamlit secrets:
      st.secrets["supabase"]["url"]
      st.secrets["supabase"]["anon_key"]

    Fallback to env:
      SUPABASE_URL
      SUPABASE_ANON_KEY
    """
    url = None
    key = None

    if st is not None:
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["anon_key"]
        except Exception:
            pass

    url = url or os.getenv("SUPABASE_URL")
    key = key or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError(
            "Supabase config missing. Provide Streamlit secrets supabase.url & supabase.anon_key "
            "or env SUPABASE_URL & SUPABASE_ANON_KEY."
        )
    return {"url": url, "anon_key": key}


_client: Optional[Client] = None

def get_client() -> Client:
    global _client
    if _client is None:
        cfg = _read_supabase_config()
        _client = create_client(cfg["url"], cfg["anon_key"])
    return _client


def first_row(rows: Any) -> Optional[Dict[str, Any]]:
    """
    PostgREST Python client returns `.data` as list-like.
    Return the first dict or None.
    """
    if rows is None:
        return None
    data = getattr(rows, "data", rows)
    if isinstance(data, list) and data:
        first = data[0]
        return first if isinstance(first, dict) else None
    return None
