# data_utils.py — unified data helpers for ScoutLens (cloud-ready)
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import date, datetime

import pandas as pd

from schema import MASTER_FIELDS, COMMON_FIELDS, OUTFIELD_FIELDS, GK_FIELDS
from app_paths import DATA_DIR, file_path

# >>> Cloud/local storage adapter <<<
# - IS_CLOUD kertoo ollaanko pilvessä (Supabase kv) vai paikallisesti.
# - load_json/save_json tekevät automaattisesti oikean tallennuksen.
from storage import IS_CLOUD, load_json, save_json

# -----------------------------------------------------------------------------
# Directories & paths (local mode only)
# -----------------------------------------------------------------------------
BASE_DIR: Path = DATA_DIR / "teams"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# Optional shared JSON stores
# HUOM: Cloud-moodissa luetaan/tallennetaan vain tiedostonimen mukaan (fp.name)
PLAYERS_FP: Path = file_path("players.json")
SHORTLIST_PATH: Path = file_path("shortlists.json")  # keep plural

# Public re-exports (useful for other modules)
MASTER_COLUMNS = MASTER_FIELDS
DEFAULT_PLAYER_COLUMNS = COMMON_FIELDS.copy()
DEFAULT_STATS_COLUMNS = ["PlayerID", "Season", "Goals", "Assists", "MinutesPlayed"]

# -----------------------------------------------------------------------------
# Utils
# -----------------------------------------------------------------------------
def _safe_team_name(name: str) -> str:
    return (name or "").strip().replace("  ", " ").replace(" ", "_").upper()

def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def parse_date(s: Optional[str]) -> Optional[date]:
    """Muuntaa päivämäärämerkkijonon ``date``-objektiksi.

    Hyväksyy yleisiä formaatteja (``YYYY-MM-DD``, ``DD.MM.YYYY``, ``YYYY/MM/DD``).
    Palauttaa ``None`` jos arvo puuttuu tai muunnos epäonnistuu.
    """
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None

def _read_json_local(fp: Path, default: Any):
    try:
        if fp.exists():
            txt = fp.read_text(encoding="utf-8").strip()
            if txt:
                return json.loads(txt)
    except Exception:
        pass
    return default

def _read_json(fp: Path, default: Any):
    """Cloudissa luetaan kv:stä (fp.name avaimena), lokaalisti levyltä."""
    if IS_CLOUD:
        return load_json(fp.name, default)
    return _read_json_local(fp, default)

def _write_json(fp: Path, obj) -> None:
    """Cloudissa tallennus kv:hen (fp.name avaimena), lokaalisti levyyn."""
    if IS_CLOUD:
        save_json(fp.name, obj)
        return
    _ensure_parent(fp)
    fp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def get_team_paths(team_name: str, base_dir: Path = BASE_DIR) -> Dict[str, Path]:
    safe = _safe_team_name(team_name)
    root = base_dir / safe
    return {
        "folder": root,
        "master": root / "player_master.csv",
        "players": root / "players.csv",            # legacy
        "seasonal_stats": root / "seasonal_stats.csv",
    }

def list_teams() -> List[str]:
    """
    Union of teams found as subfolders under BASE_DIR (local mode)
    and teams seen in players.json (works in both modes).
    When both exist, prefer the pretty name from players.json.
    """
    # Folder names (cloudissa ei listata levyä)
    folder_names: set[str] = set()
    if not IS_CLOUD:
        folder_names = {p.name for p in BASE_DIR.iterdir() if p.is_dir()}

    # Team names from players.json (pretty names)
    pj_names: set[str] = set()
    try:
        players = _read_json(PLAYERS_FP, [])
        def _norm_team(p: dict) -> str:
            return (
                p.get("team_name")
                or p.get("Team")
                or p.get("team")
                or p.get("current_club")
                or p.get("CurrentClub")
                or ""
            ).strip()
        pj_names = {t for t in (_norm_team(p) for p in players) if t}
    except Exception:
        pj_names = set()

    # Map safe->pretty
    safe_map = { _safe_team_name(t): t for t in pj_names }

    union: set[str] = set()
    for f in folder_names:
        union.add(safe_map.get(f, f))
    union.update(pj_names)

    return sorted(t for t in union if t)

