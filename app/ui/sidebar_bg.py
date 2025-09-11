from __future__ import annotations
import sys
from pathlib import Path
from base64 import b64encode
import streamlit as st


def _base_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def _candidate_paths(name_or_path: str) -> list[Path]:
    base = _base_dir()
    p = Path(name_or_path)
    cand = [
        base / "app" / "assets" / p.name,
        base / "assets" / p.name,
        p if p.is_absolute() else base / p,
    ]
    seen: set[Path] = set()
    uniq: list[Path] = []
    for c in cand:
        if c not in seen:
            uniq.append(c)
            seen.add(c)
    return uniq


@st.cache_data(show_spinner=False)
def _read_image_b64(p: Path) -> str:
    return b64encode(p.read_bytes()).decode("ascii")


def set_sidebar_background(image: str = "sidebar_bg.png") -> None:
    """Set sidebar background image from assets folder."""
    tried = _candidate_paths(image)
    img_path = next((p for p in tried if p.exists()), None)
    if not img_path:
        tried_str = "\n - " + "\n - ".join(str(p) for p in tried)
        st.warning(f"Sidebar background not found. Tried:{tried_str}")
        return

    b64 = _read_image_b64(img_path)
    css = f"""
    <style>
      section[data-testid="stSidebar"] {{
        background:
          linear-gradient(180deg, var(--bg-page), var(--bg-card)),
          url("data:image/png;base64,{b64}");
        background-size: cover;
      }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
