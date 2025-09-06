# storage.py
from __future__ import annotations
import os, json
from pathlib import Path
from typing import Any, Optional

# --- secrets helper ---
def _secret(key: str, default=None):
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    import os
    return os.environ.get(key, default)

# --- mode flags ---
MODE     = (_secret("SCOUTLENS_MODE", "local") or "local").lower()  # local | cloud
TENANT   = _secret("SCOUTLENS_TENANT", "default")
IS_CLOUD = (MODE == "cloud")

# Back-compat alias (jos koodissa käytetään 'CLOUD')
CLOUD = IS_CLOUD


# Paikallisessa moodissa käytetään jo olemassa olevaa DATA_DIR:iä
try:
    from app_paths import DATA_DIR
except Exception:
    DATA_DIR = Path.home() / "AppData" / "Roaming" / "ScoutLens"  # varapolku Windowsille
DATA_DIR.mkdir(parents=True, exist_ok=True)

if CLOUD:
    from supabase import create_client, Client
    _sb: Optional[Client] = None

    def _client() -> Client:
        global _sb
        if _sb is None:
            url = _secret("SUPABASE_URL")
            key = _secret("SUPABASE_ANON_KEY")
            if not url or not key:
                raise RuntimeError("SUPABASE_URL / SUPABASE_ANON_KEY puuttuu.")
            _sb = create_client(url, key)
        return _sb

def load_json(name: str, default: Any):
    """
    name: esim. 'players.json', 'matches.json'...
    """
    if not CLOUD:
        fp = DATA_DIR / name
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            return default
    # Cloud
    r = _client().table("kv").select("blob").eq("key", name).maybe_single().execute()
    data = None
    if isinstance(r.data, dict) and "blob" in r.data:
        data = r.data["blob"]
    elif isinstance(r.data, list) and r.data and "blob" in r.data[0]:
        data = r.data[0]["blob"]
    return data if data is not None else default

def save_json(name: str, obj: Any) -> None:
    if not CLOUD:
        (DATA_DIR / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    _client().table("kv").upsert({"key": name, "blob": obj}).execute()
