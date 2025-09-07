# data_utils.py — Supabase-backed helpers (clean)
from __future__ import annotations

from __future__ import annotations

from pathlib import Path
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import math
import numpy as np
import pandas as pd

from postgrest.exceptions import APIError
from app.schema import MASTER_FIELDS, COMMON_FIELDS
from app.supabase_client import get_client
from app.utils.supa import first_row

# Yhteensopivuus: jotkin moduulit odottavat BASE_DIR -muuttujaa
BASE_DIR = Path(".")

# Julkiset re-exportit
MASTER_COLUMNS = MASTER_FIELDS
DEFAULT_PLAYER_COLUMNS = COMMON_FIELDS.copy()
DEFAULT_STATS_COLUMNS = ["PlayerID", "Season", "Goals", "Assists", "MinutesPlayed"]

# Columns that are persisted in the Supabase ``players`` table
PLAYERS_COLUMNS = [
    "id","external_id","team_id","team_name","name","nationality",
    "date_of_birth","preferred_foot","club_number","position",
    "scout_rating","transfermarkt_url","notes",
]


# ---------------------------------------------------------------------------
# JSON sanitizing
# ---------------------------------------------------------------------------
def _to_json_safe(obj: Any) -> Any:
    """Recursively convert obj to JSON-safe primitives for PostgREST."""
    if obj is None or isinstance(obj, (bool, str, int)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, (np.generic,)):
        return _to_json_safe(obj.item())
    if isinstance(obj, (pd.Timestamp, datetime)):
        if pd.isna(obj):
            return None
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if obj is pd.NaT or (isinstance(obj, float) and math.isnan(obj)):
        return None
    if isinstance(obj, Decimal):
        f = float(obj)
        return f if math.isfinite(f) else None
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_json_safe(v) for v in obj]
    return str(obj)