# -----------------------------------------------------------------------------
# DataFrame hygiene / JSON serialisointi
# -----------------------------------------------------------------------------
def _coerce_master(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=MASTER_COLUMNS)

    # Ensure all master columns exist
    for col in MASTER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    # PlayerID
    if "PlayerID" in df.columns:
        df["PlayerID"] = pd.to_numeric(df["PlayerID"], errors="coerce").astype("Int64")

    # DateOfBirth normalisointi (datetime/str -> date)
    if "DateOfBirth" in df.columns:
        try:
            df["DateOfBirth"] = pd.to_datetime(df["DateOfBirth"], errors="coerce").dt.date
        except Exception:
            pass

    # Stable column order
    df = df[[c for c in MASTER_COLUMNS if c in df.columns] + [c for c in df.columns if c not in MASTER_COLUMNS]]
    return df

def _coerce_seasonal(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=DEFAULT_STATS_COLUMNS)
    for col in DEFAULT_STATS_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    # Types
    if "PlayerID" in df.columns:
        df["PlayerID"] = pd.to_numeric(df["PlayerID"], errors="coerce").astype("Int64")
    if "Season" in df.columns:
        df["Season"] = df["Season"].astype(str)
    if "MinutesPlayed" in df.columns:
        df["MinutesPlayed"] = pd.to_numeric(df["MinutesPlayed"], errors="coerce").fillna(0).astype("Int64")
    return df

def _records_json_safe(df: pd.DataFrame) -> List[dict]:
    """Muuttaa DataFramen listaksi dict-objekteja JSONia varten (päivämäärät -> ISO)."""
    tmp = df.copy()
    for col in tmp.columns:
        # datetime64 -> string
        if pd.api.types.is_datetime64_any_dtype(tmp[col]):
            tmp[col] = tmp[col].astype(str)
        else:
            # date-objektit -> isoformat
            try:
                tmp[col] = tmp[col].apply(lambda x: x.isoformat() if isinstance(x, (date, datetime)) else x)
            except Exception:
                pass
    return tmp.to_dict(orient="records")

# -----------------------------------------------------------------------------
# Master table (per-team player table)
# -----------------------------------------------------------------------------
def load_master(team: str) -> pd.DataFrame:
    safe = _safe_team_name(team)

    if IS_CLOUD:
        data = load_json(f"teams/{safe}/player_master.json", default=[])
        df = pd.DataFrame(data)
        return _coerce_master(df)

    # Local (CSV)
    paths = get_team_paths(team)
    paths["folder"].mkdir(parents=True, exist_ok=True)
    p = paths["master"]
    if p.exists():
        try:
            df = pd.read_csv(p)
        except Exception:
            df = pd.DataFrame(columns=MASTER_COLUMNS)
    else:
        df = pd.DataFrame(columns=MASTER_COLUMNS)
        _ensure_parent(p); df.to_csv(p, index=False)
    return _coerce_master(df)

def save_master(df: pd.DataFrame, team: str) -> None:
    safe = _safe_team_name(team)

    if IS_CLOUD:
        save_json(f"teams/{safe}/player_master.json", _records_json_safe(_coerce_master(df)))
        return

    p = get_team_paths(team)["master"]
    _ensure_parent(p)
    _coerce_master(df).to_csv(p, index=False)

# Backwards-compat: some modules call load_players/save_players meaning master
def load_players(team: str) -> pd.DataFrame:
    return load_master(team)

def save_players(df: pd.DataFrame, team: str) -> None:
    save_master(df, team)

