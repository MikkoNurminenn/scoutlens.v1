import pytest


def test_remove_players_deletes_children(monkeypatch):
    calls = []

    class FakeTable:
        def __init__(self, name):
            self.name = name
        def delete(self):
            calls.append((self.name, "delete"))
            return self
        def in_(self, col, vals):
            calls.append((self.name, "in", col, list(vals)))
            return self
        def execute(self):
            calls.append((self.name, "execute"))
            return {"status": 200}
    class FakeClient:
        def table(self, name):
            return FakeTable(name)

    from tools.db_delete_helpers import remove_players_from_storage_by_ids
    remove_players_from_storage_by_ids(FakeClient(), ["p1", "p2"])

    assert calls[0][0] == "reports"
    assert calls[3][0] == "shortlist_items"
    assert calls[-3][0] == "players"
