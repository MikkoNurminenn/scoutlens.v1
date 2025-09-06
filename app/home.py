# app/home.py — Home (pilvi-yhteensopiva, siisti ja vakaa)
from __future__ import annotations
import io
import json
from datetime import datetime, date, time as dtime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

# Tallennusadapteri (local JSON ↔ Supabase kv)
from storage import IS_CLOUD, load_json, save_json

# ---------------- "Tiedostonimet" (avaimet kv:ssä) ----------------
PLAYERS_FN    = "players.json"
REPORTS_FN    = "scout_reports.json"
MATCHES_FN    = "matches.json"
NOTES_FN      = "notes.json"

# ---------------- Optional import calendar_ui ----------------
# calendar_ui.py voi halutessaan tarjota omat loaderit/saverit.
def _fallback_load_matches() -> List[Dict[str, Any]]:
    return load_json(MATCHES_FN, default=[])

def _fallback_save_matches(items: List[Dict[str, Any]]) -> None:
    save_json(MATCHES_FN, items)

try:
    # Jos nämä on määritelty, käytetään niitä
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

def _go_to(page: str):
    st.session_state["nav_page"] = page
    st.rerun()

# ---------------- Data helpers (adapterin päällä) ----------------
def _load_players() -> List[Dict[str, Any]]:
    return load_json(PLAYERS_FN, default=[])

def _load_reports() -> List[Dict[str, Any]]:
    return load_json(REPORTS_FN, default=[])

def _load_notes() -> List[Dict[str, Any]]:
    notes = load_json(NOTES_FN, default=[])
    return notes if isinstance(notes, list) else []

def _append_note(text: str):
    notes = _load_notes()
    notes.append({"ts": datetime.now().isoformat(timespec="seconds"), "text": text.strip()})
    save_json(NOTES_FN, notes)

# ---------------- CSS ----------------
HOME_CSS = r"""
:root{
  --fg:#e5e7eb; --fg-dim:#cbd5e1;
  --card:#0f172a; --card-2:#0b1220; --muted:#94a3b8;
  --ac1:#6366f1; --ac2:#0ea5e9; --ok:#10b981; --warn:#f59e0b; --bad:#ef4444;
}
.block {background:var(--card); border:1px solid #1f2937; border-radius:14px; padding:14px;}
.kpi   {background:var(--card-2); border:1px solid #1f2937; border-radius:14px; padding:14px;}
h1,h2,h3, .small {color:var(--fg);}
.small {font-size:0.9rem; color:var(--fg-dim);}
.row {margin-top:8px; margin-bottom:6px;}
.badge {display:inline-block; padding:2px 8px; border-radius:999px; background:#111827; color:var(--muted); border:1px solid #1f2937;}
"""

def _metric(label: str, value: Any, help_text: Optional[str] = None):
    st.markdown(
        f'<div class="kpi"><div class="small">{label}</div>'
        f'<div style="font-size:1.8rem;font-weight:700">{value}</div>'
        f'{f"<div class=small>{help_text}</div>" if help_text else ""}'
        f'</div>',
        unsafe_allow_html=True
    )

# ---------------- Admin / Utilities ----------------
def _cloud_health() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Kirjoita+Lue testi kv:hen. Palauttaa (ok, data)."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        save_json("healthcheck.json", {"ping": now, "mode": "cloud" if IS_CLOUD else "local"})
        data = load_json("healthcheck.json", {})
        return True, data
    except Exception:
        return False, None

def _export_zip() -> bytes:
    """Luo zip, jossa tämän näkymän keskeiset JSONit (kv:stä tai lokaalista)."""
    from zipfile import ZipFile, ZIP_DEFLATED
    buf = io.BytesIO()
    with ZipFile(buf, "w", compression=ZIP_DEFLATED) as z:
        z.writestr(PLAYERS_FN,     json.dumps(_load_players(), ensure_ascii=False, indent=2))
        z.writestr(REPORTS_FN,     json.dumps(_load_reports(), ensure_ascii=False, indent=2))
        z.writestr(MATCHES_FN,     json.dumps(_load_matches(), ensure_ascii=False, indent=2))
        z.writestr(NOTES_FN,       json.dumps(_load_notes(),   ensure_ascii=False, indent=2))
    buf.seek(0)
    return buf.read()

# ---------------- Main ----------------
def show_home():
    st.markdown(f"<style>{HOME_CSS}</style>", unsafe_allow_html=True)

    # ---- Header
    st.markdown("### 🏠 Home")
    st.caption("ScoutLens • LATAM scouting toolkit")

    # ---- Cloud health (näkyy pienessä expanderissa, auttaa debugissa)
    with st.expander("Cloud health", expanded=False):
        ok, data = _cloud_health()
        if ok:
            st.success("Write+read OK")
            st.json(data)
        else:
            st.warning("Healthcheck ei onnistunut. Tarkista secrets/verkko.")

        st.download_button(
            "⬇️ Export (ZIP)", data=_export_zip(), file_name="scoutlens_backup.zip",
            use_container_width=True
        )

    # ---- Data loads
    players = _load_players()
    reports = _load_reports()
    notes   = _load_notes()
    matches = _load_matches()   # tärkeä: lataa aina funktiokutsulla

    # ---- KPI-rivi
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        _metric("Pelaajia", _safe_len(players))
    with k2:
        _metric("Raportteja", _safe_len(reports))
    with k3:
        today0 = datetime.combine(date.today(), dtime.min)
        upcoming_cnt = sum(1 for m in matches if (lambda dt=_match_dt(m): dt and dt >= today0)())
        _metric("Tulevat ottelut", upcoming_cnt)
    with k4:
        _metric("Muistiinpanoja", _safe_len(notes))

    st.divider()

    # ---- Quick Actions (ei syviä nested columns -virheitä)
    st.markdown("#### ⚡ Pika-toiminnot")
    qa1, qa2, qa3, qa4, qa5 = st.columns(5)
    if qa1.button("👥 Team View", use_container_width=True):
        _go_to("Team View")
    if qa2.button("🧑‍💻 Player Editor", use_container_width=True):
        _go_to("Player Editor")
    if qa3.button("📝 Match Reporter", use_container_width=True):
        _go_to("Match Reporter")
    if qa4.button("🗓️ Kalenteri", use_container_width=True):
        _go_to("Calendar")
    if qa5.button("🗒️ Muistiinpanot", use_container_width=True):
        _go_to("Notes")

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
        # Listakortit, ei sisäkkäisiä columns→columns -rakenteita
        for row in rows:
            c1, c2, c3, c4 = st.columns([1.2, 2.5, 1.6, 0.9])
            with c1:
                st.markdown(
                    f'**{row["_dt"].strftime("%a %d.%m.%Y")}**\n\n'
                    f'<span class="badge">{row.get("time","") or row["_dt"].strftime("%H:%M")}</span>',
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
                ts  = n.get("ts", "")
                st.markdown(f"- **{ts}** — {txt[:140]}{'…' if len(txt) > 140 else ''}")
