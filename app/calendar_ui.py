"""Streamlit calendar view backed by Supabase matches + match targets."""

from __future__ import annotations

import importlib
import json
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import quote_plus

import streamlit as st
from dateutil import parser
from postgrest.exceptions import APIError
from zoneinfo import ZoneInfo

from app.supabase_client import get_client
from app.time_utils import LATAM_TZS, utc_iso, to_tz

_calendar_spec = importlib.util.find_spec("streamlit_calendar")
calendar_component = None
if _calendar_spec is not None:
    calendar_component = importlib.import_module("streamlit_calendar").calendar

UTC = ZoneInfo("UTC")
FAR_FUTURE = datetime.max.replace(tzinfo=UTC)
DEFAULT_DURATION_MINUTES = 105
FETCH_WINDOW_DAYS = 60
SIDEBAR_STATE_KEY = "_sidebar_owner_active"
DEBUG_LOG_KEY = "calendar__debug_log"
DEBUG_ENABLED_KEY = "calendar__debug_enabled"


@contextmanager
def _sidebar_owner() -> Iterator[None]:
    """Context manager to mark sidebar ownership for the global guard."""

    prev = bool(st.session_state.get(SIDEBAR_STATE_KEY))
    st.session_state[SIDEBAR_STATE_KEY] = True
    try:
        yield
    finally:
        st.session_state[SIDEBAR_STATE_KEY] = prev


def _clean_str(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _debug_enabled() -> bool:
    return bool(st.session_state.get(DEBUG_ENABLED_KEY))


def _push_debug_event(event: str, *, payload: Optional[Dict[str, Any]] = None) -> None:
    if not _debug_enabled():
        return

    entry: Dict[str, Any] = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "event": event,
    }
    if payload is not None:
        try:
            normalized = json.loads(json.dumps(payload, default=str))
        except TypeError:
            normalized = str(payload)
        entry["payload"] = normalized

    log: List[Dict[str, Any]] = st.session_state.get(DEBUG_LOG_KEY, []) or []
    log.append(entry)
    st.session_state[DEBUG_LOG_KEY] = log[-50:]


def _render_debug_helpers() -> None:
    debug_default = bool(st.session_state.get(DEBUG_ENABLED_KEY))
    with st.expander("🐞 Debug helpers", expanded=debug_default):
        debug_enabled = st.checkbox(
            "Enable calendar debug logging",
            value=debug_default,
            key="calendar__debug_toggle",
        )
        st.session_state[DEBUG_ENABLED_KEY] = debug_enabled

        log: List[Dict[str, Any]] = st.session_state.get(DEBUG_LOG_KEY, []) or []
        if debug_enabled:
            if log:
                st.caption("Recent calendar events (most recent last):")
                st.json(log)
            else:
                st.caption("Debug logging is enabled. Interact with the calendar to collect events.")

        if st.button("Clear debug log", disabled=not log):
            st.session_state[DEBUG_LOG_KEY] = []


