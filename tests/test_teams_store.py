import sys
from pathlib import Path
from importlib import reload

# Ensure application modules can be imported as top-level modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))


def setup_teams_store(tmp_path, monkeypatch):
    """Return ``teams_store`` using an in-memory mock instead of files."""
    monkeypatch.setattr("app_paths.DATA_DIR", tmp_path, raising=False)

    import teams_store
    reload(teams_store)

    store: list[str] = []

    def fake_load(fp, default):
        return store or default

    def fake_save(fp, obj):
        store.clear()
        store.extend(obj)

    monkeypatch.setattr(teams_store, "_load", fake_load, raising=False)
    monkeypatch.setattr(teams_store, "_save", fake_save, raising=False)

    # Avoid real Supabase lookups
    import supabase_client
    reload(supabase_client)
    monkeypatch.setattr(supabase_client, "get_client", lambda: object())

    return teams_store


def test_add_team_success(tmp_path, monkeypatch):
    ts = setup_teams_store(tmp_path, monkeypatch)
    ok, _ = ts.add_team("Testers")
    assert ok is True
    assert "Testers" in ts.list_teams()


def test_add_team_duplicate(tmp_path, monkeypatch):
    ts = setup_teams_store(tmp_path, monkeypatch)
    assert ts.add_team("Santos")[0] is True
    ok, msg = ts.add_team("santos")   # case-insensitive
    assert ok is False
    assert "exists" in msg.lower()