# -----------------------------------------------------------------------------
# Seasonal stats per team
# -----------------------------------------------------------------------------
def load_seasonal_stats(team: str) -> pd.DataFrame:
    safe = _safe_team_name(team)

    if IS_CLOUD:
        data = load_json(f"teams/{safe}/seasonal_stats.json", default=[])
        df = pd.DataFrame(data)
        return _coerce_seasonal(df)

    # Local (CSV)
    p = get_team_paths(team)["seasonal_stats"]
    if p.exists():
        try:
            df = pd.read_csv(p)
        except Exception:
            df = pd.DataFrame(columns=DEFAULT_STATS_COLUMNS)
    else:
        df = pd.DataFrame(columns=DEFAULT_STATS_COLUMNS)
        _ensure_parent(p); df.to_csv(p, index=False)
    return _coerce_seasonal(df)

def save_seasonal_stats(df: pd.DataFrame, team: str) -> None:
    safe = _safe_team_name(team)

    if IS_CLOUD:
        save_json(f"teams/{safe}/seasonal_stats.json", _records_json_safe(_coerce_seasonal(df)))
        return

    p = get_team_paths(team)["seasonal_stats"]
    _ensure_parent(p)
    _coerce_seasonal(df).to_csv(p, index=False)

# -----------------------------------------------------------------------------
# Folder bootstrap & helpers
# -----------------------------------------------------------------------------
def initialize_team_folder(team_name: str, stat_columns: Optional[List[str]] = None, base_dir: Path = BASE_DIR) -> Path:
    """
    Local: luo kansiot + tyhjät CSV:t.
    Cloud: alustaa tyhjät JSON-rivit kv:hen (ei levyä). Palauttaa "virtuaalipolun".
    """
    if IS_CLOUD:
        safe = _safe_team_name(team_name)
        # Luo tyhjät rakenteet kv:hen jos puuttuu
        if load_json(f"teams/{safe}/player_master.json", default=None) is None:
            save_json(f"teams/{safe}/player_master.json", _records_json_safe(pd.DataFrame(columns=MASTER_COLUMNS)))
        if load_json(f"teams/{safe}/seasonal_stats.json", default=None) is None:
            cols = stat_columns or DEFAULT_STATS_COLUMNS
            save_json(f"teams/{safe}/seasonal_stats.json", _records_json_safe(pd.DataFrame(columns=cols)))
        # Palautetaan symbolinen polku samaan formaattiin kuin lokaalisti
        return (base_dir / safe)

    # Local
    paths = get_team_paths(team_name, base_dir)
    paths["folder"].mkdir(parents=True, exist_ok=True)
    # players.csv (legacy)
    if not paths["players"].exists():
        pd.DataFrame(columns=DEFAULT_PLAYER_COLUMNS).to_csv(paths["players"], index=False)
    # seasonal_stats.csv
    if not paths["seasonal_stats"].exists():
        cols = stat_columns or DEFAULT_STATS_COLUMNS
        pd.DataFrame(columns=cols).to_csv(paths["seasonal_stats"], index=False)
    # player_master.csv
    if not paths["master"].exists():
        pd.DataFrame(columns=MASTER_COLUMNS).to_csv(paths["master"], index=False)
    return paths["folder"]

def ensure_team_exists(team_name: str) -> bool:
    """Create the team folder structure if it does not already exist.
    Returns True when a new folder was created.
    """
    if IS_CLOUD:
        safe = _safe_team_name(team_name)
        had_master = load_json(f"teams/{safe}/player_master.json", default=None) is not None
        had_stats  = load_json(f"teams/{safe}/seasonal_stats.json", default=None) is not None
        if had_master and had_stats:
            return False
        initialize_team_folder(team_name)
        return True

    # Local
    p = get_team_paths(team_name)["folder"]
    if p.exists():
        return False
    initialize_team_folder(team_name)
    return True

def validate_player_input(name: str, df: pd.DataFrame) -> Tuple[bool, str]:
    """Minimal validation helper for Player Editor."""
    nm = (name or "").strip()
    if not nm:
        return False, "Name cannot be empty."
    if "Name" in df.columns and nm in df["Name"].astype(str).tolist():
        return False, "Player name already exists."
    return True, ""
