# app/supabase_client.py
from supabase import create_client
import streamlit as st

def get_client(write: bool = False):
    """
    Luo Supabase client.
    - write=False → käyttää anon_key (SELECT, read-only)
    - write=True  → käyttää service_role_key (INSERT/UPDATE/DELETE)
    """
    url = st.secrets["supabase"]["url"]

    if write:
        key = st.secrets["supabase"]["service_role_key"]
    else:
        key = st.secrets["supabase"]["anon_key"]

    return create_client(url, key)
