import sys
from pathlib import Path

# Ensure application modules can be imported as top-level modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from teams_store import add_team, list_teams
import app_paths

def test_add_team_success(tmp_path, monkeypatch):
    monkeypatch.setattr("app_paths.DATA_DIR", tmp_path, raising=False)
    from importlib import reload
    import teams_store
    reload(teams_store)

    ok, info = teams_store.add_team("Testers")
    assert ok is True
    assert (tmp_path / "teams" / "Testers" / "players.json").exists()
    assert "Testers" in teams_store.list_teams()


def test_add_team_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr("app_paths.DATA_DIR", tmp_path, raising=False)
    from importlib import reload
    import teams_store
    reload(teams_store)

    assert teams_store.add_team("Santos")[0] is True
    ok, msg = teams_store.add_team("santos")   # case-insensitive
    assert ok is False
    assert "exists" in msg.lower()
