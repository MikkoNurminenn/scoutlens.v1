# storage.py — Unified storage (Supabase if secrets exist, else JSON files)
from __future__ import annotations
import os, json
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

# Paikallisen JSON-varaston polut
try:
    from app_paths import file_path, DATA_DIR
except Exception:
    # fallback, jos ajetaan irti
    DATA_DIR = Path("./data")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    def file_path(name: str) -> Path:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR / name

PLAYERS_FP = file_path("players.json")

def _safe_read_json(fp: Path, default):
    try:
        if fp.exists():
            txt = fp.read_text(encoding="utf-8")
            return json.loads(txt) if txt.strip() else default
    except Exception:
        pass
    return default

def _safe_write_json(fp: Path, data):
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- Supabase client (optional) ----------
def _make_supabase():
    try:
        from supabase import create_client
    except Exception:
        return None
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None

class Storage:
    """
    Yhtenäinen rajapinta pelaajien tallennukseen:
      - Jos supabase-secrets asetettu → käytä taulua 'players'
      - Muuten fallback JSON: players.json
    Schema (players-taulu Supabasessa) — vähintään nämä sarakkeet:
      id (text, pk), name (text), team_name (text), date_of_birth (text),
      nationality (text), preferred_foot (text), club_number (int4),
      position (text), scout_rating (int4), transfermarkt_url (text),
      photo_path (text), tags (text[] tai text JSON)
    """
    def __init__(self):
        self.sb = _make_supabase()
        self.is_supabase = self.sb is not None

    # --------- READ ---------
    def list_players(self) -> List[Dict[str, Any]]:
        if self.is_supabase:
            try:
                res = self.sb.table("players").select("*").execute()
                data = res.data or []
                # jos tags on JSON-string, normalisoi listaksi
                for p in data:
                    if isinstance(p.get("tags"), str):
                        try: p["tags"] = json.loads(p["tags"])
                        except Exception: pass
                return data
            except Exception:
                pass
        # fallback: JSON
        return _safe_read_json(PLAYERS_FP, [])

    def list_players_by_team(self, team_name: str) -> List[Dict[str, Any]]:
        tnorm = (team_name or "").strip().lower()
        rows = self.list_players()
        return [r for r in rows if (r.get("team_name","") or r.get("Team","")).strip().lower() == tnorm]

    # --------- UPSERT ---------
    def upsert_player(self, player: Dict[str, Any]) -> str:
        pid = str(player.get("id") or player.get("PlayerID") or "")
        if not pid:
            import uuid
            pid = uuid.uuid4().hex
            player["id"] = pid

        # normalisoi tags → listaksi / jsoniksi
        tags = player.get("tags")
        if self.is_supabase:
            # Supabaseen: tags voi olla text[] tai JSON (säilötään JSON:na stringiksi jos ei ole array-tyyppi)
            if isinstance(tags, (list, tuple)):
                pass
            elif tags is None:
                player["tags"] = []
            else:
                # yritä parsea
                try:
                    player["tags"] = json.loads(tags)
                except Exception:
                    player["tags"] = [str(tags)]
            try:
                self.sb.table("players").upsert(player, on_conflict="id").execute()
                return pid
            except Exception:
                # fallback JSON jos supabase kirjoitus epäonnistuu
                pass

        # JSON-varasto
        data = _safe_read_json(PLAYERS_FP, [])
        # päivitä olemassa oleva
        idx = -1
        for i, p in enumerate(data):
            if str(p.get("id")) == pid:
                idx = i; break
        if idx >= 0:
            data[idx] = {**data[idx], **player}
        else:
            data.append(player)
        _safe_write_json(PLAYERS_FP, data)
        return pid

    # --------- PATCHES ---------
    def set_photo_path(self, player_id: str, path_str: str):
        if self.is_supabase:
            try:
                self.sb.table("players").update({"photo_path": path_str}).eq("id", player_id).execute()
                return
            except Exception:
                pass
        # JSON
        data = _safe_read_json(PLAYERS_FP, [])
        for p in data:
            if str(p.get("id")) == str(player_id):
                p["photo_path"] = path_str
                break
        _safe_write_json(PLAYERS_FP, data)

    def set_tags(self, player_id: str, tags: List[str]):
        if self.is_supabase:
            try:
                self.sb.table("players").update({"tags": tags}).eq("id", player_id).execute()
                return
            except Exception:
                pass
        data = _safe_read_json(PLAYERS_FP, [])
        found = False
        for p in data:
            if str(p.get("id")) == str(player_id):
                p["tags"] = tags
                found = True
                break
        if not found:
            data.append({"id": str(player_id), "tags": tags})
        _safe_write_json(PLAYERS_FP, data)

    # --------- DELETE ---------
    def remove_by_ids(self, ids: List[str]) -> int:
        if self.is_supabase:
            try:
                # supabase ei palauta poistettujen lukua ellei select*; haetaan määrä ensin
                res0 = self.sb.table("players").select("id").in_("id", ids).execute()
                n = len(res0.data or [])
                if n:
                    self.sb.table("players").delete().in_("id", ids).execute()
                return n
            except Exception:
                pass
        data = _safe_read_json(PLAYERS_FP, [])
        kept = [p for p in data if str(p.get("id")) not in set(map(str, ids))]
        _safe_write_json(PLAYERS_FP, kept)
        return len(data) - len(kept)
