# app/pages/calendar_local.py
# Streamlit calendar for football scouting – local JSON storage (no Supabase)

from __future__ import annotations

import json
import tempfile
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import quote_plus

import streamlit as st
from zoneinfo import ZoneInfo

try:
    from streamlit_calendar import calendar as third_party_calendar
except ModuleNotFoundError:  # pragma: no cover
    third_party_calendar = None  # type: ignore[assignment]

# ---- Storage config ----
DATA_DIR = Path("data")
MATCHES_PATH = DATA_DIR / "matches.json"
TARGETS_PATH = DATA_DIR / "match_targets.json"  # optional; may be empty

DEFAULT_MATCH_LENGTH_MINUTES = 120
SELECTBOX_KEY = "calendar_selected_event_id"


# ---- FS helpers ----
def _ensure_data_dir() -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # why: surface FS issues early
        st.error(f"Failed to create data directory: {DATA_DIR} ({exc})")


def _read_json_or_default(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default  # why: corrupted file should not break the app


def _write_json_atomic(path: Path, data: Any) -> None:
    # why: atomic rename prevents partial writes
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with open(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        Path(tmp_name).replace(path)
    except Exception as exc:
        st.error(f"Saving failed for {path.name}: {exc}")


# ---- Timezone & parsing helpers (unchanged) ----
def _ensure_timezone(dt: datetime | None, tz_name: str | None) -> datetime | None:
    if dt is None:
        return None
    tz = None
    if tz_name:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:  # pragma: no cover
            tz = None
    if tz is None:
        return dt
    return dt.astimezone(tz)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("UTC"))


# ---- Domain transforms (unchanged) ----
def _build_google_maps_url(match: Dict[str, Any]) -> str | None:
    for key in ("venue", "stadium", "location"):
        value = match.get(key)
        if isinstance(value, str) and value.strip():
            query = quote_plus(value.strip())
            return f"https://www.google.com/maps/search/?api=1&query={query}"
    return None


def _match_to_event(match: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]] | None:
    kickoff_utc = _parse_datetime(match.get("kickoff_at"))
    if kickoff_utc is None:
        return None

    tz_name = match.get("tz_name") or match.get("timezone") or "UTC"
    kickoff_local = _ensure_timezone(kickoff_utc, tz_name) or kickoff_utc

    ends_at = _parse_datetime(match.get("ends_at_utc"))
    if ends_at is None:
        ends_at = kickoff_utc + timedelta(minutes=DEFAULT_MATCH_LENGTH_MINUTES)
    end_local = _ensure_timezone(ends_at, tz_name) or ends_at

    title_parts = [match.get("home_team") or "", match.get("away_team") or ""]
    title = " vs ".join(part for part in title_parts if part) or "Match"

    event_id = match.get("id") or f"match-{kickoff_utc.isoformat()}"
    match_id = match.get("id")

    maps_url = _build_google_maps_url(match)

    event = {
        "id": event_id,
        "title": title,
        "start": kickoff_local.replace(microsecond=0).isoformat(),
        "end": end_local.replace(microsecond=0).isoformat(),
        "allDay": False,
        "extendedProps": {
            "match_id": match_id,
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
            "location": match.get("location"),
            "competition": match.get("competition"),
            "tz_name": tz_name,
            "kickoff_utc": kickoff_utc.isoformat(),
            "kickoff_local": kickoff_local.isoformat(),
            "google_maps_url": maps_url,
        },
    }

    metadata = {
        "event_id": event_id,
        "match_id": match_id,
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "location": match.get("location"),
        "venue": match.get("venue"),
        "competition": match.get("competition"),
        "kickoff_local": kickoff_local,
        "kickoff_utc": kickoff_utc,
        "tz_name": tz_name,
        "notes": match.get("notes"),
        "google_maps_url": maps_url,
    }
    return event, metadata


