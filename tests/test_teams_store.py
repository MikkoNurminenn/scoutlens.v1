import sys
from pathlib import Path
import importlib

# Ensure application modules can be imported as top-level modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))


class FakeTable:
    def __init__(self, name, db):
        self.name = name
        self.db = db
        self._data = db.setdefault(name, [])
        self._filter = None

    def select(self, *args, **kwargs):
        self._filter = None
        return self

    def execute(self):
        return type("Res", (), {"data": list(self._data)})()

    def insert(self, item):
        self._data.append(item)
        return self


class FakeClient:
    def __init__(self, db):
        self.db = db

    def table(self, name):
        return FakeTable(name, self.db)


def setup_store(monkeypatch):
    db = {"teams": []}
    fake_client = FakeClient(db)
    import supabase_client
    monkeypatch.setattr(supabase_client, "get_client", lambda: fake_client)
    import teams_store
    importlib.reload(teams_store)
    return teams_store, db


def test_add_team_success(monkeypatch):
    ts, db = setup_store(monkeypatch)
    ok, info = ts.add_team("Testers")
    assert ok is True
    assert info == "Testers"
    assert "Testers" in ts.list_teams()


def test_add_team_duplicate(monkeypatch):
    ts, db = setup_store(monkeypatch)
    assert ts.add_team("Santos")[0] is True
    ok, msg = ts.add_team("santos")
    assert ok is False
    assert "exists" in msg.lower()
