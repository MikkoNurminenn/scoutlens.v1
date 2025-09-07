# app/calendar_ui.py
from __future__ import annotations

import json
import uuid
import calendar as pycal
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from zoneinfo import ZoneInfo

from app.app_paths import file_path, DATA_DIR

MATCHES_FP = file_path("matches.json")

# -------------- State keys --------------
PFX = "cal__"
K_MONTH = PFX + "month"
K_YEAR = PFX + "year"
K_TZ = PFX + "tz"
K_MODE = PFX + "mode"        # "add" | "edit" | None
K_EDIT = PFX + "edit_id"
K_BUSTER = PFX + "cache_buster"

# -------------- Timezones --------------
LATAM_TZS = [
    "America/Bogota","America/Lima","America/Caracas","America/La_Paz",
    "America/Guayaquil","America/Santiago","America/Buenos_Aires",
    "America/Montevideo","America/Asuncion","America/Sao_Paulo",
    "America/Manaus","America/Mexico_City",
]
LOCAL_TZ = "Europe/Helsinki"

# -------------- IO --------------
@st.cache_data(show_spinner=False)
def _load_json(_: int = 0):
    try:
        if MATCHES_FP.exists():
            return json.loads(MATCHES_FP.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def _save_json(data: Any) -> None:
    try:
        MATCHES_FP.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _bust():
    st.cache_data.clear()
    st.session_state[K_BUSTER] = st.session_state.get(K_BUSTER, 0) + 1

# -------------- Model --------------
@dataclass
class Match:
    id: str
    date: str
    time: str
    tz: str
    home: str
    away: str
    competition: str = ""
    location: str = ""
    city: str = ""
    targets: List[str] = field(default_factory=list)
    notes: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date,
            "time": self.time,
            "tz": self.tz,
            "home": self.home,
            "away": self.away,
            "competition": self.competition,
            "location": self.location,
            "city": self.city,
            "targets": self.targets,
            "notes": self.notes,
        }

# -------------- DT utils --------------
def _parse_dt(date_str: Optional[str], time_str: Optional[str], tz_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    d = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            d = datetime.strptime(str(date_str).strip(), fmt)
            break
        except Exception:
            continue
    if d is None:
        return None
    if time_str:
        for tf in ("%H:%M", "%H.%M"):
            try:
                t = datetime.strptime(str(time_str).strip(), tf)
                d = d.replace(hour=t.hour, minute=t.minute)
                break
            except Exception:
                continue
    if tz_str:
        try:
            d = d.replace(tzinfo=ZoneInfo(str(tz_str).strip()))
        except Exception:
            pass
    return d

def _disp(dt: Optional[datetime], tz: str) -> str:
    if not isinstance(dt, datetime):
        return "—"
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(tz))
        else:
            dt = dt.astimezone(ZoneInfo(tz))
    except Exception:
        pass
    return dt.strftime("%Y-%m-%d %H:%M")

# -------------- Data helpers --------------
def _load_matches() -> List[Dict[str, Any]]:
    data = _load_json(st.session_state.get(K_BUSTER, 0))
    if isinstance(data, dict) and "matches" in data:
        data = data["matches"]
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for r in data:
        m = dict(r)
        m.setdefault("id", str(uuid.uuid4()))
        m.setdefault("targets", [])
        out.append(m)
    try:
        out.sort(key=lambda m: (_parse_dt(m.get("date"), m.get("time"), m.get("tz")) or datetime.max))
    except Exception:
        pass
    return out

def _upsert(m: Dict[str, Any]) -> None:
    data = _load_matches()
    idx = next((i for i, x in enumerate(data) if str(x.get("id")) == str(m["id"])), None)
    if idx is None:
        data.append(m)
    else:
        data[idx] = m
    _save_json(data)
    _bust()

def _delete(mid: str) -> None:
    data = [x for x in _load_matches() if str(x.get("id")) != str(mid)]
    _save_json(data)
    _bust()

