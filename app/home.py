# app/home.py — minimal Supabase-backed home page (clean, with debug)
from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st
from postgrest.exceptions import APIError
from supabase_client import get_client


# ---------------- Utilities ----------------
def _safe_len(x) -> int:
    try:
        return len(x)
    except Exception:
        return 0


def _match_dt(m: Dict[str, Any]) -> Optional[datetime]:
    """Yhdistä matchin date + time tekstikentistä datetimeksi."""
    d = (m.get("date") or "").strip()
    t = (m.get("time") or "").strip()
    if d and t:
        try:
            return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
        except Exception:
            return None
    if d:
        try:
            # jos aika puuttuu → käytä klo 12:00, jotta sorttaus toimii
            return datetime.strptime(d, "%Y-%m-%d").replace(hour=12, minute=0)
        except Exception:
            return None
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
@st.cache_data(show_spinner=False, ttl=10)
def _load_players() -> List[Dict[str, Any]]:
    client = get_client()
    try:
        res = client.table("players").select("*").execute()
        return res.data or []
    except APIError as e:
        _postgrest_error_box(e)
        st.error("Players-haku epäonnistui.")
        return []
    except Exception as e:
        st.error(f"Odottamaton virhe players-haussa: {e}")
        return []


@st.cache_data(show_spinner=False, ttl=10)
def _load_reports() -> List[Dict[str, Any]]:
    client = get_client()
    try:
        res = client.table("scout_reports").select("*").execute()
        return res.data or []
    except APIError as e:
        _postgrest_error_box(e)
        st.error("Reports-haku epäonnistui.")
        return []
    except Exception as e:
        st.error(f"Odottamaton virhe reports-haussa: {e}")
        return []


@st.cache_data(show_spinner=False, ttl=10)
def _load_notes() -> List[Dict[str, Any]]:
    """Noutaa muistiinpanot uusin ensin. Käytetään kenttää 'ts' (ISO-string)."""
    client = get_client()
    try:
        res = client.table("notes").select("*").order("ts", desc=True).execute()
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
        client.table("notes").insert({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "text": txt,
        }).execute()
    except APIError as e:
        _postgrest_error_box(e)
        st.error("Muistiinpanon tallennus epäonnistui (RLS/taulu?).")
    except Exception as e:
        st.error(f"Odottamaton virhe muistiinpanossa: {e}")


@st.cache_data(show_spinner=False, ttl=10)
def _load_matches() -> List[Dict[str, Any]]:
    client = get_client()
    try:
        res = client.table("matches").select("*").execute()
        return res.data or []
    except APIError as e:
        _postgrest_error_box(e)
        st.error("Matches-haku epäonnistui.")
        return []
    except Exception as e:
        st.error(f"Odottamaton virhe matches-haussa: {e}")
        return []


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
    players = _load_players()
    reports = _load_reports()
    notes = _load_notes()
    matches = _load_matches()

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
        if st.button("Save note", use_container_width=True):
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
    now = datetime.now()
    matches_with_dt = [(m, _match_dt(m)) for m in matches]
    upcoming = [m for m, dtv in matches_with_dt if dtv and dtv >= now]
    upcoming.sort(key=lambda m: _match_dt(m))

    if not upcoming:
        st.write("—")
    else:
        for m in upcoming[:10]:
            dt = _match_dt(m)
            when = dt.strftime("%Y-%m-%d %H:%M") if dt else (m.get("date") or "")
            home = m.get("home_team") or m.get("HomeTeam") or ""
            away = m.get("away_team") or m.get("AwayTeam") or ""
            comp = m.get("competition") or ""
            loc = m.get("location") or ""
            line = f"**{when}** — {home} vs {away}"
            extras = " · ".join(x for x in [comp, loc] if x)
            if extras:
                line += f" · {extras}"
            st.markdown(f"- {line}")
