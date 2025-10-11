from __future__ import annotations

import json
import base64
from datetime import datetime
from inspect import signature
from typing import Any, Dict, Iterable, List, Optional

import streamlit as st

try:  # pragma: no cover - Streamlit API differences across versions
    from streamlit.errors import StreamlitAPIException
except Exception:  # pragma: no cover - older Streamlit versions
    StreamlitAPIException = Exception  # type: ignore[misc,assignment]

try:  # pragma: no cover - optional dependency for local browser storage
    from streamlit_js_eval import streamlit_js_eval
except ModuleNotFoundError:  # pragma: no cover
    def streamlit_js_eval(*_, **__):
        raise RuntimeError("streamlit-js-eval is required for browser storage features")
from zoneinfo import ZoneInfo

DEFAULT_TZ = "America/Bogota"
try:
    _DATETIME_INPUT_SUPPORTS_TZ = "timezone" in signature(st.datetime_input).parameters
except Exception:  # pragma: no cover - Streamlit API differences
    _DATETIME_INPUT_SUPPORTS_TZ = False
try:
    UTC = ZoneInfo("UTC")
except Exception:  # pragma: no cover - ZoneInfo always available on Py3.11
    UTC = ZoneInfo("Etc/UTC")


def _resolve_tz(name: Optional[str]) -> ZoneInfo:
    if name:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    try:
        return ZoneInfo(DEFAULT_TZ)
    except Exception:
        return UTC