# ---- Local data access layer (replaces Supabase) ----
@st.cache_data(ttl=60, show_spinner=False)
def _load_match_targets(match_ids: Tuple[str, ...]) -> Dict[str, List[Dict[str, Any]]]:
    ids = tuple(sorted({mid for mid in match_ids if mid}))
    if not ids:
        return {}
    _ensure_data_dir()
    raw = _read_json_or_default(TARGETS_PATH, default=[])
    # expected structure (optional):
    # [{"match_id": "id", "player_id": "p1", "name": "...", "position": "...", "current_club": "..."}]
    targets: Dict[str, List[Dict[str, Any]]] = {}
    for row in raw if isinstance(raw, list) else []:
        match_id = row.get("match_id")
        if not match_id or match_id not in ids:
            continue
        entry = {
            "player_id": row.get("player_id"),
            "name": row.get("name"),
            "position": row.get("position"),
            "current_club": row.get("current_club"),
        }
        targets.setdefault(match_id, []).append(entry)
    return targets


@st.cache_data(ttl=60, show_spinner=False)
def _load_matches() -> List[Dict[str, Any]]:
    """Load matches from local JSON ordered by kickoff time (descending)."""
    _ensure_data_dir()
    rows = _read_json_or_default(MATCHES_PATH, default=[])
    if not isinstance(rows, list):
        return []
    cleaned = [row for row in rows if isinstance(row, dict)]
    # sort desc by kickoff_at
    def _key(m: Dict[str, Any]) -> float:
        dt = _parse_datetime(m.get("kickoff_at"))
        return -(dt.timestamp() if dt else 0.0)
    return sorted(cleaned, key=_key)