def _parse_iso(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = parser.isoparse(str(value))
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _event_datetime(event: Dict[str, Any], field: str) -> Optional[datetime]:
    if not isinstance(event, dict):
        return None
    raw = event.get(field)
    if raw is None and field in {"start", "end"}:
        raw = event.get(f"{field}Str")
    return _parse_iso(raw)


def _iso_from_row(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return utc_iso(value)
    parsed = _parse_iso(value)
    if parsed is None:
        return None
    return utc_iso(parsed)


def _event_color(row: Dict[str, Any]) -> str:
    if row.get("shortlist_id"):
        return "#3b82f6"  # blue
    if not row.get("home_team") or not row.get("away_team"):
        return "#ef4444"  # red
    return "#22c55e"  # green


def _match_to_event(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    start_iso = _iso_from_row(row.get("kickoff_at"))
    if not start_iso:
        return None
    end_iso = _iso_from_row(row.get("ends_at_utc"))
    if not end_iso:
        start_dt = _parse_iso(row.get("kickoff_at"))
        if start_dt is not None:
            end_iso = utc_iso(start_dt + timedelta(minutes=DEFAULT_DURATION_MINUTES))

    title = f"{row.get('home_team') or '—'} vs {row.get('away_team') or '—'}"
    if row.get("competition"):
        title = f"{title} · {row['competition']}"

    return {
        "id": row.get("id"),
        "title": title,
        "start": start_iso,
        "end": end_iso,
        "allDay": False,
        "backgroundColor": _event_color(row),
        "borderColor": "#111827",
        "extendedProps": {
            "tz_name": row.get("tz_name"),
            "venue": row.get("venue") or row.get("location"),
            "country": row.get("country"),
        },
    }


def _warn_api_error(prefix: str, error: APIError) -> None:
    message = getattr(error, "message", None) or str(error)
    _push_debug_event(
        "api_error",
        payload={"prefix": prefix, "message": message},
    )
    st.error(f"{prefix}: {message}")


def _kickoff_sort_key(row: Dict[str, Any]) -> datetime:
    dt = _parse_iso(row.get("kickoff_at"))
    if dt is None:
        return FAR_FUTURE
    return dt.astimezone(UTC)


def _load_matches() -> List[Dict[str, Any]]:
    sb = get_client()
    now_utc = datetime.now(tz=UTC)
    until_utc = now_utc + timedelta(days=FETCH_WINDOW_DAYS)

    try:
        res = (
            sb.table("matches")
            .select(
                "id,home_team,away_team,competition,venue,country,tz_name,kickoff_at,ends_at_utc,notes,location"
            )
            .gte("kickoff_at", utc_iso(now_utc))
            .lte("kickoff_at", utc_iso(until_utc))
            .order("kickoff_at", desc=True)
            .limit(1000)
            .execute()
        )
    except APIError as exc:
        _warn_api_error("Failed to load matches", exc)
        return []

    rows = res.data or []
    rows.sort(key=_kickoff_sort_key)
    return rows


def _load_players() -> List[Dict[str, Any]]:
    try:
        res = (
            get_client()
            .table("players")
            .select("id,name,current_club")
            .order("name")
            .limit(1000)
            .execute()
        )
        return res.data or []
    except APIError as exc:
        _warn_api_error("Failed to load players", exc)
        return []


def _load_match(match_id: str) -> Optional[Dict[str, Any]]:
    try:
        res = (
            get_client()
            .table("matches")
            .select(
                "id,home_team,away_team,competition,venue,country,tz_name,kickoff_at,ends_at_utc,notes,location,match_targets(player_id)"
            )
            .eq("id", match_id)
            .single()
            .execute()
        )
    except APIError as exc:
        _warn_api_error("Failed to load match", exc)
        return None

    data = res.data or {}
    targets = data.pop("match_targets", []) or []
    data["targets"] = [
        t.get("player_id")
        for t in targets
        if isinstance(t, dict) and t.get("player_id")
    ]
    return data


def _load_match_targets(match_id: str) -> List[str]:
    try:
        res = (
            get_client()
            .table("match_targets")
            .select("player_id")
            .eq("match_id", match_id)
            .execute()
        )
        rows = res.data or []
        return [r.get("player_id") for r in rows if r.get("player_id")]
    except APIError as exc:
        _warn_api_error("Failed to load match targets", exc)
        return []


def _sync_targets(match_id: str, desired: List[str], existing: List[str]) -> None:
    sb = get_client()
    desired_ids = {pid for pid in desired if pid}
    existing_ids = {pid for pid in existing if pid}

    to_add = desired_ids - existing_ids
    to_remove = existing_ids - desired_ids

    if to_add:
        rows = [
            {"match_id": match_id, "player_id": pid}
            for pid in sorted(to_add)
        ]
        try:
            sb.table("match_targets").insert(rows).execute()
        except APIError as exc:
            _warn_api_error("Failed to add match targets", exc)

    for pid in to_remove:
        try:
            sb.table("match_targets").delete().eq("match_id", match_id).eq("player_id", pid).execute()
        except APIError as exc:
            _warn_api_error("Failed to remove match target", exc)


def _maps_search_url(*parts: Optional[str]) -> Optional[str]:
    values = [str(p).strip() for p in parts if p and str(p).strip()]
    if not values:
        return None
    query = ", ".join(values)
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def _kickoff_details(match: Dict[str, Any]) -> str:
    kickoff = match.get("kickoff_at")
    tz_name = match.get("tz_name") or "UTC"
    dt = _parse_iso(kickoff)
    if not dt:
        return "—"
    try:
        local = to_tz(dt, tz_name)
    except Exception:
        local = dt
    return f"{local.strftime('%Y-%m-%d %H:%M')} ({tz_name})"


def _render_new_match_form(selection: Optional[Dict[str, Any]] = None) -> None:
    selection = selection or {}
    start_raw = selection.get("start")
    end_raw = selection.get("end")
    try:
        start_dt = parser.isoparse(start_raw) if start_raw else None
    except (TypeError, ValueError):
        start_dt = None
    try:
        end_dt = parser.isoparse(end_raw) if end_raw else None
    except (TypeError, ValueError):
        end_dt = None

    tz_options = list(LATAM_TZS)
    default_tz = st.session_state.get("calendar__tz", tz_options[0])
    if default_tz not in tz_options:
        default_tz = tz_options[0]

    selection_token = f"{start_raw}|{end_raw}" if (start_raw or end_raw) else "manual"

    _push_debug_event(
        "open_new_match_form",
        payload={
            "selection": {
                "start": start_raw,
                "end": end_raw,
            },
            "selection_token": selection_token,
        },
    )

    with _sidebar_owner():
        with st.sidebar:
            st.subheader("➕ New match")
            home = st.text_input("Home team", key="calendar__new_home")
            away = st.text_input("Away team", key="calendar__new_away")
            competition = st.text_input("Competition", key="calendar__new_comp")
            venue = st.text_input("Venue (stadium/city)", key="calendar__new_venue")
            country = st.text_input("Country", key="calendar__new_country")
            tz_name = st.selectbox(
                "Match timezone",
                tz_options,
                index=tz_options.index(default_tz),
                key="calendar__new_tz",
            )
            notes = st.text_area("Notes", key="calendar__new_notes")

            try:
                tzinfo = ZoneInfo(tz_name)
            except Exception:
                tzinfo = UTC
                tz_name = "UTC"

            if isinstance(start_dt, datetime):
                if start_dt.tzinfo is None:
                    start_local_dt = start_dt.replace(tzinfo=tzinfo)
                else:
                    start_local_dt = start_dt.astimezone(tzinfo)
            else:
                start_local_dt = (datetime.now(tzinfo) + timedelta(hours=2)).replace(
                    minute=0,
                    second=0,
                    microsecond=0,
                )

            if isinstance(end_dt, datetime):
                if end_dt.tzinfo is None:
                    end_local_dt = end_dt.replace(tzinfo=start_local_dt.tzinfo or tzinfo)
                else:
                    end_local_dt = end_dt.astimezone(start_local_dt.tzinfo or tzinfo)
            else:
                end_local_dt = start_local_dt + timedelta(minutes=DEFAULT_DURATION_MINUTES)

            duration_default = int(
                max(30, round((end_local_dt - start_local_dt).total_seconds() / 60))
            )

            if st.session_state.get("calendar__new_selection_token") != selection_token:
                st.session_state["calendar__new_selection_token"] = selection_token
                for field in (
                    "calendar__new_home",
                    "calendar__new_away",
                    "calendar__new_comp",
                    "calendar__new_venue",
                    "calendar__new_country",
                    "calendar__new_notes",
                ):
                    st.session_state.pop(field, None)
                st.session_state["calendar__new_date"] = start_local_dt.date()
                st.session_state["calendar__new_time"] = start_local_dt.time().replace(
                    second=0,
                    microsecond=0,
                )
                st.session_state["calendar__new_duration"] = duration_default

            kickoff_date = st.date_input("Kick-off date", key="calendar__new_date")
            kickoff_time = st.time_input("Kick-off time", key="calendar__new_time")
            duration_minutes = int(
                st.number_input(
                    "Duration (minutes)",
                    min_value=30,
                    max_value=240,
                    step=5,
                    key="calendar__new_duration",
                )
            )

            kickoff_local = datetime.combine(kickoff_date, kickoff_time)
            kickoff_local = kickoff_local.replace(tzinfo=tzinfo)
            end_local = kickoff_local + timedelta(minutes=duration_minutes)

            disabled = False
            if not (home.strip() and away.strip()):
                disabled = True
                st.info("Provide home & away teams to save the match.")

            if st.button("Save match ✅", type="primary", disabled=disabled, use_container_width=True):
                payload = {
                    "home_team": home.strip(),
                    "away_team": away.strip(),
                    "competition": _clean_str(competition),
                    "venue": _clean_str(venue),
                    "country": _clean_str(country),
                    "tz_name": _clean_str(tz_name),
                    "kickoff_at": kickoff_local.isoformat(),
                    "ends_at_utc": utc_iso(end_local.astimezone(UTC)),
                    "notes": _clean_str(notes),
                    "location": _clean_str(venue),
                }
                _push_debug_event(
                    "submit_new_match",
                    payload={
                        "payload": payload,
                        "selection_token": selection_token,
                    },
                )
                try:
                    response = get_client().table("matches").insert(payload).execute()
                    _push_debug_event(
                        "new_match_created",
                        payload={
                            "response": getattr(response, "data", None),
                        },
                    )
                    st.session_state["calendar__tz"] = tz_name
                    st.session_state.pop("calendar__selection", None)
                    st.session_state.pop("calendar__show_new_form", None)
                    st.success("Match created")
                    st.rerun()
                except APIError as exc:
                    _warn_api_error("Failed to create match", exc)

            if st.button("Cancel", use_container_width=True):
                st.session_state.pop("calendar__selection", None)
                st.session_state.pop("calendar__show_new_form", None)
                st.rerun()


def _render_match_editor(match: Dict[str, Any], is_authenticated: bool) -> None:
    tz_options = list(LATAM_TZS)
    tz_val = match.get("tz_name") or tz_options[0]
    if tz_val not in tz_options:
        tz_val = tz_options[0]

    players = _load_players()
    player_options = [p.get("id") for p in players if p.get("id")]
    player_labels = {
        p.get("id"): f"{p.get('name', 'Unknown')} ({p.get('current_club') or '–'})"
        for p in players
        if p.get("id")
    }

    existing_targets = match.get("targets") or _load_match_targets(match.get("id"))

    with _sidebar_owner():
        with st.sidebar:
            st.subheader("✏️ Edit match")
            st.caption(f"Kick-off: {_kickoff_details(match)}")

            competition = st.text_input("Competition", match.get("competition") or "")
            venue = st.text_input("Venue", match.get("venue") or match.get("location") or "")
            country = st.text_input("Country", match.get("country") or "")
            home = st.text_input("Home team", match.get("home_team") or "")
            away = st.text_input("Away team", match.get("away_team") or "")
            tz_name = st.selectbox("Match time zone", tz_options, index=tz_options.index(tz_val))
            notes = st.text_area("Notes", match.get("notes") or "")

            st.markdown("**🎯 Targets in this match**")
            selected_targets = st.multiselect(
                "Players to follow",
                options=player_options,
                default=list(existing_targets),
                format_func=lambda pid: player_labels.get(pid, pid),
            )

            if not is_authenticated:
                st.info("Sign in to save changes.")

            if st.button("💾 Save", type="primary", disabled=not is_authenticated, use_container_width=True):
                payload = {
                    "competition": _clean_str(competition),
                    "venue": _clean_str(venue),
                    "country": _clean_str(country),
                    "home_team": home.strip() if home else None,
                    "away_team": away.strip() if away else None,
                    "tz_name": _clean_str(tz_name),
                    "notes": _clean_str(notes),
                    "location": _clean_str(venue),
                }
                try:
                    get_client().table("matches").update(payload).eq("id", match["id"]).execute()
                    if is_authenticated:
                        _sync_targets(match["id"], selected_targets, existing_targets)
                    st.success("Match updated")
                    st.rerun()
                except APIError as exc:
                    _warn_api_error("Failed to update match", exc)

            if st.button("📝 New Report", use_container_width=True):
                st.session_state["report_prefill_match_id"] = match.get("id")
                st.session_state["current_page"] = "Reports"
                st.rerun()

            if st.button("🗑️ Delete", type="secondary", disabled=not is_authenticated, use_container_width=True):
                try:
                    get_client().table("matches").delete().eq("id", match["id"]).execute()
                    st.success("Match deleted")
                    st.rerun()
                except APIError as exc:
                    _warn_api_error("Failed to delete match", exc)


def _handle_drop(event_payload: Dict[str, Any], is_authenticated: bool) -> None:
    if not is_authenticated:
        st.warning("Sign in to modify match times.")
        return

    event = event_payload.get("event") or {}
    match_id = event.get("id")
    if not match_id:
        return

    start_dt = _event_datetime(event, "start")
    end_dt = _event_datetime(event, "end")

    if not start_dt:
        return

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=UTC)
    if end_dt and end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=start_dt.tzinfo or UTC)

    kickoff_local = start_dt
    if kickoff_local.tzinfo is None:
        kickoff_local = kickoff_local.replace(tzinfo=UTC)

    if end_dt is None:
        end_local = kickoff_local + timedelta(minutes=DEFAULT_DURATION_MINUTES)
    else:
        end_local = end_dt
        if end_local.tzinfo is None:
            end_local = end_local.replace(tzinfo=kickoff_local.tzinfo or UTC)

    payload = {
        "kickoff_at": kickoff_local.isoformat(),
        "ends_at_utc": utc_iso(end_local.astimezone(UTC)),
    }
    try:
        get_client().table("matches").update(payload).eq("id", match_id).execute()
        st.toast("Kick-off updated")
    except APIError as exc:
        _warn_api_error("Failed to update kick-off", exc)


def _handle_resize(event_payload: Dict[str, Any], is_authenticated: bool) -> None:
    if not is_authenticated:
        st.warning("Sign in to modify match duration.")
        return

    event = event_payload.get("event") or {}
    match_id = event.get("id")
    if not match_id:
        return

    start_dt = _event_datetime(event, "start")
    end_dt = _event_datetime(event, "end")

    if not start_dt or not end_dt:
        return

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=UTC)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=start_dt.tzinfo or UTC)

    payload = {
        "kickoff_at": start_dt.isoformat(),
        "ends_at_utc": utc_iso(end_dt.astimezone(UTC)),
    }
    try:
        get_client().table("matches").update(payload).eq("id", match_id).execute()
        st.toast("Duration updated")
    except APIError as exc:
        _warn_api_error("Failed to update duration", exc)


