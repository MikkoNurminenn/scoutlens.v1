# tests/test_player_editor.py
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
            calls.append((self.name, "in", column, list(values)))
            return self
        # no-ops to guard against accidental calls
        def select(self, cols):
            calls.append((self.name, "select", cols))
            return self
        def contains(self, column, values):
            calls.append((self.name, "contains", column, list(values)))
            return self
        def update(self, data):
            calls.append((self.name, "update", data))
            return self
        def eq(self, column, value):
            calls.append((self.name, "eq", column, value))
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

    # Order of table usage
    table_calls = [c for c in calls if c[1] == "table"]
    assert [c[0] for c in table_calls] == [
        "reports",
        "shortlist_items",
        "player_notes",
        "players",
    ]

    # Correct filters applied
    assert ("reports", "in", "player_id", ["a", "b"]) in calls
    assert ("shortlist_items", "in", "player_id", ["a", "b"]) in calls
    assert ("player_notes", "in", "player_id", ["a", "b"]) in calls
    assert ("players", "in", "id", ["a", "b"]) in calls

    # Executes happen; players execute is last
    exec_indices = {name: [i for i, x in enumerate(calls) if x[:2] == (name, "execute")] for name in [
        "reports", "shortlist_items", "player_notes", "players"
    ]}
    assert all(exec_indices[name] for name in ["reports", "shortlist_items", "player_notes", "players"])  # all executed
    assert calls[-1] == ("players", "execute")

    # Ensure we are not doing array-based shortlist surgery anymore
    forbidden = [
        ("shortlists", "select", "id, player_ids"),
        ("shortlists", "contains", "player_ids", ["a", "b"]),
        ("shortlists", "update", {"player_ids": ["x"]}),
        ("shortlist_items", "select", "id, player_ids"),
        ("shortlist_items", "contains", "player_ids", ["a", "b"]),
        ("shortlist_items", "update", {"player_ids": ["x"]}),
    ]
    for f in forbidden:
        assert f not in calls
