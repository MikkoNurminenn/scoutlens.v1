import sys
from pathlib import Path
import importlib
import uuid

# Salli "app" -moduulit
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

# ---------------- In-memory Supabase mock ----------------
class FakeTable:
    def __init__(self, name, db):
        self.name = name
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

    def order(self, column, desc=False):
        self._order = (column, bool(desc))
        return self

    # insert/upsert minimalistit riittävät teams-tauluun
    def insert(self, item):
        if "id" not in item or not item["id"]:
            item["id"] = uuid.uuid4().hex
        self._data.append(dict(item))
        return self

    def upsert(self, data):
        items = data if isinstance(data, list) else [data]
        for item in items:
            if "id" not in item or not item["id"]:
                item["id"] = uuid.uuid4().hex
            # upsert yksinkertaisesti: korvaa jos sama nimi löytyy
            replaced = False
            for i, row in enumerate(self._data):
                if str(row.get("name","")).strip().lower() == str(item.get("name","")).strip().lower():
                    self._data[i] = {**row, **item}
                    replaced = True
                    break
            if not replaced:
                self._data.append(dict(item))
        return self

    def delete(self):
        return self

    def execute(self):
        data = list(self._data)
        for op, col, val in self._filters:
            if op == "eq":
                data = [r for r in data if r.get(col) == val]
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
def setup_teams_store(monkeypatch):
    """
    Palauttaa teams_store-moduulin, joka käyttää in-memory Supabase-mockia.
    """
    db = {"teams": []}
    fake_client = FakeClient(db)

    import supabase_client
    importlib.reload(supabase_client)
    monkeypatch.setattr(supabase_client, "get_client", lambda: fake_client)

    import teams_store
    importlib.reload(teams_store)
    return teams_store, db

# ---------------- Tests ----------------
def test_add_team_success(monkeypatch):
    ts, db = setup_teams_store(monkeypatch)
    ok, info = ts.add_team("Testers")
    assert ok is True
    assert "Testers" in ts.list_teams()

def test_add_team_duplicate_case_insensitive(monkeypatch):
    ts, db = setup_teams_store(monkeypatch)
    assert ts.add_team("Santos")[0] is True
    ok, msg = ts.add_team("santos")  # case-insensitive duplikaatti
    assert ok is False
    assert "exist" in msg.lower()

def test_list_teams_sorted(monkeypatch):
    ts, db = setup_teams_store(monkeypatch)
    for n in ["Boca Juniors", "River Plate", "Atlético Nacional"]:
        assert ts.add_team(n)[0] is True
    teams = ts.list_teams()
    assert teams == sorted(teams)
