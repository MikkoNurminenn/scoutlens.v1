import sys
from pathlib import Path
import importlib
import pandas as pd

# Ensure application modules can be imported as top-level modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))


def setup_data_utils(tmp_path, monkeypatch):
    """Return ``data_utils`` configured to use an in-memory Supabase mock."""
    monkeypatch.setenv("SCOUTLENS_APPDATA", str(tmp_path))

    import app_paths
    importlib.reload(app_paths)

    # Mock cloud storage using an in-memory dictionary
    store: dict[str, object] = {}

    import storage
    importlib.reload(storage)
    monkeypatch.setattr(storage, "IS_CLOUD", True, raising=False)

    def fake_load_json(name_or_fp, default):
        key = Path(name_or_fp).name if name_or_fp else ""
        return store.get(key, default)

    def fake_save_json(name_or_fp, data):
        key = Path(name_or_fp).name if name_or_fp else ""
        store[key] = data

    monkeypatch.setattr(storage, "load_json", fake_load_json, raising=False)
    monkeypatch.setattr(storage, "save_json", fake_save_json, raising=False)

    # Prevent real Supabase connections
    import supabase_client
    importlib.reload(supabase_client)
    monkeypatch.setattr(supabase_client, "get_client", lambda: object())

    import data_utils
    importlib.reload(data_utils)
    return data_utils


def test_list_teams(tmp_path, monkeypatch):
    du = setup_data_utils(tmp_path, monkeypatch)
    assert du.list_teams() == []

    import storage

    storage.save_json(
        "players.json",
        [
            {"team_name": "Team A"},
            {"team_name": "Team B"},
            {"team_name": "TEAM_C"},
        ],
    )

    teams = du.list_teams()
    assert "Team B" in teams
    assert "TEAM_B" not in teams
    assert set(teams) == {"Team A", "Team B", "TEAM_C"}


def test_load_master_empty_when_missing(tmp_path, monkeypatch):
    du = setup_data_utils(tmp_path, monkeypatch)
    team = "My Team"
    df = du.load_master(team)
    assert list(df.columns) == du.MASTER_COLUMNS
    assert df.empty


def test_save_master_persists_data(tmp_path, monkeypatch):
    du = setup_data_utils(tmp_path, monkeypatch)
    team = "My Team"
    df_new = pd.DataFrame([{ "PlayerID": 1, "Name": "Alice" }])
    du.save_master(df_new, team)
    df_loaded = du.load_master(team)
    assert df_loaded.loc[0, "PlayerID"] == 1
    assert df_loaded.loc[0, "Name"] == "Alice"
    assert str(df_loaded["PlayerID"].dtype) == "Int64"
