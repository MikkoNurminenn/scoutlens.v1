# app/home.py — minimal Supabase-backed home page
from __future__ import annotations

import io
import json
from datetime import datetime, date, time as dtime, timedelta
from typing import Any, Dict, List, Optional

import streamlit as st

from supabase_client import get_client


def _safe_len(x) -> int:
    try:
        return len(x)
    except Exception:
        return 0


def _match_dt(m: Dict[str, Any]) -> Optional[datetime]:
    d = m.get("date")
    t = m.get("time")
    if d and t:
        try:
            return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
        except Exception:
            return None
    return None


def _load_players() -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
    return client.table("players").select("*").execute().data or []


def _load_reports() -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
    return client.table("scout_reports").select("*").execute().data or []


def _load_notes() -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
    res = client.table("notes").select("*").order("ts", desc=True).execute()
    return res.data or []


def _load_matches() -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
    res = client.table("matches").select("*").execute()
    return res.data or []


def _append_note(text: str):
    client = get_client()
    if client:
        client.table("notes").insert({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "text": text.strip(),
        }).execute()


def _export_zip() -> bytes:
    from zipfile import ZipFile, ZIP_DEFLATED
    client = get_client()
    players = _load_players()
    reports = _load_reports()
    matches = _load_matches()
    notes = _load_notes()
    buf = io.BytesIO()
    with ZipFile(buf, "w", compression=ZIP_DEFLATED) as z:
        z.writestr("players.json", json.dumps(players, ensure_ascii=False, indent=2))
        z.writestr("scout_reports.json", json.dumps(reports, ensure_ascii=False, indent=2))
        z.writestr("matches.json", json.dumps(matches, ensure_ascii=False, indent=2))
        z.writestr("notes.json", json.dumps(notes, ensure_ascii=False, indent=2))
    buf.seek(0)
    return buf.read()


def show_home():
    st.markdown("### 🏠 Home")
    st.caption("ScoutLens • LATAM scouting toolkit")

    players = _load_players()
    reports = _load_reports()
    notes = _load_notes()
    matches = _load_matches()

    teams = {
        str(
            p.get("team_name")
            or p.get("Team")
            or p.get("team")
            or p.get("current_club")
            or p.get("CurrentClub")
            or ""
        ).strip()
        for p in players
    }
    teams_cnt = len([t for t in teams if t])

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Players", _safe_len(players))
    with k2:
        st.metric("Teams", teams_cnt)
    with k3:
        st.metric("Reports", _safe_len(reports))

    st.download_button(
        "⬇️ Export (ZIP)", data=_export_zip(), file_name="scoutlens_backup.zip",
        use_container_width=True
    )

    st.markdown("#### 🗒️ Quick notes")
    left, right = st.columns([2, 1])
    with left:
        text = st.text_area(
            "Write a note",
            placeholder="Observations, ideas, follow-ups…",
            height=100,
        )
        if st.button("Save note"):
            if text and text.strip():
                _append_note(text)
                st.success("Saved.")
                st.rerun()
    with right:
        st.caption("Latest notes")
        recent = notes[:8]
        if not recent:
            st.write("—")
        else:
            for n in recent:
                txt = n.get("text", "")
                ts = n.get("ts", "")
                st.markdown(f"- **{ts}** — {txt[:140]}{'…' if len(txt) > 140 else ''}")


