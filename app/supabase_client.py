"""Supabase client helpers for ScoutLens."""

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st
from supabase import AuthError

from app.utils.supa import get_client as _get_cached_client

__all__ = ["get_client", "sign_in", "sign_out", "session_value"]

_AUTH_STATE_KEY = "auth"
_SESSION_STATE_KEY = "supabase_session"


def session_value(session: Any, key: str) -> Any:
    """Safely retrieve values from Supabase session objects or dicts."""

    if session is None:
        return None

    if hasattr(session, key):
        return getattr(session, key)

    if isinstance(session, dict):
        return session.get(key)

    getter = getattr(session, "get", None)
    if callable(getter):  # pragma: no cover - defensive for mapping-like sessions
        try:
            return getter(key)
        except Exception:
            return None

    return None


def _ensure_auth_state() -> Dict[str, Any]:
    """Return the mutable auth state dict stored in Streamlit session state."""
    auth = st.session_state.setdefault(_AUTH_STATE_KEY, {})
    auth.setdefault("authenticated", False)
    auth.setdefault("user", None)
    return auth


def _serialize_user(user: Any) -> Optional[Dict[str, Any]]:
    """Convert Supabase user model objects to plain dictionaries."""
    if user is None:
        return None
    if isinstance(user, dict):
        return user
    for attr in ("model_dump", "dict"):
        method = getattr(user, attr, None)
        if callable(method):
            try:
                data = method()
            except TypeError:
                data = method(exclude_none=True)  # type: ignore[arg-type]
            if isinstance(data, dict):
                return data
    snapshot: Dict[str, Any] = {}
    for attr in (
        "id",
        "email",
        "app_metadata",
        "user_metadata",
        "role",
        "aud",
        "created_at",
        "last_sign_in_at",
    ):
        if hasattr(user, attr):
            value = getattr(user, attr)
            if value is not None:
                snapshot[attr] = value
    if not snapshot:
        snapshot["repr"] = repr(user)
    return snapshot


def _store_session(session: Any, user: Any | None = None) -> None:
    """Persist access and refresh tokens plus user metadata in session state."""
    access_token = session_value(session, "access_token")
    refresh_token = session_value(session, "refresh_token")
    session_data: Dict[str, str] = {}
    if access_token:
        session_data["access_token"] = access_token
    if refresh_token:
        session_data["refresh_token"] = refresh_token
    if session_data:
        st.session_state[_SESSION_STATE_KEY] = session_data
    auth = _ensure_auth_state()
    auth["authenticated"] = True
    auth["user"] = _serialize_user(user or session_value(session, "user"))
    auth.pop("last_error", None)


def _clear_session_state(reason: Optional[str] = None) -> None:
    """Reset cached Supabase session data and auth flags."""
    had_tokens = st.session_state.pop(_SESSION_STATE_KEY, None) is not None
    auth = _ensure_auth_state()
    auth["authenticated"] = False
    auth["user"] = None
    if reason and had_tokens:
        auth["last_error"] = reason
    else:
        auth.pop("last_error", None)


def _apply_saved_session(client) -> None:
    """Sync Supabase client auth with tokens stored in session state."""
    stored = st.session_state.get(_SESSION_STATE_KEY)
    current = client.auth.get_session()
    current_access = session_value(current, "access_token") if current else None

    if stored:
        access_token = stored.get("access_token")
        refresh_token = stored.get("refresh_token")
        if access_token and refresh_token and access_token != current_access:
            try:
                response = client.auth.set_session(access_token, refresh_token)
            except AuthError as exc:
                print(f"Supabase set_session failed: {exc}")
                _clear_session_state("Your session expired. Please sign in again.")
                return
            session = getattr(response, "session", None)
            user = getattr(response, "user", None)
            if session and session_value(session, "access_token"):
                _store_session(session, user)
                return

    current = client.auth.get_session()
    if current and session_value(current, "access_token"):
        _store_session(current, session_value(current, "user"))
        return

    if stored:
        _clear_session_state("Your session expired. Please sign in again.")
    else:
        _clear_session_state()


def get_client():
    """Return the shared Supabase client, restoring saved auth when present."""
    client = _get_cached_client()
    _apply_saved_session(client)
    return client


def sign_in(email: str, password: str):
    """Authenticate with Supabase email/password and cache the session tokens."""
    response = get_client().auth.sign_in_with_password({"email": email, "password": password})
    session = getattr(response, "session", None)
    user = getattr(response, "user", None)
    if session and session_value(session, "access_token"):
        _store_session(session, user)
    else:
        _clear_session_state()
    return response


def sign_out() -> None:
    """Sign out from Supabase and clear cached session tokens."""
    client = get_client()
    try:
        client.auth.sign_out()
    finally:
        _clear_session_state()
