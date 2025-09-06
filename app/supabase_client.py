# supa.py
from supabase import create_client, Client

SUPABASE_URL: str = "https://gqiaicnmnoxmqwbeyflp.supabase.co"
SUPABASE_ANON_KEY: str = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxaWFpY25tbm94bXF3YmV5ZmxwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxNDU4NzcsImV4cCI6MjA3MjcyMTg3N30."
    "xHFQfCVCX5VhaZgOpRvXLWMHJ3x4huYFubF-CjQxw8U"
)

def get_client() -> Client:
    """Palauttaa Supabase clientin ANON-avaimella"""
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Testi että toimii
if __name__ == "__main__":
    supabase = get_client()
    try:
        res = supabase.table("players").select("*").limit(5).execute()
        print("✅ Supabase-yhteys toimii. Esimerkkidata:")
        print(res.data)
    except Exception as e:
        print("❌ Virhe Supabase-yhteydessä:", e)
