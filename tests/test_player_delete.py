import pytest

from app import player_editor


def test_remove_from_players_storage_by_ids_cascades(monkeypatch):
    calls = []

    class Table:
        def __init__(self, name):
            self.name = name
            self.mode = None
        def delete(self):
            calls.append((self.name, "delete"))
            self.mode = "delete"
            return self
        def in_(self, column, values):
            calls.append((self.name, "in", column, values))
            return self
        def select(self, cols):
            calls.append((self.name, "select", cols))
            self.mode = "select"
            return self
        def contains(self, column, values):
            calls.append((self.name, "contains", column, values))
            return self
        def update(self, data):
            calls.append((self.name, "update", data))
            self.mode = "update"
            return self
        def eq(self, column, value):
            calls.append((self.name, "eq", column, value))
            return self
        def execute(self):
            calls.append((self.name, "execute"))
            if self.name == "shortlists" and self.mode == "select":
                class Res:
                    pass
                res = Res()
                res.data = [
                    {"id": "s1", "player_ids": ["a", "x"]},
                    {"id": "s2", "player_ids": ["b"]},
                ]
                return res
            return self
    class Client:
        def table(self, name):
            calls.append((name, "table"))
            return Table(name)

    monkeypatch.setattr(player_editor, "get_client", lambda: Client())

    n = player_editor.remove_from_players_storage_by_ids(["a", "b"])
    assert n == 2

    table_calls = [c for c in calls if c[1] == "table"]
    assert table_calls[0][0] == "reports"
    assert table_calls[-1][0] == "players"

    # Ensure cascading deletes
    assert ("reports", "in", "player_id", ["a", "b"]) in calls
    assert ("notes", "in", "player_id", ["a", "b"]) in calls
    assert ("players", "in", "id", ["a", "b"]) in calls

    # Shortlists should be selected and updated, not deleted
    assert ("shortlists", "delete") not in [c[:2] for c in calls]
    assert ("shortlists", "select", "id, player_ids") in calls
    assert ("shortlists", "contains", "player_ids", ["a", "b"]) in calls
    assert ("shortlists", "update", {"player_ids": ["x"]}) in calls
    assert ("shortlists", "eq", "id", "s1") in calls
    assert ("shortlists", "update", {"player_ids": []}) in calls
    assert ("shortlists", "eq", "id", "s2") in calls

    # Updates must execute before player deletions
    shortlist_exec_indices = [i for i, c in enumerate(calls) if c[0] == "shortlists" and c[1] == "execute"]
    players_exec_index = calls.index(("players", "execute"))
    assert shortlist_exec_indices and max(shortlist_exec_indices) < players_exec_index
    assert calls[-1] == ("players", "execute")
