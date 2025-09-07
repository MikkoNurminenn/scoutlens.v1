# Task: Refactor ScoutLens to a Reports-First MVP (remove Teams, simplify to Shortlists + Reports)

## Goal

Make ScoutLens laser-focused on **creating and saving scouting reports**. Remove the separate **Teams** feature and any duplicate grouping logic. Use **Shortlists** as the single way to organize players. Keep Supabase as the only data store.

## High-Level Changes

1. **Remove/disable “Teams”** UI, code paths, and dependencies.
2. **Keep only “Shortlists”** as grouping. Each player row shows `current_club`, so Team pages are redundant.
3. **Reports are the core flow**: add player → write report → save → view reports. Make this reachable in 1–2 clicks.
4. **Supabase-only data** (no JSON/SQLite fallbacks) using credentials from `st.secrets["supabase"]`.

---

## Navigation (Streamlit)

Replace current nav with two pages only:

* **Reports** (default landing)
* **Players / Shortlists**

Optional 3rd minimalist page:

* **Export** (CSV/PDF)

Remove/hide: Team View, extra analytics pages, any JSON-backed legacy screens.

---

## Data Model (Supabase)

Use only Supabase tables (PostgREST). Migrate if needed.

```sql
-- players
create table if not exists public.players (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  position text,
  preferred_foot text,
  nationality text,
  current_club text,      -- replaces “Teams” need
  date_of_birth date,
  transfermarkt_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- shortlists
create table if not exists public.shortlists (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

-- shortlist_items (many-to-many between shortlists and players)
create table if not exists public.shortlist_items (
  id uuid primary key default gen_random_uuid(),
  shortlist_id uuid not null references public.shortlists(id) on delete cascade,
  player_id uuid not null references public.players(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (shortlist_id, player_id)
);

-- reports (core)
create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  player_id uuid not null references public.players(id) on delete cascade,
  report_date date not null default (now() at time zone 'utc')::date,
  competition text,
  opponent text,
  location text,            -- stadium/city
  position_played text,
  minutes int,
  rating numeric(3,1),      -- 0.0 - 10.0 style
  strengths text,
  weaknesses text,
  notes text,
  scout_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

> If a `teams` table or “team_*� code exists, mark it **deprecated** and delete its UI usage.

---

## Secrets / Client

Use Streamlit secrets (already in project):

```toml
# .streamlit/secrets.toml
[supabase]
url = "https://gqiaicnmnoxmqwbeyflp.supabase.co"
anon_key = "<KEEP FROM SECRETS>"
```

Python client:

```python
# supabase_client.py
from supabase import create_client
import streamlit as st

_client = None

def get_client():
    global _client
    if _client is None:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
        _client = create_client(url, key)
    return _client
```

---

## Pages & Core Flows

### 1) Reports (default page)

* **Top bar**: Quick player picker (search by name; if not found → “+ New Player” inline).
* **Primary CTA**: “New Report” opens a single form:

  * Player (pre-filled from picker)
  * Report date (default = today)
  * Competition, Opponent, Location
  * Position played, Minutes
  * Rating (0–10)
  * Strengths, Weaknesses, Notes (multiline)
  * Scout name (text or prefilled from session)
  * **Save** → insert into `public.reports`
* **Below form**: Recent reports table (sortable, filter by player/competition/date).
* **Actions**:

  * View report
  * Edit report
  * Delete report (confirm dialog)

**Query patterns**:

```python
# List latest 50 reports
sb.table("reports").select(
    "id,report_date,competition,opponent,position_played,rating,player:player_id(name,current_club)"
).order("report_date", desc=True).limit(50).execute()
```

### 2) Players / Shortlists

* **Left column**: Shortlist selector (multiselect or dropdown), buttons: “+ New Shortlist”, “Rename”, “Delete”.
* **Right column**: Table of players in the selected shortlist(s) with columns:

  * Name | Position | Current Club | Nationality | ReportsCount
  * Actions: “New Report”, “View Reports”, “Edit Player”
* **Add Player** dialog (inline) with minimal fields: `name`, `position`, `preferred_foot`, `nationality`, `current_club`, `transfermarkt_url`.
* **Add/Remove from shortlist** contextual buttons.

**Query patterns**:

```python
# List players in a shortlist
sb.table("shortlist_items").select(
  "id, player:player_id(id,name,position,current_club,nationality)"
).eq("shortlist_id", shortlist_id).execute()
```

### 3) Export (CSV/PDF)

* **CSV**: Export `reports` joined with `players` (name/current_club) as a downloadable CSV.
* **PDF (optional MVP)**: Simple per-report PDF using `reportlab` or HTML → PDF (if already present); otherwise skip and leave TODO.

---

## Deleting Teams (code & UI)

* Remove pages: `team_view.py`, `teams_store.py`, any “Teams” menu item.
* Remove imports/usages in `app.py` router.
* Delete helper functions referencing teams; replace with shortlist filters (or player `current_club` string filters).
* If any tests reference teams, update to shortlists.

---

## Component/Helper Updates

#### Player picker (shared)

* Search by `name ILIKE` and optionally `current_club`.
* If no match → “Create player” inline; on save, returns new `player_id`.

#### Report editor

* Use a single `st.form` with validation:

  * required: player_id, report_date, rating
  * rating bounds: 0.0–10.0 (step 0.1)
* Insert/Update via Supabase; show success toast and refresh list.

#### Shortlist management

* CRUD for `shortlists` and `shortlist_items`.
* Prevent duplicates via unique(shortlist_id, player_id).

---

## Supabase Queries (Python examples)

```python
from app.supabase_client import get_client
sb = get_client()

