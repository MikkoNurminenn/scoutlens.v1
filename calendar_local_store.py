from __future__ import annotations

import csv
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

APP_DIR_ENV = "APPDATA"
APP_FOLDER_NAME = "ScoutLens"
CAL_FILE = "calendar_events.json"


def _app_dir() -> str:
    """Return the directory for storing calendar data and ensure it exists."""

    if os.name == "nt" and os.getenv(APP_DIR_ENV):
        base = os.path.join(os.getenv(APP_DIR_ENV), APP_FOLDER_NAME)
    else:
        base = os.path.join(os.path.expanduser("~"), ".scoutlens")
    os.makedirs(base, exist_ok=True)
    return base


def _file_path() -> str:
    return os.path.join(_app_dir(), CAL_FILE)


def _read_all() -> List[Dict[str, Any]]:
    fp = _file_path()
    if not os.path.exists(fp):
        return []
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        bak = fp + f".bak.{int(datetime.now().timestamp())}"
        try:
            os.replace(fp, bak)
        except Exception:
            pass
        return []


def _write_all(rows: List[Dict[str, Any]]) -> None:
    fp = _file_path()
    tmp = fp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    os.replace(tmp, fp)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_events() -> List[Dict[str, Any]]:
    rows = _read_all()
    return sorted(rows, key=lambda r: r.get("start_utc", ""), reverse=True)


def list_events_between(start_utc_iso: str, end_utc_iso: str) -> List[Dict[str, Any]]:
    rows = _read_all()
    return [
        r
        for r in rows
        if (r.get("start_utc", "") < end_utc_iso) and (r.get("end_utc", "") >= start_utc_iso)
    ]


def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    for r in _read_all():
        if r.get("id") == event_id:
            return r
    return None


def create_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    rows = _read_all()
    now_iso = _now_utc_iso()
    ev = {
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
        "source": "local",
    }
    rows.append(ev)
    _write_all(rows)
    return ev


def update_event(event_id: str, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = _read_all()
    out: Optional[Dict[str, Any]] = None
    for idx, row in enumerate(rows):
        if row.get("id") == event_id:
            updated = {**row, **changes, "updated_at": _now_utc_iso()}
            rows[idx] = updated
            out = updated
            break
    if out:
        _write_all(rows)
    return out


def delete_event(event_id: str) -> bool:
    rows = _read_all()
    new_rows = [r for r in rows if r.get("id") != event_id]
    if len(new_rows) != len(rows):
        _write_all(new_rows)
        return True
    return False


def upsert_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    event_id = payload.get("id")
    if not event_id:
        return create_event(payload)
    existing = get_event(event_id)
    if existing:
        return update_event(event_id, payload)
    return create_event(payload)


def export_csv(csv_path: Optional[str] = None) -> str:
    if not csv_path:
        csv_path = os.path.join(_app_dir(), "calendar_events_export.csv")
    rows = list_events()
    fieldnames = [
        "id",
        "title",
        "start_utc",
        "end_utc",
        "timezone",
        "location",
        "home_team",
        "away_team",
        "competition",
        "targets",
        "notes",
        "created_at",
        "updated_at",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = dict(row)
            if isinstance(normalized.get("targets"), list):
                normalized["targets"] = ",".join(map(str, normalized["targets"]))
            writer.writerow({key: normalized.get(key) for key in fieldnames})
    return csv_path


def export_json(json_path: Optional[str] = None) -> str:
    if not json_path:
        json_path = os.path.join(_app_dir(), "calendar_events_export.json")
    rows = list_events()
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return json_path


__all__ = [
    "list_events",
    "list_events_between",
    "get_event",
    "create_event",
    "update_event",
    "delete_event",
    "upsert_event",
    "export_csv",
    "export_json",
]
