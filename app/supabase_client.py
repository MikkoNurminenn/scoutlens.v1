from supabase import create_client
import streamlit as st

_client = None

def get_client():
    """Return a cached Supabase client using anon key only."""
    global _client
    if _client is None:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
        _client = create_client(url, key)
    return _client
