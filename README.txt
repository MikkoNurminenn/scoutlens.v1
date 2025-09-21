# ScoutLens

## Running

From the project root run:

    streamlit run app/app.py

You can verify the package imports with:

    python -c "import app; print('ok')"

### Supabase Sync

Configure a `[supabase]` block in your Streamlit secrets to enable optional Supabase storage. Functions in `app/sync_utils.py` and `app/teams_store.py` will then read data (and write when an authenticated session is active) to your Supabase tables.

#### Developer Setup

1. Create a project at [Supabase](https://supabase.com) and copy the API URL and keys from the dashboard.
2. Create a storage bucket (for example, `data`) for JSON files.
3. Add the credentials to `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://<project>.supabase.co"
anon_key = "<public-anon-key>"
```

`app/sync_utils.py` now reuses the shared anon Supabase client and will only perform writes when the current Streamlit session has authenticated through Supabase Auth. Reads continue to work for public tables. For admin/CLI tasks that require the service role key, use `scripts/supabase_admin_sync.py` outside the Streamlit runtime:

```bash
export SUPABASE_URL="https://<project>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<private-service-role-key>"

python scripts/supabase_admin_sync.py pull players ./backup/players.json
python scripts/supabase_admin_sync.py push players ./backup/players.json
```

Replace `players` with the target table name and adjust file paths as needed.

## Migrations

- `006_shortlists_refactor.sql` drops `player_ids` from `public.shortlists` and adds a normalized `public.shortlist_items` table with a unique `(shortlist_id, player_id)` constraint.
