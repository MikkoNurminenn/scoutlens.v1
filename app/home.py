# app/home.py — Home (lokaali + pilvi-valmis adapteroitavaksi, siisti ja vakaa)
from __future__ import annotations
import io
import json
from datetime import datetime, date, time as dtime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import platform

import streamlit as st
from app_paths import file_path  # meidän polkuapuri (kirjoittaa %APPDATA%/ScoutLens tms.)
from sync_utils import push_json, pull_json

# ---------------- Pienet, paikalliset JSON-apurit (ei storage-riippuvuutta) ----------------
def load_json_fp(fp: Path, default):
    try:
        if fp.exists():
            return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def save_json_fp(fp: Path, data):
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# Nämä wrapperit mahdollistavat myöhemmin helpon vaihdon KV/Supabaseen (vaihda vain toteutusta)
def load_json(name_or_fp: str | Path, default):
    fp = file_path(name_or_fp) if isinstance(name_or_fp, str) else name_or_fp
    return load_json_fp(fp, default)

def save_json(name_or_fp: str | Path, data):
    fp = file_path(name_or_fp) if isinstance(name_or_fp, str) else name_or_fp
    save_json_fp(fp, data)

IS_CLOUD = (platform.system() not in ("Windows", "Darwin"))

# ---------------- "Tiedostonimet" ----------------
PLAYERS_FN    = "players.json"
REPORTS_FN    = "scout_reports.json"
MATCHES_FN    = "matches.json"
NOTES_FN      = "notes.json"
FILES = [
    "players.json",
    "matches.json",
    "shortlists.json",
    "scout_reports.json",
    "notes.json",
]

# ---------------- Optional import calendar_ui ----------------
def _fallback_load_matches() -> List[Dict[str, Any]]:
    return load_json(MATCHES_FN, default=[])

def _fallback_save_matches(items: List[Dict[str, Any]]) -> None:
    save_json(MATCHES_FN, items)

try:
    from calendar_ui import _load_matches as _load_matches  # type: ignore
except Exception:
    _load_matches = _fallback_load_matches  # type: ignore

try:
    from calendar_ui import _save_matches as _save_matches  # type: ignore
except Exception:
    _save_matches = _fallback_save_matches  # type: ignore

# ---------------- Utils ----------------
def _safe_len(x) -> int:
    try:
        return len(x)
    except Exception:
        return 0

def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None

def _parse_time(s: Optional[str]) -> Optional[dtime]:
    if not s:
        return None
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except Exception:
            continue
    return None

def _match_dt(m: Dict[str, Any]) -> Optional[datetime]:
    """Yhdistää date+time → datetime (naive, paikallinen)."""
    d = _parse_date(m.get("date"))
    t = _parse_time(m.get("time"))
    if d and t:
        try:
            return datetime.combine(d, t)
        except Exception:
            return None
    if d:
        return datetime.combine(d, dtime(0, 0))
    return None


# ---------------- Data helpers ----------------
def _load_players() -> List[Dict[str, Any]]:
    return load_json(PLAYERS_FN, default=[])

def _load_reports() -> List[Dict[str, Any]]:
    return load_json(REPORTS_FN, default=[])

def _load_notes() -> List[Dict[str, Any]]:
    notes = load_json(NOTES_FN, default=[])
    return notes if isinstance(notes, list) else []

def _append_note(text: str):
    notes = _load_notes()
    notes.append({"created_at": datetime.now().isoformat(timespec="seconds"), "text": text.strip()})
    save_json(NOTES_FN, notes)

def _metric(label: str, value: Any, help_text: Optional[str] = None):
    st.markdown(
        f"<div class='sl-kpi'><div class='label'>{label}</div>"
        f"<div class='value'>{value}</div>"
        f"{f'<div class=\"label\">{help_text}</div>' if help_text else ''}</div>",
        unsafe_allow_html=True,
    )

# ---------------- Admin / Utilities ----------------
def _cloud_health() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Kirjoita+Lue testi (lokaalisti tiedostoon). Palauttaa (ok, data)."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        save_json("healthcheck.json", {"ping": now, "mode": "cloud" if IS_CLOUD else "local"})
        data = load_json("healthcheck.json", {})
        return True, data
    except Exception:
        return False, None

def _export_zip() -> bytes:
    """Luo zip, jossa tämän näkymän keskeiset JSONit."""
    from zipfile import ZipFile, ZIP_DEFLATED
    buf = io.BytesIO()
    with ZipFile(buf, "w", compression=ZIP_DEFLATED) as z:
        z.writestr(PLAYERS_FN, json.dumps(_load_players(), ensure_ascii=False, indent=2))
        z.writestr(REPORTS_FN, json.dumps(_load_reports(), ensure_ascii=False, indent=2))
        z.writestr(MATCHES_FN, json.dumps(_load_matches(), ensure_ascii=False, indent=2))
        z.writestr(NOTES_FN,   json.dumps(_load_notes(),   ensure_ascii=False, indent=2))
    buf.seek(0)
    return buf.read()

