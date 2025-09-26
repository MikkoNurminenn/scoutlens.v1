"""Streamlit authentication gate backed by Supabase email/password auth."""

from __future__ import annotations

import time
from typing import Dict

import streamlit as st
from supabase import AuthApiError, AuthError

from app.supabase_client import (
    get_client,
    session_value,
    sign_in as supabase_sign_in,
    sign_out as supabase_sign_out,
)
from app.ui import bootstrap_sidebar_auto_collapse
from app.ui.login_bg import set_login_background

bootstrap_sidebar_auto_collapse()

_LAST_EMAIL_KEY = "login__last_email"
_FORM_KEY = "login_form"
_POST_LOGIN_LOADING_KEY = "login__post_auth_loading"


def _ensure_auth_state() -> Dict[str, object]:
    return st.session_state.setdefault("auth", {"authenticated": False, "user": None})


def _render_post_login_loading() -> None:
    st.markdown(
        """
        <style>
        .sl-login-loading-overlay {
            position: fixed;
            inset: 0;
            display: grid;
            place-items: center;
            background: radial-gradient(900px 540px at 22% 46%, rgba(15,23,42,0.90), rgba(15,23,42,0.80) 48%, rgba(15,23,42,0.65) 72%, rgba(15,23,42,0.35));
            z-index: 1000;
        }
        .sl-login-loading-card {
            background: rgba(15, 23, 42, 0.75);
            border-radius: 16px;
            border: 1px solid rgba(148, 163, 184, 0.25);
            padding: 36px 32px;
            max-width: 360px;
            width: min(92vw, 360px);
            text-align: center;
            box-shadow: 0 12px 30px rgba(2,6,23,0.35);
            color: #e2e8f0;
            font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        .sl-login-loading-card h3 {
            margin: 18px 0 8px 0;
            font-size: var(--fs-22, 1.35rem);
            font-weight: 700;
        }
        .sl-login-loading-card p {
            margin: 0;
            font-size: var(--fs-15, 0.95rem);
            color: rgba(226, 232, 240, 0.85);
        }
        .sl-login-spinner {
            width: 54px;
            height: 54px;
            border-radius: 50%;
            border: 4px solid rgba(148, 163, 184, 0.35);
            border-top-color: #38bdf8;
            margin: 0 auto;
            animation: sl-login-spin 1s linear infinite;
        }
        @keyframes sl-login-spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        </style>
        <div class="sl-login-loading-overlay">
            <div class="sl-login-loading-card">
                <div class="sl-login-spinner"></div>
                <h3>Signing you in…</h3>
                <p>ScoutLens is getting your workspace ready.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    time.sleep(0.75)


def logout() -> None:
    """Terminate the Supabase session and rerun the app."""
    try:
        supabase_sign_out()
    except Exception as exc:  # pragma: no cover - defensive logging for UI usage
        print(f"Supabase sign_out failed: {exc}")
    st.rerun()


def _inject_login_styles(opacity: float) -> None:
    set_login_background("login_bg.png", opacity=opacity)
    st.markdown('<div class="sl-hero"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        html, body, .stApp { background: transparent !important; }
        .block-container { min-height: 88vh; display: grid; place-items: center; }
        .login-scrim { position: fixed; inset: 0; pointer-events: none;
          background: radial-gradient(900px 520px at 18% 40%, rgba(2,6,23,.60), rgba(2,6,23,.35) 45%, rgba(2,6,23,.15) 70%, transparent 85%); }
        div[data-testid="stForm"] {
          width: 100%; max-width: 440px; margin: 0 auto;
          background: rgba(15, 23, 42, 0.40); backdrop-filter: blur(6px);
          border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);
          box-shadow: 0 4px 20px rgba(0,0,0,.18); padding: 22px 20px;
        }
        div[data-testid="stForm"] > div { padding: 0 !important; }
        .form-title { color: #e2e8f0; margin: 0 0 8px 0; font-weight: 700; font-size: var(--fs-20); }
        .stTextInput > div > div > input {
          background: rgba(2,6,23,.80);
          border: 1px solid rgba(255,255,255,.10);
          color: #f8fafc; border-radius: 12px;
        }
        .stTextInput > label { color: #e2e8f0; }
        .stButton button { border-radius: 12px; padding: 10px 14px; font-weight: 600; }
        .login-caption { color: rgba(226, 232, 240, 0.8); font-size: var(--fs-14); margin-bottom: 12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        div[data-testid="stForm"] { max-width: clamp(340px, 36vw, 580px); }
        @media (min-width: 1200px) and (max-width: 2400px) and (min-aspect-ratio: 1/1.3) and (max-aspect-ratio: 5/4) {
          div[data-testid="stForm"] { max-width: 620px; padding: 28px 24px; border-radius: 16px; }
          .form-title { font-size: var(--fs-24); }
          .stTextInput > div > div > input { font-size: var(--fs-16); padding: 12px 14px; }
          .stButton button { font-size: var(--fs-16); padding: 12px 16px; border-radius: 14px; }
        }
        @media (max-width: 540px) {
          div[data-testid="stForm"] { max-width: 94vw; padding: 18px 16px; border-radius: 10px; }
          .form-title { font-size: var(--fs-16); }
        }
        @media (max-height: 520px) and (orientation: landscape) {
          .block-container { padding-top: 2vh !important; padding-bottom: 2vh !important; }
          div[data-testid="stForm"] { max-width: 520px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def login(
    title: str = "ScoutLens",
    *,
    dim_background: bool = False,
    background_opacity: float = 1.0,
) -> None:
    """Render the authentication form when the user is not signed in."""

    _ensure_auth_state()
    client = get_client()
    session = client.auth.get_session()
    if session and session_value(session, "access_token"):
        if st.session_state.pop(_POST_LOGIN_LOADING_KEY, False):
            _render_post_login_loading()
            st.rerun()
        return

    _inject_login_styles(background_opacity)
    if dim_background:
        st.markdown('<div class="login-scrim"></div>', unsafe_allow_html=True)

    auth_state = st.session_state.get("auth", {})
    last_error = auth_state.pop("last_error", None)

    with st.form(_FORM_KEY, clear_on_submit=False):
        st.markdown(f"<div class='form-title'>{title}</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='login-caption'>Sign in with your Supabase email and password. Writes require authentication.</div>",
            unsafe_allow_html=True,
        )
        default_email = st.session_state.get(_LAST_EMAIL_KEY, "")
        email = st.text_input(
            "Email",
            value=default_email,
            autocomplete="email",
            placeholder="you@example.com",
        )
        password = st.text_input(
            "Password",
            type="password",
            autocomplete="current-password",
            placeholder="Enter your password",
        )
        submitted = st.form_submit_button("Sign in", type="primary")

    if last_error:
        st.warning(last_error)

    if submitted:
        email = email.strip()
        st.session_state[_LAST_EMAIL_KEY] = email
        if not email:
            st.warning("Email is required.")
            st.stop()
        if not password:
            st.warning("Password is required.")
            st.stop()
        try:
            response = supabase_sign_in(email=email, password=password)
        except AuthApiError as exc:
            print(f"Supabase sign_in invalid credentials: {exc}")
            st.error("Invalid email or password. Please try again.")
            st.stop()
        except AuthError as exc:
            print(f"Supabase sign_in auth error: {exc}")
            st.error("Authentication failed. Please try again in a moment.")
            st.stop()
        except Exception as exc:  # pragma: no cover - unexpected runtime failures
            print(f"Supabase sign_in unexpected error: {exc}")
            st.error("Unexpected error during sign in. Please retry.")
            st.stop()

        session = getattr(response, "session", None)
        if not session or not session_value(session, "access_token"):
            st.error("Supabase did not return a valid session. Please try again.")
            st.stop()

        st.session_state[_POST_LOGIN_LOADING_KEY] = True
        st.rerun()

    st.stop()


__all__ = ["login", "logout"]
