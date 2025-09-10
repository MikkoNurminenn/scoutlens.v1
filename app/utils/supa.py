from __future__ import annotations
from typing import Any, Dict
import os
from functools import lru_cache

try:
    import streamlit as st
except Exception:  # pragma: no cover - allow headless usage (tests / CLI)
    st = None

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
if st is not None:

    @st.cache_resource  # type: ignore[misc]
    def get_client() -> Client:
        """Return a cached Supabase client bound to anon key."""
        cfg = _read_supabase_config()
        return create_client(cfg["url"], cfg["anon_key"])

else:

    @lru_cache(maxsize=1)
    def get_client() -> Client:
        """Fallback cached client when Streamlit is unavailable."""
        cfg = _read_supabase_config()
        return create_client(cfg["url"], cfg["anon_key"])


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