def insert_match_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a new match into local JSON and return the created row."""
    _ensure_data_dir()
    rows = _read_json_or_default(MATCHES_PATH, default=[])
    if not isinstance(rows, list):
        rows = []
    new_row = dict(payload)
    new_row["id"] = uuid.uuid4().hex
    rows.append(new_row)
    _write_json_atomic(MATCHES_PATH, rows)
    return new_row


# ---- UI helpers (unchanged) ----
def _format_match_label(metadata: Dict[str, Any]) -> str:
    home = metadata.get("home_team") or "?"
    away = metadata.get("away_team") or "?"
    kickoff_local = metadata.get("kickoff_local")
    if isinstance(kickoff_local, datetime):
        ts = kickoff_local.strftime("%Y-%m-%d %H:%M")
        tz_name = metadata.get("tz_name") or "UTC"
        return f"{home} vs {away} — {ts} ({tz_name})"
    return f"{home} vs {away}"


def _build_event_description(metadata: Dict[str, Any]) -> str:
    parts: List[str] = []
    kickoff_local = metadata.get("kickoff_local")
    if isinstance(kickoff_local, datetime):
        tz_name = metadata.get("tz_name") or "UTC"
        parts.append(kickoff_local.strftime("%Y-%m-%d %H:%M") + f" ({tz_name})")
    location = metadata.get("location") or metadata.get("venue")
    if isinstance(location, str) and location.strip():
        parts.append(location.strip())
    targets = metadata.get("targets") or []
    if targets:
        names = [t.get("name") for t in targets if t.get("name")]
        if names:
            parts.append("Targets: " + ", ".join(names))
    return " • ".join(parts)


def _render_native_calendar(
    events: List[Dict[str, Any]], metadata_map: Dict[str, Dict[str, Any]]
) -> str | None:
    native_events: List[Dict[str, Any]] = []
    for event in events:
        start_val = event.get("start")
        end_val = event.get("end") or start_val
        try:
            start_dt = datetime.fromisoformat(str(start_val)) if not isinstance(start_val, datetime) else start_val
            end_dt = datetime.fromisoformat(str(end_val)) if not isinstance(end_val, datetime) else end_val
        except ValueError:
            continue
        event_id = event.get("id")
        native_events.append(
            {
                "id": event_id,
                "title": event.get("title"),
                "start": start_dt,
                "end": end_dt,
                "all_day": bool(event.get("allDay")),
                "description": _build_event_description(metadata_map.get(event_id, {})),
            }
        )

    selected = None
    try:
        calendar_state = st.calendar("Match calendar", events=native_events, key="match_calendar_native")
    except TypeError:
        calendar_state = st.calendar(events=native_events, key="match_calendar_native")

    if isinstance(calendar_state, dict):
        selected = (
            calendar_state.get("id")
            or calendar_state.get("event_id")
            or (calendar_state.get("event") or {}).get("id")
        )
    elif isinstance(calendar_state, list) and calendar_state:
        candidate = calendar_state[-1]
        if isinstance(candidate, dict):
            selected = candidate.get("id") or candidate.get("event_id")
    return selected if isinstance(selected, str) else None


def _render_third_party_calendar(events: List[Dict[str, Any]]) -> str | None:
    if third_party_calendar is None:
        return None
    options = {
        "initialView": "dayGridMonth",
        "headerToolbar": {"start": "title", "center": "", "end": "dayGridMonth,timeGridWeek,timeGridDay,listWeek"},
        "height": "auto",
        "nowIndicator": True,
        "slotMinTime": "06:00:00",
        "slotMaxTime": "23:00:00",
    }
    calendar_state = third_party_calendar(events=events, options=options, key="match_calendar")
    if isinstance(calendar_state, dict):
        event_payload = calendar_state.get("event")
        if isinstance(event_payload, dict):
            return event_payload.get("id") or (event_payload.get("extendedProps") or {}).get("match_id")
        if calendar_state.get("event_id"):
            return calendar_state.get("event_id")
    return None


# ---- Page ----
def show_calendar_page() -> None:
    st.title("📅 Match calendar")
    st.caption(
        "Review upcoming and past fixtures stored locally (no Supabase). "
        "Kickoff times are shown in local timezone when available."
    )

    _maybe_show_recent_success()
    _render_add_match_form()

    matches = _load_matches()

    events: List[Dict[str, Any]] = []
    metadata_map: Dict[str, Dict[str, Any]] = {}
    match_ids: List[str] = []
    for match in matches:
        converted = _match_to_event(match)
        if not converted:
            continue
        event, metadata = converted
        events.append(event)
        metadata_map[event["id"]] = metadata
        if metadata.get("match_id"):
            match_ids.append(metadata["match_id"])

    targets_map = _load_match_targets(tuple(match_ids))
    for meta in metadata_map.values():
        match_id = meta.get("match_id")
        meta["targets"] = targets_map.get(match_id, [])

    selected_event_id = None
    default_selected_id = st.session_state.get(SELECTBOX_KEY)

    if hasattr(st, "calendar"):
        selected_event_id = _render_native_calendar(events, metadata_map)
    else:
        selected_event_id = _render_third_party_calendar(events)
        if selected_event_id is None and third_party_calendar is None:
            st.error(
                "No calendar component is available. Update Streamlit to include `st.calendar` "
                "or install the `streamlit-calendar` package."
            )

    if not events:
        st.info("No fixtures scheduled yet. Use the form above to add your first match.")

    if selected_event_id and selected_event_id in metadata_map:
        st.session_state[SELECTBOX_KEY] = selected_event_id
        default_selected_id = selected_event_id
        st.success(_format_match_label(metadata_map[selected_event_id]))

    st.subheader("Match details")
    detail_ids = list(metadata_map.keys())
    if not detail_ids:
        st.caption("No match metadata available. Add a match to see its details here.")
    else:
        if default_selected_id not in detail_ids:
            default_selected_id = detail_ids[0]
            st.session_state[SELECTBOX_KEY] = default_selected_id

        default_index = detail_ids.index(default_selected_id) if default_selected_id in detail_ids else 0

        selected_id = st.selectbox(
            "Select a match to inspect",
            options=detail_ids,
            format_func=lambda match_id: _format_match_label(metadata_map[match_id]),
            index=default_index,
            key=SELECTBOX_KEY,
        )
        selected = metadata_map.get(selected_id)
        if not selected:
            st.caption("Select a match to see its kickoff details.")
            return

        _render_match_details(selected)

    _render_upcoming_and_past(matches)


# ---- UI sections (unchanged except copy text) ----
def _maybe_show_recent_success() -> None:
    message = st.session_state.pop("calendar_recent_add", None)
    if message:
        st.success(message)


def _render_match_details(selected: Dict[str, Any]) -> None:
    kickoff_local = selected.get("kickoff_local")
    kickoff_utc = selected.get("kickoff_utc")
    tz_name = selected.get("tz_name") or "UTC"
    cols = st.columns(2)
    with cols[0]:
        if isinstance(kickoff_local, datetime):
            st.metric("Local kickoff", kickoff_local.strftime("%Y-%m-%d %H:%M"), help=tz_name)
        else:
            st.metric("Local kickoff", "Unknown")
    with cols[1]:
        if isinstance(kickoff_utc, datetime):
            st.metric("UTC kickoff", kickoff_utc.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M"))
        else:
            st.metric("UTC kickoff", "Unknown")

    st.markdown("### Fixture information")
    location_display = selected.get("location") or selected.get("venue")
    detail_rows = [
        ("Home team", selected.get("home_team")),
        ("Away team", selected.get("away_team")),
        ("Competition", selected.get("competition")),
        ("Location", location_display),
        ("Venue", selected.get("venue")),
        ("Notes", selected.get("notes")),
    ]
    for label, value in detail_rows:
        pretty_value = value if value else "—"
        st.markdown(f"**{label}:** {pretty_value}")

    maps_url = selected.get("google_maps_url")
    if maps_url:
        st.markdown(f"[Open in Google Maps]({maps_url})")

    st.markdown("### Target players")
    targets = selected.get("targets") or []
    if not targets:
        st.caption("No target players are linked to this match yet.")
    else:
        for player in targets:
            name = player.get("name") or "Unnamed player"
            position = player.get("position") or "?"
            club = player.get("current_club")
            subtitle = f"{position}" if position else ""
            if club:
                subtitle = f"{subtitle} • {club}" if subtitle else club
            st.markdown(f"- **{name}**{f' ({subtitle})' if subtitle else ''}")


def _render_upcoming_and_past(matches: List[Dict[str, Any]]) -> None:
    upcoming, past = _split_matches(matches)

    st.markdown("### 📆 Upcoming fixtures")
    if not upcoming:
        st.caption("No upcoming fixtures scheduled.")
    else:
        for kickoff_utc, match in upcoming:
            st.markdown(_format_match_row(match, kickoff_utc))

    st.markdown("### ⏱️ Past fixtures")
    if not past:
        st.caption("No past fixtures recorded yet.")
    else:
        for kickoff_utc, match in past:
            st.markdown(_format_match_row(match, kickoff_utc))


def _split_matches(matches: List[Dict[str, Any]]) -> Tuple[List[Tuple[datetime, Dict[str, Any]]], List[Tuple[datetime, Dict[str, Any]]]]:
    now_utc = datetime.now(ZoneInfo("UTC"))
    upcoming: List[Tuple[datetime, Dict[str, Any]]] = []
    past: List[Tuple[datetime, Dict[str, Any]]] = []
    for match in matches:
        kickoff_utc = _parse_datetime(match.get("kickoff_at"))
        if kickoff_utc is None:
            continue
        if kickoff_utc >= now_utc:
            upcoming.append((kickoff_utc, match))
        else:
            past.append((kickoff_utc, match))

    upcoming.sort(key=lambda item: item[0])
    past.sort(key=lambda item: item[0], reverse=True)
    return upcoming, past


def _format_match_row(match: Dict[str, Any], kickoff_utc: datetime) -> str:
    home = (match.get("home_team") or "").strip() or "?"
    away = (match.get("away_team") or "").strip() or "?"
    tz_name = (match.get("tz_name") or match.get("timezone") or "UTC").strip() or "UTC"
    kickoff_local = _ensure_timezone(kickoff_utc, tz_name) or kickoff_utc
    local_label = kickoff_local.strftime("%Y-%m-%d %H:%M")
    comp = (match.get("competition") or "").strip()
    location = (match.get("location") or match.get("venue") or "").strip()
    parts = [f"**{home} vs {away}**", f"{local_label} ({tz_name})"]
    if comp:
        parts.append(comp)
    if location:
        parts.append(location)
    return " • ".join(parts)


def _render_add_match_form() -> None:
    with st.expander("➕ Add match", expanded=False):
        with st.form("calendar_add_match_form"):
            c1, c2 = st.columns(2)
            home = c1.text_input("Home team", key="calendar_add_home", autocomplete="off")
            away = c2.text_input("Away team", key="calendar_add_away", autocomplete="off")

            now = datetime.now()
            match_date = st.date_input("Match date", now.date(), key="calendar_add_date")
            match_time = st.time_input(
                "Kickoff time",
                now.replace(hour=18, minute=0, second=0, microsecond=0).time(),
                key="calendar_add_time",
            )

            default_tz = st.session_state.get("calendar_last_tz", "UTC")
            tz_name = st.text_input(
                "Timezone (IANA, e.g. Europe/Helsinki)",
                value=default_tz,
                key="calendar_add_tz",
                autocomplete="off",
            )

            c3, c4 = st.columns(2)
            competition = c3.text_input("Competition (optional)", key="calendar_add_comp", autocomplete="off")
            location = c4.text_input("Location (optional)", key="calendar_add_location", autocomplete="off")
            venue = st.text_input("Venue (optional)", key="calendar_add_venue", autocomplete="off")
            notes = st.text_area("Notes (optional)", key="calendar_add_notes")

            submitted = st.form_submit_button("Save match", type="primary")
            if submitted:
                _handle_match_submission(
                    home,
                    away,
                    match_date,
                    match_time,
                    tz_name,
                    competition,
                    location,
                    venue,
                    notes,
                )


def _handle_match_submission(
    home: str,
    away: str,
    match_date: date,
    match_time: time,
    tz_name: str,
    competition: str,
    location: str,
    venue: str,
    notes: str,
) -> None:
    errors: List[str] = []
    home_clean = (home or "").strip()
    away_clean = (away or "").strip()
    if not home_clean:
        errors.append("Home team is required.")
    if not away_clean:
        errors.append("Away team is required.")

    tz_clean = (tz_name or "").strip() or "UTC"
    try:
        tz = ZoneInfo(tz_clean)
    except Exception:
        errors.append("Timezone must be a valid IANA name (e.g. Europe/Helsinki).")
        tz = None

    if errors:
        for msg in errors:
            st.warning(msg)
        return

    kickoff_local = datetime.combine(match_date, match_time)
    kickoff_at = kickoff_local.replace(tzinfo=tz).isoformat() if tz else kickoff_local.isoformat()

    payload = {
        "home_team": home_clean,
        "away_team": away_clean,
        "competition": competition,
        "location": location,
        "venue": venue,
        "notes": notes,
        "kickoff_at": kickoff_at,
        "tz_name": tz_clean,
    }

    try:
        _ = insert_match_local(payload)
    except Exception as exc:  # defensive
        st.error("Unexpected error while saving the match locally.")
        print(f"[calendar_page] Local save error: {exc}")
        return

    st.session_state["calendar_last_tz"] = tz_clean
    st.session_state["calendar_recent_add"] = f"Match {home_clean} vs {away_clean} added."
    _load_matches.clear()
    _load_match_targets.clear()
    st.experimental_rerun()


__all__ = ["show_calendar_page"]