# -------------- Forms --------------
def _form(default: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    is_edit = default is not None
    col1, col2 = st.columns(2)
    with col1:
        dval = date.today()
        if is_edit and default.get("date"):
            try:
                dval = datetime.strptime(default["date"], "%Y-%m-%d").date()
            except Exception:
                pass
        date_val = st.date_input("Date", value=dval)
        time_val = st.text_input("Time (HH:MM)", value=(default.get("time", "") if is_edit else ""))
        tz_opts = [LOCAL_TZ] + LATAM_TZS
        tz_default = default.get("tz") if (is_edit and default.get("tz") in tz_opts) else LOCAL_TZ
        tz_val = st.selectbox("Time zone (IANA)", tz_opts, index=tz_opts.index(tz_default))
    with col2:
        competition = st.text_input("Competition", value=(default.get("competition", "") if is_edit else ""))
        city = st.text_input("City", value=(default.get("city", "") if is_edit else ""))
        location = st.text_input("Stadium / Location", value=(default.get("location", "") if is_edit else ""))

    home = st.text_input("Home team", value=(default.get("home", "") if is_edit else ""))
    away = st.text_input("Away team", value=(default.get("away", "") if is_edit else ""))
    targets_str = st.text_input("Scout targets (comma-separated)", value=(",".join(default.get("targets", [])) if is_edit else ""))
    notes = st.text_area("Notes", value=(default.get("notes", "") if is_edit else ""))

    c1, c2 = st.columns(2)
    with c1:
        save = st.button("Save", use_container_width=True)
    with c2:
        cancel = st.button("Cancel", use_container_width=True)

    if cancel:
        st.session_state[K_MODE] = None
        st.session_state[K_EDIT] = None
        st.rerun()

    if save:
        m = Match(
            id=(default.get("id") if is_edit else str(uuid.uuid4())),
            date=date_val.strftime("%Y-%m-%d"),
            time=time_val.strip(),
            tz=tz_val.strip(),
            home=home.strip(),
            away=away.strip(),
            competition=competition.strip(),
            location=location.strip(),
            city=city.strip(),
            targets=[t.strip() for t in targets_str.split(",") if t.strip()],
            notes=notes.strip(),
        ).as_dict()
        return m
    return None

# -------------- Month selector --------------
def _pick_month(matches: List[Dict[str, Any]]):
    today = date.today()
    years = sorted({today.year} | {datetime.strptime(m["date"], "%Y-%m-%d").year for m in matches if m.get("date")})
    months = list(range(1, 12 + 1))
    sel_year = st.session_state.get(K_YEAR, today.year)
    sel_month = st.session_state.get(K_MONTH, today.month)
    tz_opts = [LOCAL_TZ] + LATAM_TZS
    sel_tz = st.session_state.get(K_TZ, LOCAL_TZ)

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        sel_year = st.selectbox("Year", years, index=years.index(sel_year) if sel_year in years else years.index(today.year))
    with c2:
        sel_month = st.selectbox("Month", months, index=(sel_month - 1 if 1 <= sel_month <= 12 else today.month - 1), format_func=lambda m: f"{m:02d}")
    with c3:
        sel_tz = st.selectbox("Display time in", tz_opts, index=tz_opts.index(sel_tz) if sel_tz in tz_opts else 0)

    st.session_state[K_YEAR] = sel_year
    st.session_state[K_MONTH] = sel_month
    st.session_state[K_TZ] = sel_tz
    return sel_year, sel_month, sel_tz

# -------------- Calendar grid --------------
def _grid(matches: List[Dict[str, Any]], year: int, month: int, tz: str):
    st.subheader(f"📅 {year}-{month:02d}")
    cal = pycal.Calendar(firstweekday=0)  # Monday
    weeks = cal.monthdayscalendar(year, month)

    by_day: Dict[int, List[Dict[str, Any]]] = {}
    for m in matches:
        try:
            d = datetime.strptime(m["date"], "%Y-%m-%d").date()
            if d.year == year and d.month == month:
                by_day.setdefault(d.day, []).append(m)
        except Exception:
            continue

    header = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    st.write("| " + " | ".join(header) + " |")
    st.write("|" + " --- |" * 7)

    for week in weeks:
        cells = []
        for day in week:
            if day == 0:
                cells.append(" ")
                continue
            items = by_day.get(day, [])
            if not items:
                cells.append(f"**{day}**  \n")
            else:
                lines = [f"**{day}**"]
                for m in items[:3]:
                    dt_src = _parse_dt(m.get("date"), m.get("time"), m.get("tz"))
                    dt_disp = _disp(dt_src, tz)
                    lines.append(f"- {m.get('home','—')} vs {m.get('away','—')}  \n  <small>{dt_disp}</small>")
                if len(items) > 3:
                    lines.append(f"- … +{len(items)-3} more")
                cells.append("  \n".join(lines))
        st.write("| " + " | ".join(cells) + " |")

# -------------- Small card --------------
def _card(m: Dict[str, Any], tz: str):
    dt_src = _parse_dt(m.get("date"), m.get("time"), m.get("tz"))
    dt_disp = _disp(dt_src, tz)
    cap_bits = []
    if m.get("competition"):
        cap_bits.append(m["competition"])
    loc_bits = [m.get("location", ""), m.get("city", "")]
    loc_bits = [x for x in loc_bits if x]
    if loc_bits:
        cap_bits.append(", ".join(loc_bits))
    if m.get("tz"):
        cap_bits.append(f"{m['tz']} → {tz}")

    st.markdown(f"**{m.get('home','—')} vs {m.get('away','—')}**")
    st.caption(f"{m.get('date','—')} {m.get('time','')}  •  {', '.join(cap_bits)}")
    st.caption(f"🕒 Display: {dt_disp}")

    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        if st.button(f"Edit {m['id']}", key=f"edit_{m['id']}", use_container_width=True):
            st.session_state[K_MODE] = "edit"
            st.session_state[K_EDIT] = m["id"]
            st.rerun()
    with c2:
        if st.button(f"Delete {m['id']}", key=f"del_{m['id']}", use_container_width=True):
            _delete(m["id"])
            st.success("Deleted.")
            st.rerun()

# -------------- Public entry --------------
def show_calendar():
    st.header("📅 Matches — Calendar")

    t1, t2, t3 = st.columns([0.3, 0.3, 0.4])
    with t1:
        if st.button("↻ Reload", help="Clear cache and reload", use_container_width=True):
            _bust()
            st.rerun()
    with t2:
        if st.button("➕ Add match", use_container_width=True):
            st.session_state[K_MODE] = "add"
            st.session_state[K_EDIT] = None
    with t3:
        data = _load_matches()
        if data:
            df = pd.DataFrame(data)
            st.download_button(
                label="⬇️ CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="matches.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.download_button(
                label="⬇️ JSON",
                data=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="matches.json",
                mime="application/json",
                use_container_width=True,
            )

    # Add/Edit form
    if st.session_state.get(K_MODE) in ("add", "edit"):
        st.divider()
        st.subheader("Match Editor")
        default = None
        if st.session_state[K_MODE] == "edit" and st.session_state.get(K_EDIT):
            default = next((m for m in _load_matches() if str(m.get("id")) == str(st.session_state[K_EDIT])), None)
        saved = _form(default)
        if saved:
            _upsert(saved)
            st.success("Saved.")
            st.session_state[K_MODE] = None
            st.session_state[K_EDIT] = None
            st.rerun()

    st.divider()
    matches = _load_matches()
    year, month, tz = _pick_month(matches)
    _grid(matches, year, month, tz)

    # Upcoming
    st.subheader("Upcoming (next 10)")
    now_local = datetime.now(ZoneInfo(tz)) if tz else datetime.now()
    upcoming: List[tuple[datetime, Dict[str, Any]]] = []
    for m in matches:
        dt = _parse_dt(m.get("date"), m.get("time"), m.get("tz"))
        if not isinstance(dt, datetime):
            continue
        try:
            dt_local = dt if dt.tzinfo is None else dt.astimezone(ZoneInfo(tz))
        except Exception:
            dt_local = dt
        if dt_local >= now_local:
            upcoming.append((dt_local, m))
    upcoming.sort(key=lambda x: x[0])
    for _, m in upcoming[:10]:
        with st.container(border=True):
            _card(m, tz)