def _parse_iso(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _localize(dt: datetime, tz_name: str) -> datetime:
    tz = _resolve_tz(tz_name)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def _datetime_input(
    container,
    label: str,
    *,
    value: Optional[datetime],
    timezone: str,
    key: Optional[str] = None,
):
    """Wrapper around Streamlit datetime_input with timezone compatibility."""

    global _DATETIME_INPUT_SUPPORTS_TZ

    kwargs: Dict[str, Any] = {}

    if key is not None:
        kwargs["key"] = key

    if _DATETIME_INPUT_SUPPORTS_TZ:
        try:
            return container.datetime_input(
                label,
                value=value,
                timezone=timezone,
                **kwargs,
            )
        except (TypeError, StreamlitAPIException):
            _DATETIME_INPUT_SUPPORTS_TZ = False

    if value is not None:
        tz = _resolve_tz(timezone)
        dt = value
        if dt.tzinfo is not None:
            dt = dt.astimezone(tz)
        kwargs["value"] = dt.replace(tzinfo=None) if dt.tzinfo else dt
    else:
        kwargs["value"] = value

    return container.datetime_input(label, **kwargs)


def _to_local(utc_iso: Any, tz_name: str) -> Optional[datetime]:
    dt = _parse_iso(utc_iso)
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(_resolve_tz(tz_name))


def _event_header(event: Dict[str, Any], fallback_tz: str) -> str:
    title = event.get("title") or "Untitled"
    tz_name = event.get("timezone") or fallback_tz
    start_local = _to_local(event.get("start_utc"), tz_name)
    end_local = _to_local(event.get("end_utc"), tz_name)
    parts: List[str] = [title]
    if start_local:
        time_str = start_local.strftime("%Y-%m-%d %H:%M")
        if end_local:
            time_str = f"{time_str} → {end_local.strftime('%H:%M')}"
        parts.append(time_str)
    if event.get("location"):
        parts.append(str(event["location"]))
    return " — ".join(parts)


def _import_events(cal_module, data: Iterable[Any]) -> int:
    imported = 0
    for row in data:
        if isinstance(row, dict):
            cal_module.upsert_event(row)
            imported += 1
    return imported


def show_calendar() -> None:
    st.title("📆 ScoutLens Calendar (Local Only)")
    st.caption(
        "Calendar events are stored locally on your device. All other ScoutLens data stays in Supabase."
    )

    browser_supported = False
    try:
        import calendar_browser_store as browser_store

        if hasattr(browser_store, "has_js_eval"):
            browser_supported = bool(browser_store.has_js_eval())
        else:
            browser_supported = bool(getattr(browser_store, "HAS_JS_EVAL", True))
    except Exception:  # noqa: BLE001 - fallback to local storage if anything fails
        browser_store = None  # type: ignore[assignment]

    options: List[str] = []
    if browser_supported:
        options.append("Browser (mobile/phone)")
    else:
        st.info(
            "Browser storage requires the optional `streamlit-js-eval` package. "
            "Falling back to local file storage."
        )
    options.append("Local file (PC)")

    default_index = 0 if browser_supported else len(options) - 1
    mode = st.radio(
        "Calendar storage",
        options,
        index=default_index,
        horizontal=True,
    )

    if mode == "Browser (mobile/phone)" and browser_supported and browser_store:
        cal_module = browser_store
    else:
        import calendar_local_store as cal_module

    cal = cal_module
    local_tz = st.session_state.get("latam_tz", DEFAULT_TZ)

    st.subheader("Create / Edit Event")
    now_local = datetime.now(_resolve_tz(local_tz))
    with st.form("calendar_event_form"):
        title = st.text_input("Title", "Match: Junior vs. Millonarios")
        col1, col2 = st.columns(2)
        default_start = now_local.replace(microsecond=0)
        start_local_input = _datetime_input(
            col1,
            "Start (local)",
            value=default_start,
            timezone=local_tz,
        )
        end_local_input = _datetime_input(
            col2,
            "End (local)",
            value=default_start,
            timezone=local_tz,
        )
        location = st.text_input("Location (city/stadium)")
        home_team = st.text_input("Home team")
        away_team = st.text_input("Away team")
        competition = st.text_input("Competition")
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save event", type="primary")

    if submitted:
        if not start_local_input or not end_local_input:
            st.error("Start and end times are required.")
        else:
            start_local_dt = _localize(start_local_input, local_tz)
            end_local_dt = _localize(end_local_input, local_tz)
            start_utc_iso = start_local_dt.astimezone(UTC).isoformat()
            end_utc_iso = end_local_dt.astimezone(UTC).isoformat()
            cal.create_event(
                {
                    "title": title,
                    "start_utc": start_utc_iso,
                    "end_utc": end_utc_iso,
                    "timezone": local_tz,
                    "location": location,
                    "home_team": home_team,
                    "away_team": away_team,
                    "competition": competition,
                    "notes": notes,
                    "targets": [],
                }
            )
            st.success(f"Saved ({mode})")
            st.rerun()

    st.divider()
    st.subheader("Upcoming (local time)")

    events = cal.list_events()
    if not events:
        st.info("No local events yet. Add your first match above!")
    for event in events[:100]:
        header = _event_header(event, local_tz)
        with st.expander(header):
            st.json(event)
            cols = st.columns(3)
            if cols[0].button("Delete", key=f"delete_{event.get('id')}"):
                cal.delete_event(event.get("id"))
                st.toast("Deleted")
                st.rerun()

    st.divider()
    st.subheader("Backup / Transfer")

    if mode == "Browser (mobile/phone)":
        if st.button("Export JSON"):
            rows = cal.list_events()
            _browser_export_events(rows, key="calendar_export_json")
            st.toast("Exported JSON")

        uploaded = st.file_uploader("Import JSON", type=["json"], accept_multiple_files=False)
        if uploaded and st.button("Import now"):
            try:
                data = json.loads(uploaded.getvalue().decode("utf-8"))
                if not isinstance(data, list):
                    raise ValueError("JSON must contain a list of events")
                imported = _import_events(cal, data)
                st.success(f"Imported {imported} events")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Import failed: {exc}")
    else:
        col_csv, col_json = st.columns(2)
        if col_csv.button("Export CSV"):
            path = cal.export_csv()
            st.success(f"CSV exported → {path}")
        if col_json.button("Export JSON"):
            path = cal.export_json()
            st.success(f"JSON exported → {path}")

        uploaded = st.file_uploader("Import JSON", type=["json"], accept_multiple_files=False)
        if uploaded and st.button("Import now (local file)"):
            try:
                data = json.loads(uploaded.getvalue().decode("utf-8"))
                if not isinstance(data, list):
                    raise ValueError("JSON must contain a list of events")
                imported = _import_events(cal, data)
                st.success(f"Imported {imported} events")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Import failed: {exc}")


def _browser_export_events(rows: Iterable[Any], *, key: str) -> None:
    js_expressions = _build_browser_export_js(rows)
    streamlit_js_eval(
        js_expressions=js_expressions,
        key=key,
    )


def _build_browser_export_js(rows: Iterable[Any]) -> tuple[str, ...]:
    payload = json.dumps(list(rows), ensure_ascii=False)
    payload_base64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return (
        "(() => {\n",
        f"  const decoded = atob('{payload_base64}');\n",
        "  const bytes = Uint8Array.from(decoded, (c) => c.charCodeAt(0));\n",
        "  const data = new Blob([bytes], {type: 'application/json'});\n",
        "  const url = URL.createObjectURL(data);\n",
        "  const a = document.createElement('a');\n",
        "  a.href = url; a.download = 'scoutlens_calendar_backup.json';\n",
        "  a.click(); URL.revokeObjectURL(url);\n",
        "})()",
    )


__all__ = ["show_calendar"]
