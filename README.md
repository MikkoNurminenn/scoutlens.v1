# ScoutLens

ScoutLens is a Streamlit + Supabase scouting workspace for turning player evaluations, reports, notes, and supporting workflow data into one usable football scouting tool.

## What this project is

The codebase is focused on scouting operations rather than just data storage. It brings together:

- player records
- scouting reports
- notes
- match and planning data
- export tooling
- a reports-first product refactor that keeps the workflow moving toward a clearer MVP

The repository also contains tests, UI hardening work, and migration files that support ongoing product cleanup.

## Stack

- Python
- Streamlit
- Supabase / PostgREST
- pytest

## Current direction

ScoutLens is being tightened into a reports-first scouting workflow:

- add or search a player
- write and save a scouting report
- organize work through shortlists
- review notes, supporting data, and exports from one place

That makes the repository more product-oriented than notebook-oriented, even though data remains central to the workflow.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/app.py
```

Run the current test suite with:

```bash
pytest -q
```

## Supabase setup

Configure a `[supabase]` block in `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://<project>.supabase.co"
anon_key = "<public-anon-key>"
```

For admin-only sync tasks that need elevated access, use `scripts/supabase_admin_sync.py` outside the Streamlit runtime with environment variables.

## Why this repo stays public

ScoutLens represents the product side of the portfolio: a domain-specific workflow tool with active refactoring, UI hardening, and real application structure rather than a single one-off script.
