# app/supabase_client.py
from __future__ import annotations
import os
from functools import lru_cache

def _get_secret(name: str):
    """Yritä lukea Streamlit-secreti tai palauta None ilman virheitä."""
    try:
        import streamlit as st  # vältetään kovaa riippuvuutta jos ajetaan testeissä
        return st.secrets.get(name)
    except Exception:
        return None

@lru_cache(maxsize=1)
def get_client():
    """
    Palauttaa Supabase-clientin tai None, jos konffi/riippuvuudet puuttuvat.
    Älä kaada sovellusta: UI pystyy tällöin näyttämään 'offline' –tilan.
    """
    url = os.getenv("SUPABASE_URL") or _get_secret("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY") or _get_secret("SUPABASE_ANON_KEY")
    if not url or not key:
        return None

    # Python-clientin import voi puuttua build-ympäristössä -> palauta None
    try:
        from supabase import create_client  # pip: supabase
    except Exception:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None

def is_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") or _get_secret("SUPABASE_URL")) and \
           bool(os.getenv("SUPABASE_ANON_KEY") or _get_secret("SUPABASE_ANON_KEY"))
