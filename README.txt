
PLAYER AGE-MINUTES TOOL

1. Open 'players.csv' in Excel or Notepad
2. Edit or add player data (Name, Age, Position, etc.)
3. Save the file
4. Double-click 'start_tool.bat' to open the dashboard in your browser

Make sure Python and Streamlit are installed.
If needed, install Streamlit with:
    pip install streamlit

### Supabase Sync

Set `SUPABASE_URL` and `SUPABASE_KEY` environment variables to enable
optional Supabase storage. Functions in `app/sync_utils.py` and
`app/teams_store.py` will then read and write data to your Supabase tables.

#### Developer Setup

1. Create a project at [Supabase](https://supabase.com) and copy the API URL
   and service role or anon key from the dashboard.
2. Create a storage bucket (for example, `data`) for JSON files.
3. Export the required environment variables before running ScoutLens or the
   sync helpers:

   ```bash
   export SUPABASE_URL="https://<project>.supabase.co"
   export SUPABASE_KEY="<service-role-or-anon-key>"
   # Optional: set to 1 to force cloud mode
   export SCOUTLENS_CLOUD=1
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