def _handle_event_change(change_payload: Dict[str, Any], is_authenticated: bool) -> None:
    if not is_authenticated:
        st.warning("Sign in to modify match times.")
        return

    event = change_payload.get("event") or {}
    old_event = change_payload.get("oldEvent") or {}
    match_id = event.get("id") or old_event.get("id")
    if not match_id:
        return

    start_dt = _event_datetime(event, "start") or _event_datetime(event, "startStr")
    end_dt = _event_datetime(event, "end") or _event_datetime(event, "endStr")

    if start_dt is None:
        start_dt = _event_datetime(old_event, "start") or _event_datetime(old_event, "startStr")
    if end_dt is None:
        end_dt = _event_datetime(old_event, "end") or _event_datetime(old_event, "endStr")

    if start_dt is None:
        return

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=UTC)

    if end_dt is None:
        end_dt = start_dt + timedelta(minutes=DEFAULT_DURATION_MINUTES)
    elif end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=start_dt.tzinfo or UTC)

    new_start_iso = start_dt.isoformat()
    compare_start_iso = utc_iso(start_dt.astimezone(UTC))
    compare_end_iso = utc_iso(end_dt.astimezone(UTC))
    ends_at_utc_iso = compare_end_iso

    old_start = _event_datetime(old_event, "start") or _event_datetime(old_event, "startStr")
    old_end = _event_datetime(old_event, "end") or _event_datetime(old_event, "endStr")
    if (
        old_start
        and old_end
        and utc_iso(old_start.astimezone(UTC)) == compare_start_iso
        and utc_iso(old_end.astimezone(UTC)) == compare_end_iso
    ):
        return

    payload = {
        "kickoff_at": new_start_iso,
        "ends_at_utc": ends_at_utc_iso,
    }
    try:
        get_client().table("matches").update(payload).eq("id", match_id).execute()
        st.toast("Match timing updated")
    except APIError as exc:
        _warn_api_error("Failed to update match timing", exc)


