from __future__ import annotations
from typing import Any, Dict, Optional
import os
from functools import lru_cache

import httpx

try:
    import streamlit as st
except Exception:  # pragma: no cover - allow headless usage (tests / CLI)
    st = None

from supabase import Client, ClientOptions, SupabaseException, create_client


class SupabaseConfigError(RuntimeError):
    """Raised when Supabase credentials are missing from secrets or env."""


class SupabaseConnectionError(RuntimeError):
    """Raised when the client cannot reach Supabase within the timeout window."""


_MISSING_CONFIG_MSG = (
    "Supabase secrets missing. Add `[supabase].url` and `[supabase].anon_key` to "
    "`.streamlit/secrets.toml` or set SUPABASE_URL and SUPABASE_ANON_KEY environment "
    "variables."
)


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
        raise SupabaseConfigError(_MISSING_CONFIG_MSG)

    return {"url": url, "anon_key": key}


def _build_client_options() -> ClientOptions:
    """Return Supabase client options with tighter HTTP timeouts."""

    timeout = httpx.Timeout(10.0, connect=5.0)
    return ClientOptions(
        httpx_client=httpx.Client(timeout=timeout),
        postgrest_client_timeout=timeout,
        storage_client_timeout=timeout,
        function_client_timeout=timeout,
    )


def _create_supabase_client() -> Client:
    cfg = _read_supabase_config()
    options = _build_client_options()
    try:
        return create_client(cfg["url"], cfg["anon_key"], options=options)
    except SupabaseException as exc:
        client = options.httpx_client
        if client is not None:
            client.close()
        raise SupabaseConfigError(str(exc) or _MISSING_CONFIG_MSG) from exc
    except httpx.HTTPStatusError as exc:
        client = options.httpx_client
        if client is not None:
            client.close()
        status = exc.response.status_code if exc.response is not None else "unknown"
        body = None
        if exc.response is not None:
            try:
                body = exc.response.text
            except Exception:  # pragma: no cover - defensive fallback
                body = None
        if body:
            preview = body.strip().replace("\n", " ")[:200]
            print(f"Supabase client HTTP error: {status} -> {preview}")
        else:
            print(f"Supabase client HTTP error: {status} -> {exc}")
        raise SupabaseConfigError(
            "Supabase responded with HTTP "
            f"{status}. Verify the Supabase URL/anon key in your Streamlit secrets or environment."
        ) from exc
    except httpx.HTTPError as exc:
        client = options.httpx_client
        if client is not None:
            client.close()
        print(f"Supabase client connection failed: {exc}")
        raise SupabaseConnectionError(
            "Unable to reach Supabase right now. Check your internet connection and try again."
        ) from exc


if st is not None:

    @st.cache_resource  # type: ignore[misc]
    def get_client() -> Client:
        """Return a cached Supabase client bound to anon key."""
        return _create_supabase_client()

else:

    @lru_cache(maxsize=1)
    def get_client() -> Client:
        """Fallback cached client when Streamlit is unavailable."""
        return _create_supabase_client()


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

__all__ = [
    "get_client",
    "first_row",
    "SupabaseConfigError",
    "SupabaseConnectionError",
]
