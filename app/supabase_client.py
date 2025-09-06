# supabase_client.py
from __future__ import annotations
import os
from functools import lru_cache

try:  # optional dependency
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover - Streamlit not available
    st = None  # type: ignore

try:  # optional dependency
    from supabase import create_client, Client
except Exception:  # pragma: no cover - missing supabase
    create_client = None  # type: ignore
    Client = None  # type: ignore


@lru_cache
def get_sb() -> "Client | None":
    """Return a Supabase client using the anon key if available."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if st is not None:
        url = st.secrets.get("SUPABASE_URL", url)
        key = st.secrets.get("SUPABASE_ANON_KEY", key)
    if not url or not key or create_client is None:
        return None
    return create_client(url, key)


__all__ = ["get_sb"]

