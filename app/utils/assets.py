from __future__ import annotations
import base64
import sys
from pathlib import Path


def _base_dir() -> Path:
    """Return base directory accommodating PyInstaller bundles."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # Source run: this file is in app/utils/
    return Path(__file__).resolve().parents[2]


def get_asset_path(name: str) -> Path:
    """Get path to an asset under the repo's assets folder."""
    return _base_dir() / "assets" / name


def set_page_bg(image_path: Path) -> None:
    import streamlit as st
    try:
        data = image_path.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        css = f"""
        <style>
        .stApp {{
            background: 
              linear-gradient(rgba(0,0,0,0.35), rgba(0,0,0,0.35)),
              url("data:image/png;base64,{b64}") center center / cover no-repeat fixed;
        }}
        /* Ensure main blocks are transparent so bg shows through */
        .stApp [data-testid="stHeader"] {{ background: transparent; }}
        .stApp [data-testid="stToolbar"] {{ background: transparent; }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except Exception:
        # Fallback gradient if asset not available
        st.markdown(
            """
            <style>
            .stApp { background: linear-gradient(135deg,#0f172a,#1e293b); }
            </style>
            """,
            unsafe_allow_html=True,
        )