def list_reports(limit=50):
    return sb.table("reports").select(
        "id,report_date,competition,opponent,position_played,rating,"
        "player:player_id(name,current_club)"
    ).order("report_date", desc=True).limit(limit).execute().data

def create_report(payload: dict):
    # payload includes player_id, report_date, etc.
    return sb.table("reports").insert(payload).execute()

def upsert_player(p: dict):
    # Upsert by (name, date_of_birth) if desired; MVP can just insert.
    return sb.table("players").insert(p).execute()

def list_players_by_shortlist(shortlist_id: str):
    return sb.table("shortlist_items").select(
        "player:player_id(id,name,position,current_club,nationality)"
    ).eq("shortlist_id", shortlist_id).execute().data
```

---

## UI Polish (minimal, practical)

* Use consistent Streamlit keys (prefix `reports__`, `players__`).
* Keep tables simple, add a **“New Report”** button on every player row.
* Show **ReportsCount** via a lightweight RPC or a separate query per page load (not per row) to avoid N+1.

---

## Migration / Cleanup

1. **Drop/hide Teams UI:** delete files + router references.
2. **Run SQL** above to ensure tables exist.
3. **Remove JSON/SQLite artifacts** related to Teams; ensure no local writes for core paths.
4. **Secrets:** ensure `[supabase]` block is present; fail fast with clear `st.error` if missing.
5. **Feature flags:** If needed, a `USE_TEAMS=False` constant to quickly guard old code paths until removed.

---

## Acceptance Criteria

* [ ] App launches to **Reports** page by default.
* [ ] “New Report” flow from landing works in ≤2 clicks (pick/create player → save report).
* [ ] No **Teams** pages, buttons, or imports exist.
* [ ] Players are organized **only** via Shortlists; adding/removing works and prevents duplicates.
* [ ] Each player row shows **current_club**; no navigation requires a Team page.
* [ ] Reports list shows latest 50 with joined player name & current club; sorting by date works.
* [ ] All data ops use **Supabase**; no local JSON writes for these features.
* [ ] CSV export of reports (+player name/current_club) is available and downloads successfully.
* [ ] Code passes basic lint and no `ModuleNotFoundError`/PostgREST errors in normal use.

---

## Nice-to-Have (if quick)

* [ ] Inline “Create Player” from Reports page (modal) and auto-return to report form with selected player.
* [ ] Simple filter chips on Reports: player, competition, date range.
* [ ] Confirm dialog on report delete.

---

## Notes

* Do **not** reintroduce Team concept; filtering by `current_club` is enough if needed.
* Keep latency low: prefer `order("report_date", desc=True).limit(50)`.
* Use UTC dates in DB; allow local selection in UI if needed later.

---

If anything blocks you (e.g., missing secrets), show a clear error in the UI:

> “Supabase secrets missing. Add `[supabase].url` and `[supabase].anon_key` to `.streamlit/secrets.toml`.”

---
