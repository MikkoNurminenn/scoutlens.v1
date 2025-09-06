import sys
from pathlib import Path
import importlib
import pandas as pd

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

    def eq(self, column, value):
        self._filter = (column, value)
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        data = list(self._data)
        if self._filter:
            col, val = self._filter
            data = [r for r in data if r.get(col) == val]
        return type("Res", (), {"data": data})()

    def upsert(self, data):
        items = data if isinstance(data, list) else [data]
        for item in items:
            id = item.get("id")
            for i, row in enumerate(self._data):
                if row.get("id") == id:
                    self._data[i] = item
                    break
            else:
                self._data.append(item)
        return self

    def insert(self, data):
        items = data if isinstance(data, list) else [data]
        self._data.extend(items)
        return self

    def delete(self):
        return self

    def in_(self, column, values):
        vals = set(values)
        self._data[:] = [r for r in self._data if r.get(column) not in vals]
        return self


class FakeClient:
    def __init__(self, db):
        self.db = db

    def table(self, name):
        return FakeTable(name, self.db)


def setup_data_utils(monkeypatch):
    db = {"teams": [], "players": [], "matches": []}
    fake_client = FakeClient(db)
    import supabase_client
    monkeypatch.setattr(supabase_client, "get_client", lambda: fake_client)
    import data_utils
    importlib.reload(data_utils)
    return data_utils, db


def test_list_teams(monkeypatch):
    du, db = setup_data_utils(monkeypatch)
    assert du.list_teams() == []
    db["teams"].extend([{ "name": "Team A" }, { "name": "Team B" }])
    teams = du.list_teams()
    assert set(teams) == {"Team A", "Team B"}


def test_load_master_creates_empty(monkeypatch):
    du, db = setup_data_utils(monkeypatch)
    team = "My Team"
    df = du.load_master(team)
    assert list(df.columns) == du.MASTER_COLUMNS
    assert df.empty


def test_save_master_persists_data(monkeypatch):
    du, db = setup_data_utils(monkeypatch)
    team = "My Team"
    df_new = pd.DataFrame([{ "PlayerID": 1, "Name": "Alice", "id": "1" }])
    du.save_master(df_new, team)
    df_loaded = du.load_master(team)
    assert df_loaded.loc[0, "PlayerID"] == 1
    assert df_loaded.loc[0, "Name"] == "Alice"
    assert str(df_loaded["PlayerID"].dtype) == "Int64"
