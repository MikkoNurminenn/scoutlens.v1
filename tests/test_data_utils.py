import sys
from pathlib import Path
import importlib
import json
import pandas as pd

# Ensure application modules can be imported as top-level modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))


def setup_data_utils(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUTLENS_APPDATA", str(tmp_path))
    import app_paths
    importlib.reload(app_paths)
    import storage
    monkeypatch.setattr(storage, "IS_CLOUD", False)
    import data_utils
    importlib.reload(data_utils)
    return data_utils


def test_list_teams(tmp_path, monkeypatch):
    du = setup_data_utils(tmp_path, monkeypatch)
    assert du.list_teams() == []
    du.PLAYERS_FP.write_text(
        json.dumps([{ "team_name": "Team A" }, { "team_name": "Team B" }]),
        encoding="utf-8",
    )
    du.get_team_paths("Team B")["folder"].mkdir(parents=True, exist_ok=True)
    du.get_team_paths("Team C")["folder"].mkdir(parents=True, exist_ok=True)
    teams = du.list_teams()
    assert "Team B" in teams
    assert "TEAM_B" not in teams
    assert set(teams) == {"Team A", "Team B", "TEAM_C"}


def test_load_master_creates_file(tmp_path, monkeypatch):
    du = setup_data_utils(tmp_path, monkeypatch)
    team = "My Team"
    master_path = du.get_team_paths(team)["master"]
    assert not master_path.exists()
    df = du.load_master(team)
    assert master_path.exists()
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
