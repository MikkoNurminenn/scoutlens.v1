# file: app/login.py
from __future__ import annotations

import binascii
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

import streamlit as st

from app.ui.login_bg import set_login_background


# ============================
# Password hashing utilities
# ============================
# Why: avoid plaintext; PBKDF2-HMAC/SHA256 is in the stdlib and battle-tested.


def _pbkdf2_sha256(password_bytes: bytes, salt: bytes, iterations: int) -> bytes:
    import hashlib

    return hashlib.pbkdf2_hmac("sha256", password_bytes, salt, iterations, dklen=32)


def _pbkdf2_hash(password: str, salt_hex: str, iterations: int = 200_000) -> str:
    salt = binascii.unhexlify(salt_hex)
    dk = _pbkdf2_sha256(password.encode("utf-8"), salt, iterations)
    return binascii.hexlify(dk).decode("ascii")


def generate_password_hash(password: str, *, iterations: int = 200_000) -> Tuple[str, str]:
    """Return (salt_hex, hash_hex) for provisioning users in secrets.toml."""
    salt = os.urandom(16)
    salt_hex = binascii.hexlify(salt).decode("ascii")
    hash_hex = _pbkdf2_hash(password, salt_hex, iterations)
    return salt_hex, hash_hex


def verify_password(password: str, *, salt_hex: str, expected_hash_hex: str, iterations: int = 200_000) -> bool:
    computed = _pbkdf2_hash(password, salt_hex, iterations)
    return hmac.compare_digest(computed, expected_hash_hex)


# ============================
# Config & state
# ============================

@dataclass
class AuthConfig:
    min_password_len: int = 8
    lockout_after: int = 5  # failed attempts
    lockout_minutes: int = 5


@dataclass
class UserRecord:
    username: str
    display_name: str
    password_hash: str
    salt: str


@dataclass
class StaticCreds:
    username: str
    password: str
    display_name: str


_DEF_TZ = timezone.utc


def _now() -> datetime:
    return datetime.now(tz=_DEF_TZ)


def _read_auth_config() -> AuthConfig:
    data = st.secrets.get("auth", {})
    return AuthConfig(
        min_password_len=int(data.get("min_password_len", 8)),
        lockout_after=int(data.get("lockout_after", 5)),
        lockout_minutes=int(data.get("lockout_minutes", 5)),
    )


def _read_user(username: str) -> Optional[UserRecord]:
    users: Dict[str, Dict[str, str]] = st.secrets.get("users", {})  # type: ignore[assignment]
    raw = users.get(username)
    if not raw:
        return None
    return UserRecord(
        username=username,
        display_name=raw.get("display_name", username),
        password_hash=raw.get("password_hash", ""),
        salt=raw.get("salt", ""),
    )


def _read_static_creds() -> StaticCreds:
    data = st.secrets.get("static", {})
    return StaticCreds(
        username=str(data.get("username", "Santeri")),
        password=str(data.get("password", "Volotinen")),
        display_name=str(data.get("display_name", "Santeri Volotinen")),
    )


def _ensure_auth_state() -> None:
    st.session_state.setdefault(
        "auth",
        {
            "authenticated": False,
            "user": None,  # mapping with username & name
            "attempts": 0,
            "lock_until": None,
        },
    )


def _locked_until() -> Optional[datetime]:
    lock_until = st.session_state.get("auth", {}).get("lock_until")
    return lock_until  # may be None or datetime


def _register_failure(cfg: AuthConfig) -> None:
    auth = st.session_state["auth"]
    auth["attempts"] = int(auth.get("attempts", 0)) + 1
    if auth["attempts"] >= cfg.lockout_after:
        auth["lock_until"] = _now() + timedelta(minutes=cfg.lockout_minutes)
        auth["attempts"] = 0


def _clear_failures() -> None:
    auth = st.session_state["auth"]
    auth["attempts"] = 0
    auth["lock_until"] = None


# ============================
# Public API
# ============================

def logout() -> None:
    """Log the user out and refresh app."""
    _ensure_auth_state()
    st.session_state["auth"]["authenticated"] = False
    st.session_state["auth"]["user"] = None
    st.rerun()


