from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import calendar_browser_store as browser_store
import calendar_local_store as local_store
from app import calendar_ui


def test_event_header_includes_time_and_location():
    event = {
        "title": "Friendly",
        "start_utc": "2024-07-01T15:00:00+00:00",
        "end_utc": "2024-07-01T17:00:00+00:00",
        "location": "Barranquilla",
        "timezone": "America/Bogota",
    }
    header = calendar_ui._event_header(event, "America/Bogota")
    assert "Friendly" in header
    assert "Barranquilla" in header
    assert "2024-07-01" in header


def test_local_store_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(local_store, "_app_dir", lambda: str(tmp_path))
    start = "2024-07-05T18:00:00+00:00"
    end = "2024-07-05T19:30:00+00:00"

    created = local_store.create_event({
        "title": "Match One",
        "start_utc": start,
        "end_utc": end,
        "timezone": "UTC",
        "location": "Medellín",
    })

    fetched = local_store.get_event(created["id"])
    assert fetched is not None
    assert fetched["title"] == "Match One"

    updated = local_store.update_event(created["id"], {"title": "Match Uno"})
    assert updated is not None
    assert updated["title"] == "Match Uno"

    events = local_store.list_events()
    assert len(events) == 1
    assert events[0]["id"] == created["id"]

    assert local_store.delete_event(created["id"])
    assert local_store.list_events() == []


def test_local_store_export_files(monkeypatch, tmp_path):
    monkeypatch.setattr(local_store, "_app_dir", lambda: str(tmp_path))
    local_store.create_event({
        "title": "Export Me",
        "start_utc": "2024-08-01T12:00:00+00:00",
        "end_utc": "2024-08-01T13:00:00+00:00",
        "timezone": "UTC",
    })

    csv_path = Path(local_store.export_csv())
    json_path = Path(local_store.export_json())

    assert csv_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data and data[0]["title"] == "Export Me"


def test_browser_store_uses_js_eval(monkeypatch):
    storage: Dict[str, str] = {}

    def fake_js_eval(*, js_expressions: str, want_output: bool = False, key: str | None = None):
        if "getItem" in js_expressions:
            return storage.get(browser_store.KEY, "[]")
        if "setItem" in js_expressions:
            start = js_expressions.index("`") + 1
            end = js_expressions.rindex("`")
            storage[browser_store.KEY] = js_expressions[start:end]
            return None
        if "removeItem" in js_expressions:
            storage.pop(browser_store.KEY, None)
            return None
        raise AssertionError(f"Unexpected JS expression: {js_expressions}")

    monkeypatch.setattr(browser_store, "streamlit_js_eval", fake_js_eval)

    event = browser_store.create_event({
        "title": "Browser Match",
        "start_utc": "2024-09-10T18:00:00+00:00",
        "end_utc": "2024-09-10T20:00:00+00:00",
        "timezone": "UTC",
    })

    listed = browser_store.list_events()
    assert listed and listed[0]["id"] == event["id"]

    browser_store.update_event(event["id"], {"location": "Cali"})
    refreshed = browser_store.get_event(event["id"])
    assert refreshed["location"] == "Cali"

    assert browser_store.delete_event(event["id"])
    assert browser_store.list_events() == []

    browser_store.clear_all()
    assert storage.get(browser_store.KEY) in (None, "[]")
