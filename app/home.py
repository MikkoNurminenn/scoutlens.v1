# app/home.py — minimal Supabase-backed home page (clean, with debug)
from __future__ import annotations

import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError
from app.supabase_client import get_client
from app.time_utils import to_tz
from app.db_tables import PLAYERS, SCOUT_REPORTS, NOTES, MATCHES
try:
    from app.ui import bootstrap_sidebar_auto_collapse
except ImportError:  # pragma: no cover - compatibility shim for legacy packages
    from app.ui.sidebar import bootstrap_sidebar_auto_collapse


# ---------------- Utilities ----------------
def _safe_len(x) -> int:
    try:
        return len(x)
    except Exception:
        return 0


def _get_app_tz() -> ZoneInfo:
    tz_name = (
        st.session_state.get("scoutlens_tz")
        or os.environ.get("SCOUTLENS_TZ")
        or "America/Bogota"
    )
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


APP_TZ = _get_app_tz()


bootstrap_sidebar_auto_collapse()


def _ensure_aware(dt: datetime | None, default_tz: ZoneInfo) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=default_tz)
    return dt


def _parse_kickoff(match: dict, default_tz: ZoneInfo) -> datetime | None:
    # 1) kickoff_at ISO8601, with or without tz
    val = match.get("kickoff_at")
    if isinstance(val, str) and val.strip():
        try:
            dt = datetime.fromisoformat(val.strip().replace("Z", "+00:00"))
            return _ensure_aware(dt, default_tz)
        except Exception:
            pass

    # 2) separate date + time (+ optional tz)
    d, t = match.get("date"), match.get("time")
    if d and t:
        try:
            dt = datetime.fromisoformat(f"{d}T{t}")
            tz_name = match.get("tz")
            if tz_name:
                try:
                    return _ensure_aware(dt, ZoneInfo(tz_name))
                except Exception:
                    return _ensure_aware(dt, default_tz)
            return _ensure_aware(dt, default_tz)
        except Exception:
            pass

    return None


def _postgrest_error_box(e: APIError):
    with st.expander("🔧 Supabase PostgREST -virhe (debug)", expanded=True):
        st.code(
            f"""code:    {getattr(e, 'code', None)}
message: {getattr(e, 'message', str(e))}
details: {getattr(e, 'details', None)}
hint:    {getattr(e, 'hint', None)}""",
            language="text",
        )
        st.caption("Korjaa RLS/taulun nimi/skeema tai avaimet tämän perusteella.")


# ---------------- Data loads ----------------
@st.cache_data(show_spinner=False, ttl=60)
def _load_players() -> List[Dict[str, Any]]:
    client = get_client()
    try:
        res = client.table(PLAYERS).select("*").execute()
        return res.data or []
    except APIError as e:
        _postgrest_error_box(e)
        st.error("Players-haku epäonnistui.")
        return []
    except Exception as e:
        st.error(f"Odottamaton virhe players-haussa: {e}")
        return []


@st.cache_data(show_spinner=False, ttl=60)
def _load_reports() -> List[Dict[str, Any]]:
    client = get_client()
    try:
        res = client.table(SCOUT_REPORTS).select("*").execute()
        return res.data or []
    except APIError as e:
        _postgrest_error_box(e)
        st.error("Reports-haku epäonnistui.")
        return []
    except Exception as e:
        st.error(f"Odottamaton virhe reports-haussa: {e}")
        return []


@st.cache_data(show_spinner=False, ttl=60)
def _load_notes() -> List[Dict[str, Any]]:
    """Noutaa muistiinpanot uusin ensin. Käytetään kenttää 'ts' (ISO-string)."""
    client = get_client()
    try:
        res = client.table(NOTES).select("*").order("ts", desc=True).execute()
        return res.data or []
    except APIError as e:
        _postgrest_error_box(e)
        st.error("Notes-haku epäonnistui.")
        return []
    except Exception as e:
        st.error(f"Odottamaton virhe notes-haussa: {e}")
        return []


def _append_note(text: str):
    """Tallenna muistiinpano tauluun 'notes' kentillä ts (ISO) ja text."""
    txt = (text or "").strip()
    if not txt:
        return
    client = get_client()
    try:
        client.table(NOTES).insert({
            "ts": datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds"),
            "text": txt,
        }).execute()
    except APIError as e:
        _postgrest_error_box(e)
        st.error("Muistiinpanon tallennus epäonnistui (RLS/taulu?).")
    except Exception as e:
        st.error(f"Odottamaton virhe muistiinpanossa: {e}")


