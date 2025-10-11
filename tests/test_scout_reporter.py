"""Tests for Supabase integration helpers in scout_reporter."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from app import scout_reporter


class _TableStub:
    """Mimic Supabase table API while capturing the payload."""

    def __init__(self, record: Dict[str, Any]):
        self._record = record

    def insert(self, payload: Dict[str, Any]):  # pragma: no cover - exercised in tests
        self._record["payload"] = payload
        return self

    def execute(self):  # pragma: no cover - exercised in tests
        self._record["executed"] = True
        return {"data": None}


class _ClientStub:
    """Minimal Supabase client stub used to observe calls."""

    def __init__(self, record: Dict[str, Any]):
        self._record = record

    def table(self, name: str):  # pragma: no cover - exercised in tests
        self._record["table"] = name
        return _TableStub(self._record)


def test_insert_match_persists_payload(monkeypatch):
    """insert_match must send a fully-populated record to Supabase."""

    calls: Dict[str, Any] = {}
    monkeypatch.setattr(scout_reporter, "get_client", lambda: _ClientStub(calls))

    class _FixedUUID:
        hex = "fixed-id"

    monkeypatch.setattr(scout_reporter.uuid, "uuid4", lambda: _FixedUUID())

    kickoff = "2024-08-12T15:00:00+00:00"
    scout_reporter.insert_match(
        {
            "home_team": "Atlético",
            "away_team": "Boca",
            "competition": "Libertadores",
            "location": "Estadio Uno",
            "kickoff_at": kickoff,
        }
    )

    assert calls["table"] == scout_reporter.MATCHES
    assert calls["executed"] is True

    payload = calls["payload"]
    assert payload["id"] == "fixed-id"
    assert payload["home_team"] == "Atlético"
    assert payload["away_team"] == "Boca"
    assert payload["competition"] == "Libertadores"
    assert payload["location"] == "Estadio Uno"
    assert payload["kickoff_at"] == kickoff
    # Optional fields default to empty strings when omitted by the caller.
    assert payload["notes"] == ""


def test_insert_match_surfaces_supabase_error(monkeypatch):
    """Failures from Supabase should be propagated after showing the error."""

    class _FailingTable:
        def insert(self, payload):  # pragma: no cover - exercised in tests
            return self

        def execute(self):  # pragma: no cover - exercised in tests
            raise RuntimeError("boom")

    class _FailingClient:
        def table(self, name):  # pragma: no cover - exercised in tests
            return _FailingTable()

    monkeypatch.setattr(scout_reporter, "get_client", lambda: _FailingClient())

    errors: Dict[str, Any] = {}

    def fake_error(msg):  # pragma: no cover - exercised in tests
        errors["message"] = msg

    def fake_code(tb, language="text"):  # pragma: no cover - exercised in tests
        errors["code_language"] = language

    monkeypatch.setattr(scout_reporter.st, "error", fake_error)
    monkeypatch.setattr(scout_reporter.st, "code", fake_code)

    with pytest.raises(RuntimeError):
        scout_reporter.insert_match(
            {
                "home_team": "River",
                "away_team": "Colón",
                "kickoff_at": "2024-09-02T17:30:00+00:00",
            }
        )

    assert errors["message"] == "❌ Save failed"
    assert errors["code_language"] == "text"