def _calendar_payload(state: Dict[str, Any], callback: str) -> Optional[Dict[str, Any]]:
    if not isinstance(state, dict):
        return None
    state_callback = state.get("callback")
    if state_callback:
        if state_callback != callback:
            return None
        return state.get(callback)
    return state.get(callback)


def show_calendar() -> None:
    st.header("📅 Matches — Calendar")

    auth = st.session_state.get("auth", {})
    is_authenticated = bool(auth.get("authenticated"))
    if not is_authenticated:
        st.info("Sign in to create or edit matches. Calendar is read-only for guests.")

    if calendar_component is None:
        st.info(
            "Install streamlit-calendar for the drag-and-drop calendar. You can still review and add matches below."
        )

    _render_debug_helpers()

    matches = _load_matches()
    events: List[Dict[str, Any]] = []
    for row in matches:
        event = _match_to_event(row)
        if event:
            events.append(event)

    if is_authenticated and st.button("➕ Add match", key="calendar__open_form"):
        _push_debug_event("click_add_match_button")
        st.session_state["calendar__show_new_form"] = True
        st.session_state.pop("calendar__selection", None)

    if calendar_component is not None:
        options = {
            "initialView": "dayGridMonth",
            "height": 760,
            "locale": "en",
            "timeZone": "local",
            "firstDay": 1,
            "selectable": is_authenticated,
            "editable": is_authenticated,
            "eventStartEditable": is_authenticated,
            "eventDurationEditable": is_authenticated,
            "eventTimeFormat": {"hour": "2-digit", "minute": "2-digit"},
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay,listWeek",
            },
        }

        state = calendar_component(
            events=events,
            options=options,
            key="scoutlens_calendar",
        )
    else:
        state = None

    if isinstance(state, dict):
        selection = _calendar_payload(state, "select")
        if selection and is_authenticated:
            _push_debug_event(
                "calendar_selection_authenticated",
                payload={"selection": selection},
            )
            st.session_state["calendar__show_new_form"] = True
            st.session_state["calendar__selection"] = selection
        elif selection:
            _push_debug_event(
                "calendar_selection_guest",
                payload={"selection": selection},
            )
            st.warning("Sign in to add matches from the calendar.")

        click = _calendar_payload(state, "eventClick")
        if click:
            match_id = (click.get("event") or {}).get("id")
            if match_id:
                match = _load_match(match_id)
                if match:
                    _render_match_editor(match, is_authenticated)

        drop = _calendar_payload(state, "eventDrop")
        if drop:
            _handle_drop(drop, is_authenticated)

        resize = _calendar_payload(state, "eventResize")
        if resize:
            _handle_resize(resize, is_authenticated)

        change = _calendar_payload(state, "eventChange")
        if change:
            _handle_event_change(change, is_authenticated)

    if is_authenticated and st.session_state.get("calendar__show_new_form"):
        _render_new_match_form(st.session_state.get("calendar__selection"))

    if matches:
        expanded = calendar_component is None
        with st.expander("Upcoming matches", expanded=expanded):
            for row in matches[:25]:
                title = f"{row.get('home_team') or '—'} vs {row.get('away_team') or '—'}"
                details = _kickoff_details(row)
                comp = row.get("competition")
                suffix = f" · {comp}" if comp else ""
                st.markdown(f"- **{title}** — {details}{suffix}")

    if not events:
        st.info("No matches scheduled in the next 60 days. Add one to get started!")



__all__ = ["show_calendar", "_maps_search_url"]
