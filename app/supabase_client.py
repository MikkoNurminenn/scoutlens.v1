from supabase import create_client
import streamlit as st

_client = None

def get_client():
    global _client
    if _client is not None:
        return _client

    try:
        url = st.secrets["supabase"]["url"]
        anon_key = st.secrets["supabase"]["anon_key"]
    except Exception:
        st.error("Supabase secrets missing. Please add [supabase] block with url + anon_key in Secrets.")
        st.stop()

    _client = create_client(url, anon_key)
    return _client
