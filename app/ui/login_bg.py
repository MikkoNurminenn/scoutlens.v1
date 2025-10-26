from __future__ import annotations

import sys
from pathlib import Path
from base64 import b64encode

import streamlit as st


def _bundle_base() -> Path:
    # PyInstaller support
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # repo/dev root: this file is app/ui/login_bg.py -> go two levels up
    return Path(__file__).resolve().parents[2]


def _candidate_paths(name_or_path: str) -> list[Path]:
    base = _bundle_base()
    p = Path(name_or_path)
    cand = [
        base / "app" / "assets" / p.name,
        base / "assets" / p.name,
        p if p.is_absolute() else base / p,
    ]
    # De-duplicate while preserving order
    seen = set()
    uniq: list[Path] = []
    for c in cand:
        if c not in seen:
            uniq.append(c)
            seen.add(c)
    return uniq


@st.cache_data(show_spinner=False)
def _read_image_b64(p: Path) -> str:
    return b64encode(p.read_bytes()).decode("ascii")


def set_login_background(
    image: str = "login_bg.png", opacity: float = 0.25, add_panel_css: bool = False
) -> None:
    tried = _candidate_paths(image)
    img_path = next((p for p in tried if p.exists()), None)
    if not img_path:
        tried_str = "\n - " + "\n - ".join(str(p) for p in tried)
        st.warning(f"Login background not found. Tried:{tried_str}")
        return

    b64 = _read_image_b64(img_path)
    panel_css = (
        """
      .login-panel {
        background: rgba(0,0,0,0.35);
        backdrop-filter: blur(4px);
        border-radius: 16px;
        padding: 1.25rem;
      }
      .login-panel:empty { display: none; }
    """
        if add_panel_css
        else ""
    )
    css = f"""
    <style>
      [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        inset: 0;
        background-image: url("data:image/png;base64,{b64}");
        background-position: center;
        background-repeat: no-repeat;
        background-size: cover;
        background-attachment: fixed;
        opacity: {opacity};
        z-index: -1;
      }}
      [data-testid="stAppViewContainer"] {{
        background-color: transparent;
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
      }}
      [data-testid="stHeader"] {{
        background: rgba(0,0,0,0);
      }}
      [data-testid="stToolbar"] {{
        right: 2rem;
      }}
      @supports (-webkit-touch-callout: none) {{
        [data-testid="stAppViewContainer"]::before {{
          background-attachment: scroll;
          position: absolute;
        }}
        [data-testid="stAppViewContainer"] {{
          background-attachment: scroll;
        }}
      }}
      {panel_css}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
