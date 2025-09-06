# --- generic helpers for JSON files (used by home.py & others) ---
import os, json
from pathlib import Path
import streamlit as st
try:
    from app_paths import file_path, DATA_DIR
except Exception:
    DATA_DIR = Path("./data")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    def file_path(name: str) -> Path:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR / name

# Cloud-indikaattori: totta jos Supabase-secrets on asetettu
IS_CLOUD = bool(st.secrets.get("SUPABASE_URL") or st.secrets.get("SUPABASE_ANON_KEY"))

def load_json(name_or_path, default):
    """Lue JSON (nimi suhteessa DATA_DIRiin tai absoluuttinen polku)."""
    fp = Path(name_or_path)
    if not fp.is_absolute():
        fp = file_path(str(fp))
    try:
        if fp.exists():
            txt = fp.read_text(encoding="utf-8")
            return json.loads(txt) if txt.strip() else default
    except Exception:
        pass
    return default

def save_json(name_or_path, data):
    """Kirjoita JSON (nimi suhteessa DATA_DIRiin tai absoluuttinen polku)."""
    fp = Path(name_or_path)
    if not fp.is_absolute():
        fp = file_path(str(fp))
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
