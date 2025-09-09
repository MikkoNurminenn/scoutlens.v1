from __future__ import annotations
import base64
from pathlib import Path
import sys


def _resource_path(relative: str) -> Path:
    """Return absolute Path for asset that works in dev, Cloud, PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parents[1]
    return (base / "assets" / relative).resolve()


def _b64_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def inject_login_background_css(st, image_name: str = "login_bg.png") -> None:
    """Inject CSS to set full-screen background for Login view."""
    img_path = _resource_path(image_name)
    if not img_path.exists():
        st.warning(f"Background image not found: {img_path}")
        return

    b64 = _b64_image(img_path)
    css = f"""
    <style>
    .stApp {{
        background: url("data:image/png;base64,{b64}") no-repeat center center fixed;
        background-size: cover;
    }}

    .block-container {{
        background: transparent !important;
    }}

    .scoutlens-login-card {{
        background: rgba(0,0,0,0.55);
        backdrop-filter: blur(4px);
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    }}

    .stButton > button,
    .stTextInput > div > div > input,
    .stSelectbox,
    .stRadio {{
        position: relative;
        z-index: 2;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
