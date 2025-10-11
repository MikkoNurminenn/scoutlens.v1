from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app import calendar_ui


def test_maps_search_url_combines_parts():
    url = calendar_ui._maps_search_url("Estadio Uno", "La Plata")
    assert url is not None
    assert url.startswith("https://www.google.com/maps/search/?api=1&query=")
    assert "Estadio+Uno%2C+La+Plata" in url


def test_maps_search_url_handles_empty_values():
    assert calendar_ui._maps_search_url(" ", None) is None
    assert calendar_ui._maps_search_url() is None


def test_kickoff_sort_key_handles_missing_kickoff():
    rows = [
        {"id": "missing", "kickoff_at": None},
        {"id": "scheduled", "kickoff_at": "2024-07-05T18:00:00-05:00"},
    ]

    rows.sort(key=calendar_ui._kickoff_sort_key)

    assert [row["id"] for row in rows] == ["scheduled", "missing"]
    for row in rows:
        key = calendar_ui._kickoff_sort_key(row)
        assert key.tzinfo is not None


class _DummyTable:
    def __init__(self):
        self.payload = None
        self.filters = []

    def update(self, payload):
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def execute(self):  # pragma: no cover - side effect free stub
        return self


class _DummyClient:
    def __init__(self):
        self.table_obj = _DummyTable()

    def table(self, name):
        assert name == "matches"
        return self.table_obj


@pytest.fixture
def dummy_st():
    return SimpleNamespace(warning=lambda *args, **kwargs: None, toast=lambda *args, **kwargs: None)


class _QueryRecorder:
    def __init__(self):
        self.filters = []
        self.ordered = None
        self.limited = None

    def select(self, *_args, **_kwargs):
        return self

    def gte(self, column, value):
        self.filters.append(("gte", column, value))
        return self

    def lte(self, column, value):
        self.filters.append(("lte", column, value))
        return self

    def order(self, column, desc=False):
        self.ordered = (column, desc)
        return self

    def limit(self, value):
        self.limited = value
        return self

    def execute(self):
        return SimpleNamespace(data=[])


def test_load_matches_includes_recent_past(monkeypatch):
    recorder = _QueryRecorder()

    class _Client:
        def table(self, name):
            assert name == "matches"
            return recorder

    fixed_now = datetime(2024, 1, 15, 12, 0, tzinfo=calendar_ui.UTC)

    class _FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            assert tz is calendar_ui.UTC
            return fixed_now

    monkeypatch.setattr(calendar_ui, "get_client", lambda: _Client())
    monkeypatch.setattr(calendar_ui, "datetime", _FixedDateTime)

    rows = calendar_ui._load_matches()

    assert rows == []

    gte_filters = [f for f in recorder.filters if f[0] == "gte"]
    assert gte_filters, "Expected gte filter to be applied"
    gte_value = gte_filters[0][2]
    assert gte_filters[0][1] == "kickoff_at"

    expected_since = calendar_ui.utc_iso(
        fixed_now - timedelta(days=calendar_ui.FETCH_PAST_DAYS)
    )
    assert gte_value == expected_since

    lte_filters = [f for f in recorder.filters if f[0] == "lte"]
    assert lte_filters, "Expected lte filter to be applied"
    assert lte_filters[0][1] == "kickoff_at"

    expected_until = calendar_ui.utc_iso(
        fixed_now + timedelta(days=calendar_ui.FETCH_WINDOW_DAYS)
    )
    assert lte_filters[0][2] == expected_until


def test_handle_drop_preserves_match_timezone(monkeypatch, dummy_st):
    client = _DummyClient()
    monkeypatch.setattr(calendar_ui, "get_client", lambda: client)
    monkeypatch.setattr(calendar_ui, "st", dummy_st)

    payload = {
        "event": {
            "id": "match-1",
            "start": "2024-07-05T18:00:00-05:00",
            "end": "2024-07-05T20:00:00-05:00",
        }
    }

    calendar_ui._handle_drop(payload, is_authenticated=True)

    assert client.table_obj.filters == [("id", "match-1")]
    assert client.table_obj.payload["kickoff_at"] == "2024-07-05T18:00:00-05:00"
    assert client.table_obj.payload["ends_at_utc"] == "2024-07-06T01:00:00+00:00"


def test_handle_resize_updates_local_kickoff(monkeypatch, dummy_st):
    client = _DummyClient()
    monkeypatch.setattr(calendar_ui, "get_client", lambda: client)
    monkeypatch.setattr(calendar_ui, "st", dummy_st)

    payload = {
        "event": {
            "id": "match-9",
            "start": "2024-07-07T21:15:00-03:00",
            "end": "2024-07-07T23:05:00-03:00",
        }
    }

    calendar_ui._handle_resize(payload, is_authenticated=True)

    assert client.table_obj.filters == [("id", "match-9")]
    assert client.table_obj.payload["kickoff_at"] == "2024-07-07T21:15:00-03:00"
    assert client.table_obj.payload["ends_at_utc"] == "2024-07-08T02:05:00+00:00"
