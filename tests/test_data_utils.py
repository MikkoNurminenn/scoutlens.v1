import sys
from pathlib import Path
import importlib
import uuid
import pandas as pd

# Varmista että "app" löytyy import-polusta (säädä tarvittaessa)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))


# ---------------- In-memory Supabase mock ----------------
class FakeTable:
    def __init__(self, name, db):
        self.name = name
        self.db = db
        self._data = db.setdefault(name, [])
        self._filters = []
        self._order = None

    def select(self, *args, **kwargs):
        self._filters = []
        self._order = None
        return self

    def eq(self, column, value):
        self._filters.append(("eq", column, value))
        return self

    def in_(self, column, values):
        self._filters.append(("in", column, set(values)))
        return self

    def order(self, column, desc=False):
        self._order = (column, bool(desc))
        return self

    def upsert(self, data):
        items = data if isinstance(data, list) else [data]
        pk = "id"
        # players/matches voivat tulla ilman id:tä → generoi
        for item in items:
            if pk not in item or not item[pk]:
                item[pk] = uuid.uuid4().hex
            # team_name filttereille: varmistetaan että avain on olemassa jos taulu players/matches
            # (ei pakollinen tässä mockissa, mutta ei haittaa)
            found = False
            for i, row in enumerate(self._data):
                if row.get(pk) == item[pk]:
                    self._data[i] = {**row, **item}
                    found = True
                    break
            if not found:
                self._data.append(dict(item))
        return self

    def insert(self, data):
        items = data if isinstance(data, list) else [data]
        for item in items:
            if "id" not in item or not item["id"]:
                item["id"] = uuid.uuid4().hex
            self._data.append(dict(item))
        return self

    def delete(self):
        # delete ketjuttuu .in_():ssa; varsinainen poisto tehdään execute:ssa
        return self

    def execute(self):
        # Suodata
        data = list(self._data)
        for op, col, val in self._filters:
            if op == "eq":
                data = [r for r in data if r.get(col) == val]
            elif op == "in":
                data = [r for r in data if r.get(col) in val]
        # Järjestys
        if self._order:
            col, desc = self._order
            data.sort(key=lambda r: r.get(col), reverse=desc)
        return type("Res", (), {"data": data})()


class FakeClient:
    def __init__(self, db):
        self.db = db

    def table(self, name):
        return FakeTable(name, self.db)


# ---------------- Test setup helper ----------------
def setup_data_utils(monkeypatch):
    """
    Palauttaa (data_utils, db) siten, että data_utils käyttää in-memory Supabase-mockia.
    """
    db = {"teams": [], "players": [], "matches": [], "scout_reports": [], "shortlists": []}
    fake_client = FakeClient(db)

    import supabase_client
    importlib.reload(supabase_client)
    monkeypatch.setattr(supabase_client, "get_client", lambda: fake_client)

    import data_utils
    importlib.reload(data_utils)
    return data_utils, db


# ---------------- Tests ----------------
def test_list_teams(monkeypatch):
    du, db = setup_data_utils(monkeypatch)
    assert du.list_teams() == []

    # lisää joukkueita teams-tauluun
    db["teams"].extend([{"id": "t1", "name": "Team A"}, {"id": "t2", "name": "Team B"}])

    teams = du.list_teams()
    assert set(teams) == {"Team A", "Team B"}


def test_load_master_empty_when_missing(monkeypatch):
    du, db = setup_data_utils(monkeypatch)
    team = "My Team"
    df = du.load_master(team)
    assert list(df.columns) == du.MASTER_COLUMNS
    assert df.empty


def test_save_master_persists_data(monkeypatch):
    du, db = setup_data_utils(monkeypatch)
    team = "My Team"
    uuid_val = "123e4567e89b12d3a456426614174000"  # 32-merkkiä, sama formaatti kuin uuid.hex

    df_new = pd.DataFrame([{"PlayerID": uuid_val, "Name": "Alice"}])
    du.save_master(df_new, team)

    df_loaded = du.load_master(team)
    assert not df_loaded.empty
    assert df_loaded.loc[0, "PlayerID"] == uuid_val
    assert df_loaded.loc[0, "Name"] == "Alice"
