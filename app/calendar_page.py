"""Calendar page rendering match fixtures in an interactive view."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import streamlit as st
from postgrest.exceptions import APIError
from zoneinfo import ZoneInfo

from app.db_tables import MATCHES
from app.supabase_client import get_client

try:
    from streamlit_calendar import calendar
except ModuleNotFoundError:  # pragma: no cover - defensive guard when dependency missing
    calendar = None  # type: ignore[assignment]


DEFAULT_MATCH_LENGTH_MINUTES = 120


def _ensure_timezone(dt: datetime | None, tz_name: str | None) -> datetime | None:
    """Return ``dt`` converted to ``tz_name`` when available."""

    if dt is None:
        return None

    tz = None
    if tz_name:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:  # pragma: no cover - invalid tz names are rare but possible
            tz = None
    if tz is None:
        return dt
    return dt.astimezone(tz)


def _parse_datetime(value: Any) -> datetime | None:
    """Parse ISO8601 values safely, returning timezone-aware datetimes in UTC."""

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


def _match_to_event(match: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]] | None:
    """Transform a match dictionary into a calendar event plus rich metadata."""

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
    title = " vs ".join(part for part in title_parts if part)
    if not title:
        title = "Match"

    event_id = match.get("id") or f"match-{kickoff_utc.isoformat()}"

    event = {
        "id": event_id,
        "title": title,
        "start": kickoff_local.replace(microsecond=0).isoformat(),
        "end": end_local.replace(microsecond=0).isoformat(),
        "allDay": False,
        "extendedProps": {
            "match_id": match.get("id"),
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
            "location": match.get("location"),
            "competition": match.get("competition"),
            "tz_name": tz_name,
            "kickoff_utc": kickoff_utc.isoformat(),
            "kickoff_local": kickoff_local.isoformat(),
        },
    }

    metadata = {
        "event_id": event_id,
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "location": match.get("location"),
        "venue": match.get("venue"),
        "competition": match.get("competition"),
        "kickoff_local": kickoff_local,
        "kickoff_utc": kickoff_utc,
        "tz_name": tz_name,
        "notes": match.get("notes"),
    }

    return event, metadata


@st.cache_data(ttl=60, show_spinner=False)
def _load_matches() -> List[Dict[str, Any]]:
    """Load matches from Supabase ordered by kickoff time (descending)."""

    client = get_client()
    if not client:
        return []

    try:
        response = (
            client.table(MATCHES).select("*").order("kickoff_at", desc=True).execute()
        )
    except APIError as exc:
        st.error("Failed to load matches from Supabase. Please try again later.")
        print(f"[calendar_page] Supabase error: {getattr(exc, 'message', exc)}")
        return []
    except Exception as exc:  # noqa: BLE001 - broad for defensive logging
        st.error("Unexpected error while loading matches.")
        print(f"[calendar_page] Unexpected error: {exc}")
        return []

    rows = response.data or []
    return [row for row in rows if isinstance(row, dict)]


def _format_match_label(metadata: Dict[str, Any]) -> str:
    """Return a readable label for select box entries."""

    home = metadata.get("home_team") or "?"
    away = metadata.get("away_team") or "?"
    kickoff_local = metadata.get("kickoff_local")
    if isinstance(kickoff_local, datetime):
        ts = kickoff_local.strftime("%Y-%m-%d %H:%M")
        tz_name = metadata.get("tz_name") or "UTC"
        return f"{home} vs {away} — {ts} ({tz_name})"
    return f"{home} vs {away}"


SELECTBOX_KEY = "calendar_selected_event_id"


def show_calendar_page() -> None:
    """Render the calendar page inside Streamlit."""

    st.title("📅 Match calendar")
    st.caption(
        "Review upcoming and past fixtures pulled directly from Supabase. "
        "Matches appear in the calendar using their local kickoff time when a timezone is available."
    )

    matches = _load_matches()
    if not matches:
        st.info("No matches found yet. Add matches from the Reports page to populate the calendar.")
        return

    events: List[Dict[str, Any]] = []
    metadata_map: Dict[str, Dict[str, Any]] = {}
    for match in matches:
        converted = _match_to_event(match)
        if not converted:
            continue
        event, metadata = converted
        events.append(event)
        metadata_map[event["id"]] = metadata

    if not events:
        st.info("Matches are missing kickoff times, so there is nothing to plot yet.")
        return

    selected_event_id = None
    default_selected_id = st.session_state.get(SELECTBOX_KEY)

    if calendar is None:
        st.error(
            "The `streamlit-calendar` component is not installed. "
            "Add it to your environment to view the interactive calendar."
        )
    else:
        options = {
            "initialView": "dayGridMonth",
            "headerToolbar": {
                "start": "title",
                "center": "",
                "end": "dayGridMonth,timeGridWeek,timeGridDay,listWeek",
            },
            "height": "auto",
            "nowIndicator": True,
            "slotMinTime": "06:00:00",
            "slotMaxTime": "23:00:00",
        }
        calendar_state = calendar(events=events, options=options, key="match_calendar")
        if isinstance(calendar_state, dict):
            event_payload = calendar_state.get("event")
            if isinstance(event_payload, dict):
                selected_event_id = (
                    event_payload.get("id")
                    or (event_payload.get("extendedProps") or {}).get("match_id")
                )
            if not selected_event_id:
                selected_event_id = calendar_state.get("event_id")
        if selected_event_id and selected_event_id in metadata_map:
            st.session_state[SELECTBOX_KEY] = selected_event_id
            default_selected_id = selected_event_id
            st.success(
                _format_match_label(metadata_map[selected_event_id])
            )

    st.subheader("Match details")
    detail_ids = list(metadata_map.keys())
    if not detail_ids:
        st.caption("No match metadata available.")
        return

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
            st.metric(
                "UTC kickoff",
                kickoff_utc.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M"),
            )
        else:
            st.metric("UTC kickoff", "Unknown")

    st.markdown("### Fixture information")
    for label, value in (
        ("Home team", selected.get("home_team")),
        ("Away team", selected.get("away_team")),
        ("Competition", selected.get("competition")),
        ("Location", selected.get("location")),
        ("Venue", selected.get("venue")),
        ("Notes", selected.get("notes")),
    ):
        pretty_value = value if value else "—"
        st.markdown(f"**{label}:** {pretty_value}")


__all__ = ["show_calendar_page"]
