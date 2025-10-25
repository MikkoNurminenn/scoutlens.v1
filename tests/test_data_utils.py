import json
import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def data_utils(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUTLENS_APPDATA", str(tmp_path))
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(1, str(root / "app"))
    import app_paths
    importlib.reload(app_paths)
    import app.data_utils as data_utils
    importlib.reload(data_utils)
    data_utils.IS_CLOUD = False
    data_utils.PLAYERS_FP.write_text("[]", encoding="utf-8")
    return data_utils


def test_load_master_creates_empty_csv(data_utils):
    df = data_utils.load_master("Test Team")
    assert list(df.columns) == data_utils.MASTER_COLUMNS
    assert df.empty
    assert data_utils.get_team_paths("Test Team")["master"].exists()


def test_save_and_load_master_roundtrip(data_utils):
    original = pd.DataFrame({"PlayerID": [1], "Name": ["John"]})
    data_utils.save_master(original, "My Team")
    loaded = data_utils.load_master("My Team")
    assert loaded.loc[0, "PlayerID"] == 1
    assert loaded.loc[0, "Name"] == "John"


def test_list_teams_combines_sources(data_utils):
    data_utils.get_team_paths("Real Madrid")["folder"].mkdir(parents=True)
    data_utils.get_team_paths("Unknown Team")["folder"].mkdir(parents=True)
    players = [{"Team": "Real Madrid"}, {"team_name": "Bayern München"}]
    data_utils.PLAYERS_FP.write_text(json.dumps(players), encoding="utf-8")
    teams = data_utils.list_teams()
    assert teams == ["Bayern München", "Real Madrid", "UNKNOWN_TEAM"]
