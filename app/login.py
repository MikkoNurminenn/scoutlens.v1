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
    placeholder = st.empty()
    placeholder.markdown(
        """
        <style>
        html, body, .stApp { overflow: hidden !important; }
        .stApp > header,
        .stApp > div[data-testid="stToolbar"],
        .stApp > div[data-testid="stDecoration"],
        .stApp > div[data-testid="stSidebar"] { display: none !important; }
        .sl-login-loading-overlay {
            position: fixed;
            inset: 0;
            display: grid;
            place-items: center;
            padding: 24px;
            background: radial-gradient(900px 600px at 20% 38%, rgba(2,6,23,0.92), rgba(2,6,23,0.86) 45%, rgba(2,6,23,0.72) 70%, rgba(2,6,23,0.55)),
                radial-gradient(820px 520px at 82% 22%, rgba(15,23,42,0.92), rgba(15,23,42,0.65) 52%, rgba(15,23,42,0.42));
            backdrop-filter: blur(18px) saturate(135%);
            z-index: 1000;
            overflow: hidden;
        }
        .sl-login-loading-overlay::before {
            content: "";
            position: absolute;
            width: 160%;
            height: 160%;
            background: conic-gradient(from 130deg, rgba(56,189,248,0.12), rgba(129,140,248,0.18), rgba(56,189,248,0.12), rgba(56,189,248,0.05));
            filter: blur(140px);
            opacity: 0.9;
            animation: sl-login-glow 16s linear infinite;
        }
        .sl-login-loading-card {
            position: relative;
            background:
                linear-gradient(172deg, rgba(15,23,42,0.88), rgba(15,23,42,0.74) 48%, rgba(15,23,42,0.68)) padding-box,
                linear-gradient(160deg, rgba(56,189,248,0.55), rgba(129,140,248,0.45), rgba(96,165,250,0.55)) border-box;
            border-radius: 22px;
            border: 1px solid transparent;
            padding: 44px 40px 36px;
            max-width: 420px;
            width: min(92vw, 420px);
            text-align: center;
            box-shadow: 0 28px 70px rgba(2,6,23,0.55);
            color: #e2e8f0;
            font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            backdrop-filter: blur(20px);
            overflow: hidden;
        }
        .sl-login-loading-card::before {
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(420px 240px at 12% -18%, rgba(56,189,248,0.25), transparent 65%),
                radial-gradient(520px 320px at 88% 118%, rgba(129,140,248,0.18), transparent 70%);
            opacity: 0.75;
            pointer-events: none;
        }
        .sl-login-loading-card h3 {
            margin: 18px 0 8px 0;
            font-size: var(--fs-22, 1.4rem);
            font-weight: 700;
            letter-spacing: -0.01em;
        }
        .sl-login-loading-lede {
            margin: 0;
            font-size: var(--fs-16, 1rem);
            color: rgba(226, 232, 240, 0.88);
        }
        .sl-login-loading-card p {
            margin: 0;
            font-size: var(--fs-14, 0.92rem);
            color: rgba(203, 213, 225, 0.78);
        }
        .sl-login-spinner-wrap {
            position: relative;
            width: 68px;
            height: 68px;
            margin: 0 auto 18px;
        }
        .sl-login-spinner-glow {
            position: absolute;
            inset: -16px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(56,189,248,0.25), rgba(15,23,42,0));
            filter: blur(12px);
            opacity: 0.85;
        }
        .sl-login-spinner {
            position: absolute;
            inset: 0;
            border-radius: 50%;
            background:
                conic-gradient(from 0deg, rgba(56,189,248,0.95), rgba(56,189,248,0.15) 120deg, rgba(129,140,248,0.85) 240deg, rgba(56,189,248,0.95));
            -webkit-mask: radial-gradient(farthest-side, #0000 calc(100% - 6px), #000 calc(100% - 6px));
            mask: radial-gradient(farthest-side, transparent calc(100% - 6px), #000 calc(100% - 6px));
            animation: sl-login-spin 0.9s linear infinite;
            box-shadow: 0 0 26px rgba(56,189,248,0.35);
        }
        .sl-login-pill {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 10px 16px;
            border-radius: 999px;
            margin: 22px auto 10px;
            background: linear-gradient(120deg, rgba(56,189,248,0.16), rgba(129,140,248,0.12));
            border: 1px solid rgba(148, 163, 184, 0.15);
            color: rgba(226, 232, 240, 0.88);
            font-size: var(--fs-13, 0.82rem);
            font-weight: 500;
            letter-spacing: 0.01em;
        }
        .sl-login-pill::before {
            content: "";
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: linear-gradient(135deg, #38bdf8, #6366f1);
            box-shadow: 0 0 12px rgba(56,189,248,0.75);
            animation: sl-login-pulse 1.8s ease-in-out infinite;
        }
        .sl-login-subcopy {
            margin-top: 6px;
            font-size: var(--fs-13, 0.85rem);
            color: rgba(148, 163, 184, 0.78);
        }
        .sl-login-progress {
            position: relative;
            margin-top: 24px;
            height: 4px;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.16);
            overflow: hidden;
        }
        .sl-login-progress-bar {
            position: absolute;
            inset: 0;
            width: 32%;
            border-radius: inherit;
            background: linear-gradient(120deg, rgba(56,189,248,0.75), rgba(129,140,248,0.9));
            animation: sl-login-progress 2.2s ease-in-out infinite;
        }
        @keyframes sl-login-spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes sl-login-glow {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes sl-login-pulse {
            0%, 100% { transform: scale(1); opacity: 0.9; }
            50% { transform: scale(1.25); opacity: 1; }
        }
        @keyframes sl-login-progress {
            0% { transform: translateX(-120%); }
            50% { transform: translateX(30%); }
            100% { transform: translateX(120%); }
        }
        </style>
        <div class="sl-login-loading-overlay">
            <div class="sl-login-loading-card">
                <div class="sl-login-spinner-wrap">
                    <div class="sl-login-spinner-glow"></div>
                    <div class="sl-login-spinner"></div>
                </div>
                <h3>Welcome back to ScoutLens</h3>
                <p class="sl-login-loading-lede">Curating your scouting intel and syncing secure access.</p>
                <div class="sl-login-pill">Establishing trusted Supabase session</div>
                <p class="sl-login-subcopy">Please hold on for just a moment.</p>
                <div class="sl-login-progress"><span class="sl-login-progress-bar"></span></div>
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

    auth_state = _ensure_auth_state()
    client = get_client()
    session = None
    try:
        session = client.auth.get_session()
    except AuthApiError as exc:
        print(f"Supabase get_session API error: {exc}")
        auth_state["last_error"] = "Your session has expired. Please sign in again."
        try:
            supabase_sign_out()
        except Exception as sign_out_exc:  # pragma: no cover - defensive cleanup
            print(f"Supabase sign_out after get_session failure: {sign_out_exc}")
    except AuthError as exc:
        print(f"Supabase get_session auth error: {exc}")
        auth_state["last_error"] = "Authentication error when restoring your session. Please sign in again."
    except Exception as exc:  # pragma: no cover - unexpected runtime failures
        print(f"Supabase get_session unexpected error: {exc}")
        auth_state["last_error"] = "Unable to verify your session. Please try signing in again."
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
