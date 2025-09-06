# supabase_client.py
from __future__ import annotations
import os
from functools import lru_cache

try:  # optional dependency
    from supabase import create_client, Client
except Exception:  # pragma: no cover - missing supabase
    create_client = None  # type: ignore
    Client = None  # type: ignore

@lru_cache
def get_client() -> "Client | None":
    """Return a Supabase client if credentials are available, else None."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key or create_client is None:
        return None
    return create_client(url, key)

