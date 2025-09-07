
PLAYER AGE-MINUTES TOOL

1. Open 'players.csv' in Excel or Notepad
2. Edit or add player data (Name, Age, Position, etc.)
3. Save the file
4. Double-click 'start_tool.bat' to open the dashboard in your browser

Make sure Python and Streamlit are installed.
If needed, install Streamlit with:
    pip install streamlit

### Supabase Sync

Configure a `[supabase]` block in your Streamlit secrets to enable optional
Supabase storage. Functions in `app/sync_utils.py` and `app/teams_store.py`
will then read and write data to your Supabase tables.

#### Developer Setup

1. Create a project at [Supabase](https://supabase.com) and copy the API URL
   and keys from the dashboard.
2. Create a storage bucket (for example, `data`) for JSON files.
3. Add the credentials to `.streamlit/secrets.toml`:

   ```toml
   [supabase]
   url = "https://<project>.supabase.co"
   anon_key = "<public-anon-key>"
   service_role = "<service-role-key>"  # optional, for sync_utils only
   ```

The application reads and writes JSON data to Supabase storage through
`app/sync_utils.py`. Example usage of the utilities:

```bash
python - <<'PY'
from pathlib import Path
from sync_utils import push_json, pull_json

push_json('data', 'players.json', Path('local_players.json'))
pull_json('data', 'players.json', Path('downloaded_players.json'))
PY
```

Replace `'data'` with your bucket name and adjust file paths as needed.