# ---------------- Main ----------------
def show_home():
    if st.sidebar.checkbox("Style self-check", False):
        st.markdown(
            "<div class='sl-kpi'><div class='label'>Demo KPI</div><div class='value'>42</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<a class='sl-btn'>Primary</a>", unsafe_allow_html=True)
        st.markdown("<span class='sl-chip'>Chip</span>", unsafe_allow_html=True)
        st.markdown(
            "<div class='sl-table'><table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td><span class='sl-badge-link'>7.5</span></td></tr></tbody></table></div>",
            unsafe_allow_html=True,
        )
        return

    # ---- Header
    st.markdown("### 🏠 Home")
    st.caption("ScoutLens • LATAM scouting toolkit")

    # ---- Cloud health (expanderina, hyödyllinen debugiin)
    with st.expander("Cloud health", expanded=False):
        ok, data = _cloud_health()
        if ok:
            st.success("Write+read OK")
            st.json(data)
        else:
            st.warning("Healthcheck ei onnistunut. Tarkista polut/oikeudet.")

        st.download_button(
            "⬇️ Export (ZIP)", data=_export_zip(), file_name="scoutlens_backup.zip",
            use_container_width=True
        )

    # ---- Cloud Sync (Supabase)
    st.subheader("Cloud Sync (Supabase)")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Backup → Supabase"):
            for name in FILES:
                table = Path(name).stem
                ok, msg = push_json(table, file_path(name))
                if ok:
                    st.write("✅ " + msg)
                else:
                    st.error("❌ " + msg)

    with col2:
        if st.button("Restore ← Supabase"):
            for name in FILES:
                table = Path(name).stem
                ok, msg = pull_json(table, file_path(name))
                if ok:
                    st.write("✅ " + msg)
                else:
                    st.error("❌ " + msg)
            st.cache_data.clear()
            st.success("Restored and cache cleared.")

    # ---- Data loads
    players = _load_players()
    reports = _load_reports()
    notes   = _load_notes()
    matches = _load_matches()   # tärkeä: lataa aina funktiokutsulla

    # ---- KPI-rivi
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
        _metric("Pelaajia", _safe_len(players))
    with k2:
        _metric("Joukkueita", teams_cnt)
    with k3:
        _metric("Raportteja", _safe_len(reports))

    st.divider()

    # ---- Quick Actions (ei nested columns -ongelmia)
    st.markdown("#### ⚡ Pika-toiminnot")
    st.markdown(
        """
        <div class='sl-quick-actions'>
            <a href='?p=Team%20View' class='sl-btn'>👥 Team View</a>
            <a href='?p=Player%20Editor' class='sl-btn'>🧑‍💻 Player Editor</a>
            <a href='?p=Match%20Reporter' class='sl-btn'>📝 Match Reporter</a>
            <a href='?p=Calendar' class='sl-btn'>🗓️ Kalenteri</a>
            <a href='?p=Notes' class='sl-btn'>🗒️ Muistiinpanot</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ---- Tulevat ottelut
    st.markdown("#### 🗓️ Tulevat ottelut")
    left, right = st.columns([3, 1])
    with left:
        st.caption("Näytetään aikajaksolla tulevat. Lähde: calendar_ui / matches.json")
    with right:
        days = st.slider("Aikajänne (päivää)", 7, 60, 30, help="Kuinka pitkälle eteenpäin listataan.")

    now = datetime.combine(date.today(), dtime.min)
    horizon = now + timedelta(days=days, seconds=-1)
    rows: List[Dict[str, Any]] = []
    for i, m in enumerate(matches):
        dtv = _match_dt(m)
        if dtv and now <= dtv <= horizon:
            rows.append({"_i": i, "_dt": dtv, **m})
    rows.sort(key=lambda r: r["_dt"])

    if not rows:
        st.info("Ei tulevia otteluita valitulla aikajänteellä.")
    else:
        for row in rows:
            c1, c2, c3, c4 = st.columns([1.2, 2.5, 1.6, 0.9])
            with c1:
                st.markdown(
                    f'**{row["_dt"].strftime("%a %d.%m.%Y")}**\n\n'
                    f'<span class="sl-chip">{row.get("time","") or row["_dt"].strftime("%H:%M")}</span>',
                    unsafe_allow_html=True
                )
            with c2:
                home = row.get("home_team", "—")
                away = row.get("away_team", "—")
                comp = row.get("competition") or row.get("league") or ""
                st.write(f"{home}  —  {away}")
                if comp:
                    st.caption(comp)
            with c3:
                loc = row.get("location") or row.get("venue") or ""
                city = row.get("city") or ""
                z = row.get("tz") or row.get("timezone") or ""
                txt = ", ".join(x for x in [loc, city] if x)
                st.write(txt if txt else "—")
                if z:
                    st.caption(f"TZ: {z}")
            with c4:
                if st.button("Poista", key=f"del_match_{row['_i']}", use_container_width=True):
                    all_matches = _load_matches()
                    if 0 <= row["_i"] < len(all_matches):
                        all_matches.pop(row["_i"])
                        _save_matches(all_matches)
                    st.rerun()

    st.divider()

    # ---- Pikamuistio (notes.json)
    st.markdown("#### 🗒️ Pikamuistio")
    ncol1, ncol2 = st.columns([2, 1])
    with ncol1:
        text = st.text_area(
            "Kirjoita muistiinpano",
            placeholder="Nopeat havainnot, scouting-ideat, muistilista…",
            height=100
        )
        btn_col, _ = st.columns([1, 3])
        if btn_col.button("Tallenna muistiinpano", use_container_width=True):
            if text and text.strip():
                _append_note(text)
                st.success("Tallennettu.")
                st.rerun()
    with ncol2:
        st.caption("Viimeisimmät muistiinpanot")
        recent = list(reversed(notes))[:8]
        if not recent:
            st.write("—")
        else:
            for n in recent:
                txt = n.get("text", "")
                ts  = n.get("created_at", "")
                st.markdown(f"- **{ts}** — {txt[:140]}{'…' if len(txt) > 140 else ''}")
