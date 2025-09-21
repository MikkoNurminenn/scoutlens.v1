import streamlit as st
import pandas as pd
from uuid import uuid4
from typing import Any, Dict, Iterable, List, Optional, Set

from postgrest.exceptions import APIError

from app.supabase_client import get_client

# yritetään käyttää list_teams(), mutta ei ole pakollinen
try:
    from app.data_utils import list_teams  # type: ignore
except Exception:  # pragma: no cover - fallback mode
    list_teams = None  # type: ignore


_BASE_PLAYER_COLUMNS: Set[str] = {
    "id",
    "name",
    "team_name",
    "team_id",
    "date_of_birth",
    "nationality",
    "preferred_foot",
    "club_number",
    "primary_position",
    "secondary_positions",
    "notes",
    "tags",
    "height",
    "weight",
    "position",
    "scout_rating",
    "transfermarkt_url",
    "external_id",
    "photo_path",
}


def _show_error(prefix: str, err: Exception) -> None:
    msg = getattr(err, "message", str(err))
    st.error(f"{prefix}: {msg}")


def _load_players(team: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
    query = client.table("players").select("*")
    if team:
        query = query.eq("team_name", team)
    try:
        res = query.execute()
    except APIError as err:  # pragma: no cover - UI feedback
        _show_error("Failed to load players from Supabase", err)
        return []
    return [dict(row) for row in (res.data or [])]


def _fetch_team_record(team: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    if not client or not team:
        return None
    try:
        res = (
            client.table("teams")
            .select("id,name")
            .eq("name", team)
            .limit(1)
            .execute()
        )
    except APIError as err:  # pragma: no cover - UI feedback
        _show_error("Failed to resolve team in Supabase", err)
        return None
    rows = res.data or []
    return dict(rows[0]) if rows else None

def _norm_team(p: dict) -> str:
    return (
        p.get("team_name")
        or p.get("Team")
        or p.get("team")
        or p.get("current_club")
        or p.get("CurrentClub")
        or ""
    ).strip()

def _to_df(players_for_team: list) -> pd.DataFrame:
    if not players_for_team:
        return pd.DataFrame(columns=["id", "name", "team_name"])

    # kerää kaikki kentät, jotta editori näyttää kaiken
    cols = set()
    for p in players_for_team:
        cols.update(p.keys())
    if not cols:
        cols = {"id", "name", "team_name"}

    rows = []
    for p in players_for_team:
        rows.append({c: p.get(c, None) for c in cols})
    df = pd.DataFrame(rows)

    # varmista id/name/team_name
    if "id" not in df.columns:
        if "PlayerID" in df.columns:
            df.rename(columns={"PlayerID": "id"}, inplace=True)
        else:
            df["id"] = ""
    if "name" not in df.columns and "Name" in df.columns:
        df.rename(columns={"Name": "name"}, inplace=True)
    if "team_name" not in df.columns:
        for c in ["team", "Team", "current_club", "CurrentClub"]:
            if c in df.columns:
                df["team_name"] = df[c]
                break
        if "team_name" not in df.columns:
            df["team_name"] = ""
    return df

def _clean_val(v):
    if pd.isna(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    try:
        import numpy as np

        if isinstance(v, np.integer):
            return int(v)
        if isinstance(v, np.floating):
            return float(v)
    except Exception:  # pragma: no cover - numpy optional in tests
        pass
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    return v


def _ensure_iterable(value) -> Optional[list]:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        return items or None
    if isinstance(value, Iterable) and not isinstance(value, (bytes, str)):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned or None
    return None


def _collect_allowed_columns(players_for_team: Iterable[Dict[str, Any]]) -> Set[str]:
    cols = set(_BASE_PLAYER_COLUMNS)
    for row in players_for_team:
        cols.update(row.keys())
    return cols


def _prepare_payload(
    row: Dict[str, Any],
    *,
    team: str,
    allowed: Set[str],
    team_id: Optional[str],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    # Include legacy uppercase keys when available
    name = row.get("name") or row.get("Name") or ""
    payload["name"] = str(name).strip()
    payload["team_name"] = team
    pid = (
        str(row.get("id") or "").strip()
        or str(row.get("PlayerID") or "").strip()
    )
    if not pid:
        pid = uuid4().hex
    payload["id"] = pid

    if team_id:
        payload.setdefault("team_id", team_id)

    for col in allowed:
        if col in ("id", "name", "team_name", "team_id"):
            continue
        if col in row:
            cleaned = _clean_val(row[col])
            if col in {"secondary_positions", "tags"}:
                cleaned = _ensure_iterable(row[col])
            if col in {"club_number", "height", "weight", "scout_rating"} and cleaned not in (None, ""):
                try:
                    cleaned = int(cleaned)
                except Exception:
                    cleaned = None
            if cleaned is not None:
                payload[col] = cleaned
            else:
                payload[col] = None
    return payload

# ---------- UI ----------
def show_data_manager():
    st.title("🛠️ ScoutLens Data Manager (Supabase)")
    st.caption("Edits sync directly with the Supabase `players` table.")

    # 1) Valitse joukkue
    team = st.session_state.get("selected_team")
    if not team:
        teams: List[str] = []
        if callable(list_teams):
            try:
                teams = list_teams() or []
            except Exception:
                teams = []
        if not teams:
            all_players = _load_players()
            teams = sorted({_norm_team(p) for p in all_players if _norm_team(p)})
        team = st.selectbox("Select a team to manage:", teams) if teams else None
        if team:
            st.session_state["selected_team"] = team

    if not team:
        st.warning("Please select a team to manage.")
        return

    team_players = _load_players(team)
    df = _to_df(team_players)

    st.subheader(f"Players for {team}")
    try:
        edited = st.data_editor(
            df,
            key="dm_players_editor",
            num_rows="dynamic",
            use_container_width=True,
        )
    except AttributeError:  # pragma: no cover - Streamlit fallback
        st.error("Editable data grid not available in this Streamlit version.")
        st.dataframe(df)
        return

    allowed = _collect_allowed_columns(team_players)

    if st.button("Save Changes", key="dm_save_players", type="primary"):
        client = get_client()
        if not client:
            st.error("Supabase client is not configured.")
            return
        team_row = _fetch_team_record(team)
        team_id = team_row.get("id") if team_row else None

        new_rows: List[Dict[str, Any]] = []
        for _, row in edited.iterrows():
            payload = _prepare_payload(row.to_dict(), team=team, allowed=allowed, team_id=team_id)
            new_rows.append(payload)

        existing_ids = {str(p.get("id")) for p in team_players if p.get("id")}
        new_ids = {str(row.get("id")) for row in new_rows if row.get("id")}
        removed_ids = [pid for pid in existing_ids - new_ids if pid]

        try:
            if removed_ids:
                client.table("players").delete().in_("id", removed_ids).execute()
            if new_rows:
                try:
                    client.table("players").upsert(new_rows, on_conflict="id").execute()
                except TypeError:
                    client.table("players").upsert(new_rows).execute()
            st.cache_data.clear()
            st.success(f"Player data for {team} saved to Supabase.")
        except APIError as err:  # pragma: no cover - UI feedback
            _show_error("Failed to save players", err)
        except Exception as err:  # pragma: no cover - unexpected
            st.error(f"Unexpected error saving players: {err}")

    st.markdown("### Preview Updated Data")
    st.dataframe(edited.reset_index(drop=True))
