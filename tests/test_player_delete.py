# tests/test_player_editor.py
import pytest
from types import SimpleNamespace

from app import player_editor
from postgrest.exceptions import APIError


def test_remove_from_players_storage_by_ids_cascades(monkeypatch):
    calls = []
    helper_calls = []

    def fake_remove_players_from_shortlist(*, client, shortlist_id, player_ids):
        helper_calls.append((shortlist_id, list(player_ids)))
        return len(list(player_ids))

    class Table:
        def __init__(self, name):
            self.name = name
            self._op = None
            self._in_values = []
        def delete(self):
            calls.append((self.name, "delete"))
            return self
        def in_(self, column, values):
            calls.append((self.name, "in", column, list(values)))
            self._in_values = list(values)
            return self
        # no-ops to guard against accidental calls
        def select(self, cols):
            calls.append((self.name, "select", cols))
            self._op = "select"
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
            if self.name == "shortlists_items" and self._op == "select":
                class Resp:
                    data = [{"shortlist_id": "sl1", "player_id": v} for v in self._in_values]
                return Resp()
            return self

    class Client:
        def table(self, name):
            calls.append((name, "table"))
            return Table(name)

    monkeypatch.setattr(player_editor, "get_client", lambda: Client())
    monkeypatch.setattr(player_editor, "remove_players_from_shortlist", fake_remove_players_from_shortlist)

    n = player_editor.remove_from_players_storage_by_ids(["a", "b"])
    assert n == 2

    # Order of table usage
    table_calls = [c for c in calls if c[1] == "table"]
    assert [c[0] for c in table_calls] == [
        "reports",
        "shortlists_items",
        "player_notes",
        "players",
    ]

    # Correct filters applied
    assert ("reports", "in", "player_id", ["a", "b"]) in calls
    assert ("shortlists_items", "select", "shortlist_id, player_id") in calls
    assert ("shortlists_items", "in", "player_id", ["a", "b"]) in calls
    assert ("player_notes", "in", "player_id", ["a", "b"]) in calls
    assert ("players", "in", "id", ["a", "b"]) in calls

    # Executes happen; players execute is last
    exec_indices = {name: [i for i, x in enumerate(calls) if x[:2] == (name, "execute")] for name in [
        "reports", "shortlists_items", "player_notes", "players"
    ]}
    assert all(exec_indices[name] for name in ["reports", "shortlists_items", "player_notes", "players"])  # all executed
    assert calls[-1] == ("players", "execute")

    # Helper called with expected parameters
    assert helper_calls == [("sl1", ["a", "b"])]

    # Ensure we are not doing array-based shortlist surgery anymore
    forbidden = [
        ("shortlists", "select", "id, player_ids"),
        ("shortlists", "contains", "player_ids", ["a", "b"]),
        ("shortlists", "update", {"player_ids": ["x"]}),
    ]
    for f in forbidden:
        assert f not in calls


def test_remove_from_players_storage_by_ids_fallback(monkeypatch):
    calls = []

    class Table:
        def __init__(self, name):
            self.name = name
            self._data = []

        def delete(self):
            calls.append((self.name, "delete"))
            return self

        def in_(self, column, values):
            calls.append((self.name, "in", column, list(values)))
            return self

        def select(self, cols):
            calls.append((self.name, "select", cols))
            if self.name == "shortlists":
                self._data = [{"id": "sl1", "player_ids": ["a"]}]
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
            if self.name == "shortlist_items":
                raise APIError({"message": "column shortlists.player_id does not exist", "code": "42703"})
            return SimpleNamespace(data=self._data)

    class Client:
        def table(self, name):
            calls.append((name, "table"))
            return Table(name)

    monkeypatch.setattr(player_editor, "get_client", lambda: Client())

    n = player_editor.remove_from_players_storage_by_ids(["a"])
    assert n == 1

    # Fallback path hits shortlists operations
    assert ("shortlists", "select", "id, player_ids") in calls
    assert ("shortlists", "update", {"player_ids": []}) in calls
