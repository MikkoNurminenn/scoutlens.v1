import pytest

from app import player_editor


def test_remove_from_players_storage_by_ids_cascades(monkeypatch):
    calls = []

    class Table:
        def __init__(self, name):
            self.name = name
        def delete(self):
            calls.append((self.name, "delete"))
            return self
        def in_(self, column, values):
            calls.append((self.name, "in", column, values))
            return self
        def execute(self):
            calls.append((self.name, "execute"))
            return self
    class Client:
        def table(self, name):
            calls.append((name, "table"))
            return Table(name)

    monkeypatch.setattr(player_editor, "get_client", lambda: Client())

    n = player_editor.remove_from_players_storage_by_ids(["a", "b"])
    assert n == 2

    table_calls = [c for c in calls if c[1] == "table"]
    assert [c[0] for c in table_calls] == ["reports", "shortlists", "player_notes", "players"]
    assert ("reports", "in", "player_id", ["a", "b"]) in calls
    assert ("shortlists", "in", "player_id", ["a", "b"]) in calls
    assert ("player_notes", "in", "player_id", ["a", "b"]) in calls
    assert ("players", "in", "id", ["a", "b"]) in calls
    assert calls[-1] == ("players", "execute")