def login(
    title: str = "ScoutLens",
    *,
    dim_background: bool = False,
    background_opacity: float = 1.0,
) -> None:
    """
    Minimal, hardened username/password gate using Streamlit session_state.

    Credentials strategies:
      1) Static dev creds (always allowed):
         [static]
         username = "Santeri"
         password = "Volotinen"
         display_name = "Santeri Volotinen"

      2) Optional hashed users:
         [auth]
         min_password_len = 8
         lockout_after = 5
         lockout_minutes = 5

         [users.santeri]
         display_name = "Santeri Volotinen"
         salt = "<hex>"
         password_hash = "<hex>"

    - background_opacity: passed to set_login_background (1.0 = 100%).
    - dim_background: if True, adds a radial scrim to improve contrast.
    """
    _ensure_auth_state()
    if st.session_state["auth"].get("authenticated"):
        return

    cfg = _read_auth_config()
    static_creds = _read_static_creds()

    # Background & card styles
    set_login_background("login_bg.png", opacity=background_opacity)
    st.markdown(
        """
        <style>
        html, body, .stApp { background: transparent !important; }
        .block-container { min-height: 88vh; display: grid; place-items: center; }
        /* Optional dimmer */
        .login-scrim { position: fixed; inset: 0; pointer-events: none;
          background: radial-gradient(900px 520px at 18% 40%, rgba(2,6,23,.60), rgba(2,6,23,.35) 45%, rgba(2,6,23,.15) 70%, transparent 85%); }
        /* Make the FORM itself the glass card */
        div[data-testid="stForm"] {
          width: 100%; max-width: 440px; margin: 0 auto;
          background: rgba(15, 23, 42, 0.40); backdrop-filter: blur(6px);
          border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);
          box-shadow: 0 4px 20px rgba(0,0,0,.18); padding: 22px 20px;
        }
        div[data-testid="stForm"] > div { padding: 0 !important; }
        .form-title { color: #e2e8f0; margin: 0 0 8px 0; font-weight: 700; font-size: 1.35rem; }
        /* Inputs */
        .stTextInput > div > div > input {
          background: rgba(2,6,23,.80);
          border: 1px solid rgba(255,255,255,.10);
          color: #f8fafc; border-radius: 12px;
        }
        .stTextInput > label, .stCheckbox > label { color: #e2e8f0; }
        .stCheckbox > div[role="checkbox"] { border-radius: 6px; }
        .stButton button { border-radius: 12px; padding: 10px 14px; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Lockout check
    lu = _locked_until()
    if isinstance(lu, datetime) and lu > _now():
        remaining = int((lu - _now()).total_seconds())
        minutes, seconds = divmod(remaining, 60)
        st.error(f"Too many attempts. Try again in {minutes} min {seconds} s.")
        st.stop()

    # Optional dim layer
    if dim_background:
        st.markdown('<div class="login-scrim"></div>', unsafe_allow_html=True)

    # ---- UI ----
    with st.form("login_form", clear_on_submit=False):
        st.markdown(f"<div class='form-title'>{title}</div>", unsafe_allow_html=True)

        username = st.text_input(
            "Username",
            autocomplete="username",
            placeholder="Enter your username",
        )
        password = st.text_input(
            "Password",
            type="password",
            autocomplete="current-password",
            placeholder="Enter your password",
        )
        remember = st.checkbox("Keep me signed in (this session)", value=True)
        submitted = st.form_submit_button("Sign in")

    if submitted:
        if len(password) < cfg.min_password_len:
            st.warning(f"Password must be at least {cfg.min_password_len} characters.")
            st.stop()

        # 1) Static dev creds always allowed first
        authed: Optional[UserRecord] = None
        if username == static_creds.username and password == static_creds.password:
            authed = UserRecord(
                username=static_creds.username,
                display_name=static_creds.display_name,
                password_hash="",
                salt="",
            )
        else:
            # 2) Try hashed user directory
            user = _read_user(username)
            if user and user.salt and user.password_hash:
                if verify_password(password, salt_hex=user.salt, expected_hash_hex=user.password_hash):
                    authed = user

        if not authed:
            _register_failure(cfg)
            st.error("Invalid username or password.")
            st.stop()

        _clear_failures()
        auth = st.session_state["auth"]
        auth["authenticated"] = True
        auth["user"] = {"username": authed.username, "name": authed.display_name}
        if not remember:
            auth["ephemeral"] = True  # consumers may treat this as reduced caching

        st.rerun()

    st.stop()


# ============================
# Tiny admin helper
# ============================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate salt+hash for secrets.toml")
    parser.add_argument("password", help="plaintext password to hash")
    args = parser.parse_args()

    salt_hex, hash_hex = generate_password_hash(args.password)
    print("salt =", salt_hex)
    print("password_hash =", hash_hex)
