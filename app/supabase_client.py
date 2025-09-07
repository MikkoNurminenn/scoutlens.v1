from typing import Optional
import os
import streamlit as st
from supabase import create_client, Client

_CACHE: Optional[Client] = None

def get_client() -> Client:
    global _CACHE
    if _CACHE:
        return _CACHE
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"].get("anon_key") or os.environ["SUPABASE_ANON_KEY"]
    _CACHE = create_client(url, key)
    return _CACHE
