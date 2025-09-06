# data_utils.py — Supabase-backed helpers
from __future__ import annotations

from pathlib import Path
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from schema import MASTER_FIELDS, COMMON_FIELDS
from supabase_client import get_client

# Compatibility placeholder for modules that still expect a BASE_DIR
BASE_DIR = Path(".")

# Public re-exports
MASTER_COLUMNS = MASTER_FIELDS
DEFAULT_PLAYER_COLUMNS = COMMON_FIELDS.copy()
DEFAULT_STATS_COLUMNS = ["PlayerID", "Season", "Goals", "Assists", "MinutesPlayed"]


def parse_date(s: Optional[str]) -> Optional[date]:
    """Parse a date string into a ``date`` object."""

    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# DataFrame helpers
# ---------------------------------------------------------------------------
def _coerce_master(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=MASTER_COLUMNS)
    for col in MASTER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    if "PlayerID" in df.columns:
        df["PlayerID"] = pd.to_numeric(df["PlayerID"], errors="coerce").astype("Int64")
    if "DateOfBirth" in df.columns:
        try:
            df["DateOfBirth"] = pd.to_datetime(df["DateOfBirth"], errors="coerce").dt.date
        except Exception:
            pass
    df = df[[c for c in MASTER_COLUMNS if c in df.columns] + [c for c in df.columns if c not in MASTER_COLUMNS]]
    return df


def _coerce_seasonal(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=DEFAULT_STATS_COLUMNS)
    for col in DEFAULT_STATS_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    if "PlayerID" in df.columns:
        df["PlayerID"] = pd.to_numeric(df["PlayerID"], errors="coerce").astype("Int64")
    if "Season" in df.columns:
        df["Season"] = df["Season"].astype(str)
    if "MinutesPlayed" in df.columns:
        df["MinutesPlayed"] = pd.to_numeric(df["MinutesPlayed"], errors="coerce").fillna(0).astype("Int64")
    return df


def _records_json_safe(df: pd.DataFrame) -> List[dict]:
    tmp = df.copy()
    for col in tmp.columns:
        if pd.api.types.is_datetime64_any_dtype(tmp[col]):
            tmp[col] = tmp[col].astype(str)
        else:
            try:
                tmp[col] = tmp[col].apply(
                    lambda x: x.isoformat() if isinstance(x, (date, datetime)) else x
                )
            except Exception:
                pass
    return tmp.to_dict(orient="records")


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------
def list_teams() -> List[str]:
    client = get_client()
    if not client:
        return []
    res = client.table("teams").select("name").execute()
    return sorted(r.get("name") for r in (res.data or []) if r.get("name"))


def load_master(team: str) -> pd.DataFrame:
    client = get_client()
    if not client:
        return pd.DataFrame(columns=MASTER_COLUMNS)
    res = client.table("players").select("*").eq("team_name", team).execute()
    df = pd.DataFrame(res.data or [])
    return _coerce_master(df)


def save_master(df: pd.DataFrame, team: str) -> None:
    client = get_client()
    if not client:
        return
    data = _records_json_safe(_coerce_master(df))
    for row in data:
        row["team_name"] = team
    client.table("players").upsert(data).execute()


def load_players(team: str) -> pd.DataFrame:
    return load_master(team)


def save_players(df: pd.DataFrame, team: str) -> None:
    save_master(df, team)


def load_seasonal_stats(team: str) -> pd.DataFrame:
    client = get_client()
    if not client:
        return pd.DataFrame(columns=DEFAULT_STATS_COLUMNS)
    res = client.table("matches").select("*").eq("team_name", team).execute()
    df = pd.DataFrame(res.data or [])
    return _coerce_seasonal(df)


def save_seasonal_stats(df: pd.DataFrame, team: str) -> None:
    client = get_client()
    if not client:
        return
    data = _records_json_safe(_coerce_seasonal(df))
    for row in data:
        row["team_name"] = team
    client.table("matches").upsert(data).execute()


def initialize_team_folder(team_name: str, stat_columns: Optional[List[str]] = None, base_dir: Path | None = None) -> Path:
    client = get_client()
    if client:
        client.table("teams").upsert({"name": team_name}).execute()
    # Return a symbolic path for compatibility
    return Path(team_name)


def ensure_team_exists(team_name: str) -> bool:
    client = get_client()
    if not client:
        return False
    res = client.table("teams").select("name").eq("name", team_name).execute()
    if res.data:
        return False
    client.table("teams").insert({"name": team_name}).execute()
    return True


def validate_player_input(name: str, df: pd.DataFrame) -> Tuple[bool, str]:
    nm = (name or "").strip()
    if not nm:
        return False, "Name cannot be empty."
    if "Name" in df.columns and nm in df["Name"].astype(str).tolist():
        return False, "Player name already exists."
    return True, ""


# ---------------------------------------------------------------------------
# Compatibility helpers
# ---------------------------------------------------------------------------
def get_team_paths(team_name: str, base_dir: Path | None = None) -> Dict[str, Path]:
    base = Path(base_dir) if base_dir else Path(".")
    root = base / team_name
    return {
        "folder": root,
        "master": root / "player_master.csv",
        "players": root / "players.csv",
        "seasonal_stats": root / "seasonal_stats.csv",
    }