@st.cache_data(show_spinner=False, ttl=60)
def _load_matches() -> List[Dict[str, Any]]:
    client = get_client()
    try:
        res = (
            client.table(MATCHES)
            .select("*")
            .order("kickoff_at", desc=True)
            .execute()
        )
        return res.data or []
    except APIError as e:
        _postgrest_error_box(e)
        st.error("Matches-haku epäonnistui.")
        return []
    except Exception as e:
        st.error(f"Odottamaton virhe matches-haussa: {e}")
        return []


@st.cache_data(show_spinner=False, ttl=60)
def _export_zip(players, reports, matches, notes) -> bytes:
    """Vie koko data ZIP:inä (players, reports, matches, notes)."""
    from zipfile import ZipFile, ZIP_DEFLATED
    buf = io.BytesIO()
    with ZipFile(buf, "w", compression=ZIP_DEFLATED) as z:
        z.writestr("players.json", json.dumps(players, ensure_ascii=False, indent=2))
        z.writestr("scout_reports.json", json.dumps(reports, ensure_ascii=False, indent=2))
        z.writestr("matches.json", json.dumps(matches, ensure_ascii=False, indent=2))
        z.writestr("notes.json", json.dumps(notes, ensure_ascii=False, indent=2))
    buf.seek(0)
    return buf.read()


# ---------------- UI ----------------
def show_home():
    st.markdown("### 🏠 Home")
    st.caption("ScoutLens • LATAM scouting toolkit")

    # Data
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_players = executor.submit(_load_players)
        future_reports = executor.submit(_load_reports)
        future_notes = executor.submit(_load_notes)
        future_matches = executor.submit(_load_matches)

    players = future_players.result()
    reports = future_reports.result()
    notes = future_notes.result()
    matches = future_matches.result()

    # KPI:t
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
        "⬇️ Export (ZIP)",
        data=_export_zip(players, reports, matches, notes),
        file_name="scoutlens_backup.zip",
        use_container_width=True,
    )

    # Quick notes
    st.markdown("#### 🗒️ Quick notes")
    left, right = st.columns([2, 1])

    with left:
        text = st.text_area(
            "Write a note",
            placeholder="Observations, ideas, follow-ups…",
            height=100,
        )
        if st.button("Save note", use_container_width=True, type="primary"):
            _append_note(text)
            st.success("Saved.")
            st.cache_data.clear()  # nollaa _load_notes cache
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
                preview = (txt[:140] + "…") if len(txt) > 140 else txt
                st.markdown(f"- **{ts}** — {preview}")

    # Upcoming matches (next 10)
    st.markdown("#### 📅 Upcoming matches")
    matches_with_dt: list[tuple[dict, datetime | None]] = [
        (m, _parse_kickoff(m, APP_TZ)) for m in matches
    ]

    now = datetime.now(APP_TZ)

    upcoming = [
        m
        for (m, dtv) in matches_with_dt
        if (dtv is not None and dtv.astimezone(APP_TZ) >= now)
    ]
    upcoming.sort(
        key=lambda m: (
            _parse_kickoff(m, APP_TZ)
            or datetime.max.replace(tzinfo=APP_TZ)
        )
    )

    if st.checkbox("Debug datetimes", value=False, key="home__dbg_dt"):
        rows = []
        for m, dtv in matches_with_dt:
            rows.append(
                {
                    "match": f"{m.get('home_team','?')} vs {m.get('away_team','?')}",
                    "raw_kickoff": m.get("kickoff_at")
                    or f"{m.get('date')} {m.get('time')}",
                    "parsed": str(dtv),
                    "tzinfo": str(getattr(dtv, 'tzinfo', None)),
                }
            )
        st.dataframe(pd.DataFrame(rows))
        st.write("now:", now, "tz:", now.tzinfo)

    latam_tz = st.session_state.get("latam_tz", "America/Bogota")
    user_tz = st.session_state.get("user_tz", "Europe/Helsinki")

    if not upcoming:
        st.write("—")
    else:
        for m in upcoming[:10]:
            ko = m.get("kickoff_at")
            when = ""
            if ko:
                try:
                    dt_latam = to_tz(ko, latam_tz)
                    dt_user = to_tz(ko, user_tz)
                    when = f"{dt_latam:%Y-%m-%d %H:%M} ({latam_tz}) · {dt_user:%H:%M} ({user_tz})"
                except Exception:
                    pass
            home = m.get("home_team") or m.get("HomeTeam") or ""
            away = m.get("away_team") or m.get("AwayTeam") or ""
            comp = m.get("competition") or ""
            loc = m.get("location") or ""
            line = f"**{when}** — {home} vs {away}"
            extras = " · ".join(x for x in [comp, loc] if x)
            if extras:
                line += f" · {extras}"
            st.markdown(f"- {line}")
