from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional dependency for browser runtime only
    from streamlit_js_eval import streamlit_js_eval
except ModuleNotFoundError:  # pragma: no cover

    def streamlit_js_eval(*_, **__):
        raise RuntimeError("streamlit-js-eval is required for browser calendar storage")

    streamlit_js_eval._is_placeholder = True  # type: ignore[attr-defined]


def _js_eval_available() -> bool:
    return not getattr(streamlit_js_eval, "_is_placeholder", False)


def _require_js_eval() -> None:
    global HAS_JS_EVAL
    HAS_JS_EVAL = has_js_eval()
    if not HAS_JS_EVAL:
        raise RuntimeError("Browser calendar storage requires streamlit-js-eval.")


def has_js_eval() -> bool:
    """Return True if the optional JS evaluation helper is available."""

    return _js_eval_available()


HAS_JS_EVAL = has_js_eval()

KEY = "scoutlens_calendar_events_v1"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_MIN_AWARE = datetime(1, 1, 1, tzinfo=timezone.utc)


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _ls_get() -> List[Dict[str, Any]]:
    data = streamlit_js_eval(
        js_expressions=f"window.localStorage.getItem('{KEY}')",
        want_output=True,
        key="ls_get_" + KEY,
    ) or "[]"
    try:
        arr = json.loads(data)
        return arr if isinstance(arr, list) else []
    except Exception:
        return []


def _ls_set(rows: List[Dict[str, Any]]) -> None:
    payload = json.dumps(rows, ensure_ascii=False)
    streamlit_js_eval(
        js_expressions=f"window.localStorage.setItem('{KEY}', `{payload}`)",
        key="ls_set_" + KEY,
    )


def list_events() -> List[Dict[str, Any]]:
    _require_js_eval()
    rows = _ls_get()
    return sorted(
        rows,
        key=lambda r: _parse_dt(r.get("start_utc")) or _MIN_AWARE,
        reverse=True,
    )


def list_events_between(start_utc_iso: str, end_utc_iso: str) -> List[Dict[str, Any]]:
    _require_js_eval()
    rows = _ls_get()
    start_dt = _parse_dt(start_utc_iso)
    end_dt = _parse_dt(end_utc_iso)
    if not start_dt or not end_dt:
        return []

    filtered: List[Dict[str, Any]] = []
    for row in rows:
        row_start = _parse_dt(row.get("start_utc"))
        row_end = _parse_dt(row.get("end_utc"))
        if not row_start or not row_end:
            continue
        if row_start < end_dt and row_end >= start_dt:
            filtered.append(row)

    return sorted(
        filtered,
        key=lambda r: _parse_dt(r.get("start_utc")) or _MIN_AWARE,
        reverse=True,
    )


def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    for r in _ls_get():
        if r.get("id") == event_id:
            return r
    return None


def create_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    _require_js_eval()
    rows = _ls_get()
    now_iso = _now_utc_iso()
    event = {
        "id": payload.get("id") or str(uuid.uuid4()),
        "title": payload.get("title", "Untitled"),
        "start_utc": payload["start_utc"],
        "end_utc": payload["end_utc"],
        "timezone": payload.get("timezone"),
        "location": payload.get("location"),
        "home_team": payload.get("home_team"),
        "away_team": payload.get("away_team"),
        "competition": payload.get("competition"),
        "targets": payload.get("targets", []),
        "notes": payload.get("notes"),
        "created_at": now_iso,
        "updated_at": now_iso,
        "source": "browser",
    }
    rows.append(event)
    _ls_set(rows)
    return event


def update_event(event_id: str, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    _require_js_eval()
    rows = _ls_get()
    updated_event: Optional[Dict[str, Any]] = None
    for idx, row in enumerate(rows):
        if row.get("id") == event_id:
            updated_event = {**row, **changes, "updated_at": _now_utc_iso()}
            rows[idx] = updated_event
            break
    if updated_event:
        _ls_set(rows)
    return updated_event


def delete_event(event_id: str) -> bool:
    _require_js_eval()
    rows = _ls_get()
    new_rows = [r for r in rows if r.get("id") != event_id]
    if len(new_rows) != len(rows):
        _ls_set(new_rows)
        return True
    return False


def upsert_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    _require_js_eval()
    event_id = payload.get("id")
    if not event_id:
        return create_event(payload)
    existing = get_event(event_id)
    if existing:
        return update_event(event_id, payload)
    return create_event(payload)


def clear_all() -> None:
    _require_js_eval()
    streamlit_js_eval(
        js_expressions=f"window.localStorage.removeItem('{KEY}')",
        key="ls_clear_" + KEY,
    )


__all__ = [
    "list_events",
    "list_events_between",
    "get_event",
    "create_event",
    "update_event",
    "delete_event",
    "upsert_event",
    "clear_all",
    "HAS_JS_EVAL",
    "has_js_eval",
]