def _assert_json_serializable(records: List[Dict[str, Any]]) -> None:
    import json
    for idx, r in enumerate(records):
        json.dumps(r, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


# ---------------------------------------------------------------------------
# Päivämääräapureita
# ---------------------------------------------------------------------------
def parse_date(s: Optional[str | date | datetime]) -> Optional[date]:
    """Muunna erilaiset merkkijonot/objektit turvallisesti date-objektiksi."""
    if s is None or s == "" or (isinstance(s, float) and pd.isna(s)):
        return None
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    if isinstance(s, datetime):
        return s.date()
    s = str(s).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    # viimeinen oljenkorsi: pandas parseri
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.isna(dt):
            return None
        if isinstance(dt, pd.Timestamp):
            return dt.date()
    except Exception:
        pass
    return None


def _ser_date(d: Optional[date | datetime]) -> Optional[str]:
    """Serialisoi date/datetime → 'YYYY-MM-DD' merkkijono (tai None)."""
    if d is None:
        return None
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# DataFrame-kohdistus ja turvallinen sarjoitus
# ---------------------------------------------------------------------------
def _coerce_master(df: pd.DataFrame) -> pd.DataFrame:
    """Varmista MASTER_COLUMNS, PlayerID stringiksi, DateOfBirth → date-objekti."""
    if df is None or df.empty:
        return pd.DataFrame(columns=MASTER_COLUMNS)

    # Lisää puuttuvat sarakkeet tyhjinä
    for col in MASTER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    # PlayerID aina string (UUID) — ei Int64
    if "PlayerID" in df.columns:
        df["PlayerID"] = df["PlayerID"].astype(str).fillna("")

    # DateOfBirth DataFrameen python date-objektina (ei NaT) → toimii st.date_inputissa
    if "DateOfBirth" in df.columns:
        df["DateOfBirth"] = df["DateOfBirth"].apply(parse_date)

    # Pidä stabiili sarakejärjestys
    ordered = [c for c in MASTER_COLUMNS if c in df.columns]
    rest = [c for c in df.columns if c not in ordered]
    df = df[ordered + rest]
    return df


def _coerce_seasonal(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=DEFAULT_STATS_COLUMNS)
    for col in DEFAULT_STATS_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    # PlayerID string
    if "PlayerID" in df.columns:
        df["PlayerID"] = df["PlayerID"].astype(str).fillna("")

    # Season string
    if "Season" in df.columns:
        df["Season"] = df["Season"].astype(str)

    # MinutesPlayed numero (Int64) mutta NaN→0
    if "MinutesPlayed" in df.columns:
        df["MinutesPlayed"] = (
            pd.to_numeric(df["MinutesPlayed"], errors="coerce").fillna(0).astype("Int64")
        )
    return df


def _records_json_safe(df: pd.DataFrame) -> List[dict]:
    """Return a list of JSON-serializable dicts for the given DataFrame."""
    if df is None:
        return []
    recs = df.to_dict(orient="records")
    return [_to_json_safe(r) for r in recs]


# ---------------------------------------------------------------------------
# Supabase-toiminnot
# ---------------------------------------------------------------------------
def list_teams() -> List[str]:
    client = get_client()
    if not client:
        return []
    r = client.table("teams").select("name").order("name").execute()
    return [row["name"] for row in (r.data or []) if row.get("name")]


def load_players(team_name: str | None = None) -> pd.DataFrame:
    client = get_client()
    if not client:
        return pd.DataFrame()
    q = client.table("players").select("*")
    if team_name:
        q = q.eq("team_name", team_name)
    res = q.execute()
    return pd.DataFrame(res.data or [])


def save_players(
    df: pd.DataFrame,
    team_name: str | None = None,
    *,
    batch_size: int = 500,
    debug: bool = False,
) -> None:
    client = get_client()
    if not client or df is None or df.empty:
        return
    if team_name and "team_name" not in df.columns:
        df = df.assign(team_name=team_name)
    df = df.replace({np.nan: None})
    cols = [c for c in PLAYERS_COLUMNS if c in df.columns]
    records_raw = df[cols].to_dict(orient="records")
    records = [_to_json_safe(r) for r in records_raw]

    if debug:
        try:
            _assert_json_serializable(records[:5])
        except Exception as e:
            first = records[:1] or [{}]
            print(
                "\U0001F534 JSON not safe at row 0",
                "error:",
                repr(e),
                "record snippet:",
                {k: first[0].get(k) for k in list(first[0])[:8]},
            )
            raise

    table = client.table("players")
    for i in range(0, len(records), batch_size):
        chunk = records[i:i + batch_size]
        if not chunk:
            continue
        try:
            table.upsert(chunk, on_conflict="id").execute()
        except TypeError:
            table.upsert(chunk).execute()


def load_master(team: str) -> pd.DataFrame:
    df = load_players(team)
    if not df.empty:
        df = df.rename(columns={"id": "PlayerID", "name": "Name"})
    return _coerce_master(df)


def save_master(
    df: pd.DataFrame,
    team: str,
    *,
    batch_size: int = 500,
    debug: bool = False,
) -> None:
    if df is None:
        return
    df = _coerce_master(df)
    df = df.rename(columns={"PlayerID": "id", "Name": "name"})
    df["team_name"] = team
    save_players(df, batch_size=batch_size, debug=debug)


def list_players_by_team(team: str) -> List[Dict[str, Any]]:
    """Palauta tiimin pelaajat dict-listana (id/name/team_name mukaan)."""
    df = load_master(team)
    if df is None or df.empty:
        return []
    recs = _records_json_safe(df)
    for r in recs:
        r["id"] = str(r.get("PlayerID") or r.get("id") or "")
        r["name"] = r.get("Name", "")
        r["team_name"] = team
    return recs


# Seasonal stats (voit säätää taulun nimen/kolumnit oman skeeman mukaan)
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
    """Supabase-versiossa varmistetaan tiimin olemassaolo ja palautetaan symbolinen polku."""
    client = get_client()
    if client:
        client.table("teams").upsert({"name": team_name}).execute()
    return Path(team_name)  # symbolinen (yhteensopivuus muun koodin kanssa)


def ensure_team_exists(team_name: str) -> bool:
    """True jos luotiin, False jos oli jo olemassa."""
    client = get_client()
    if not client:
        return False
    res = client.table("teams").select("name").eq("name", team_name).execute()
    if res.data:
        return False
    client.table("teams").insert({"name": team_name}).execute()
    return True


# ---------------------------------------------------------------------------
# Quick player insert
# ---------------------------------------------------------------------------
_ALLOWED = {
    "players": {
        "name",
        "position",
        "preferred_foot",
        "nationality",
        "current_club",
        "date_of_birth",
        "transfermarkt_url",
        "notes",
    }
}


def _filter_cols(table: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: v
        for k, v in (payload or {}).items()
        if k in _ALLOWED.get(table, set()) and v not in (None, "")
    }


def insert_player_quick(data: Dict[str, Any]) -> Dict[str, Any]:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Name is required")
    payload = _filter_cols("players", data)
    payload["name"] = name
    sb = get_client()
    try:
        res = sb.table("players").insert(payload).execute()
    except APIError as e:
        raise e
    return first_row(res) or {}


def validate_player_input(name: str, df: pd.DataFrame) -> Tuple[bool, str]:
    nm = (name or "").strip()
    if not nm:
        return False, "Name cannot be empty."
    if "Name" in df.columns and nm in df["Name"].astype(str).tolist():
        return False, "Player name already exists."
    return True, ""


# ---------------------------------------------------------------------------
# Yhteensopivuus: polkujen "generointi" (ei käytä enää tiedostoja)
# ---------------------------------------------------------------------------
def get_team_paths(team_name: str, base_dir: Path | None = None) -> Dict[str, Path]:
    """Palauta symboliset polut jotta legacy-koodi ei hajoa."""
    base = Path(base_dir) if base_dir else Path(".")
    root = base / team_name
    return {
        "folder": root,
        "master": root / "player_master.csv",
        "players": root / "players.csv",
        "seasonal_stats": root / "seasonal_stats.csv",
    }
