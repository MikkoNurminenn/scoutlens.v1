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
