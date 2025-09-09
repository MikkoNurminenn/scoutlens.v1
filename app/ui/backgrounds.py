from __future__ import annotations
import base64
from pathlib import Path
import sys


def _resource_path(relative: str) -> Path:
    """
    Return absolute path for assets that works in:
    - normal source run
    - PyInstaller (sys._MEIPASS)
    Assets live in app/assets/
    """
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parents[1]  # .../app
    return (base / "assets" / relative).resolve()


def _b64_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def inject_login_background(st, image_name: str = "login_bg.png") -> None:
    """
    iOS-compatible full-screen background.
    Use ONLY on the Login view.
    """
    img_path = _resource_path(image_name)
    if not img_path.exists():
        st.warning(f"Background image not found: {img_path}")
        return

    b64 = _b64_image(img_path)

    st.markdown(
        f"""
        <style>
        /* Fixed background layer (iOS-safe: no background-attachment) */
        #scoutlens-bg {{
            position: fixed;
            inset: 0;
            z-index: 0;
            background-image: url("data:image/png;base64,{b64}");
            background-position: center center;
            background-repeat: no-repeat;
            background-size: cover;
        }}

        /* Ensure app content sits above and stays transparent */
        [data-testid="stAppViewContainer"] > .main {{
            position: relative;
            z-index: 1;
            background: transparent !important;
        }}

        /* Optional: cleaner header on Login */
        [data-testid="stHeader"] {{ background: transparent; }}

        /* Readable login card on top of image */
        .scoutlens-login-card {{
            background: rgba(0,0,0,0.55);
            backdrop-filter: blur(4px);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.35);
        }}
        </style>
        <div id="scoutlens-bg" aria-hidden="true"></div>
        """,
        unsafe_allow_html=True,
    )

