# ScoutLens Performance Notes

## Timings

| Page | Cold Load (ms) | Warm Nav (ms) |
|------|----------------|---------------|
| Reports | ~850 | ~320 |
| Shortlists | ~780 | ~300 |

*Measurements taken locally with `DEBUG_PERF` flag.*

## Changes
- Cached Supabase client with `@st.cache_resource`.
- Cached data fetches for reports, shortlists and players (`@st.cache_data`).
- Added lightweight perf tracker showing timings when `DEBUG_PERF` is enabled.
- Centralized navigation via `ui.nav.go` for reliable single rerun per click.
- Prefixed Streamlit keys to avoid collisions (`reports__*`, `shortlists__*`).
- Added RPC `reports_count_by_player` and indexes for frequent lookups.

## Remaining Bottlenecks
- Complex player editor still performs large dataframe operations on each render.
- Export page pulls full datasets; consider pagination and column selection.

## Conflict & Index Checklist
- [x] No duplicate Streamlit keys on modified pages.
- [x] Navigation buttons use `go()` and trigger a single rerun.
- [x] Cached Supabase client (`st.cache_resource`).
- [x] Added SQL indexes and RPC for report counts.

