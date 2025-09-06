import json
from datetime import date, datetime
from pathlib import Path
import re

import pandas as pd
import streamlit as st

def _inject_css_once(key: str, css_html: str):
    sskey = f"__css_injected__{key}"
    if not st.session_state.get(sskey):
        st.markdown(css_html, unsafe_allow_html=True)
        st.session_state[sskey] = True

import plotly.express as px

from app_paths import file_path, DATA_DIR
from storage import load_json

# ---- tiedostopolut
PLAYERS_FP = file_path("players.json")
REPORTS_FP = file_path("scout_reports.json")
MATCHES_FP = file_path("matches.json")
TEAMS_FP   = file_path("teams.json")  # fallbackia varten

# ---- tiimit: käytä teams_storea, muuten fallback
try:
    from teams_store import list_teams_all  # ensisijainen
except Exception:
    def _norm_team_for_list(p: dict) -> str:
        # EI lueta current_club -kenttiä
        return (p.get("team_name") or p.get("Team") or p.get("team") or "").strip()

    def list_teams_all() -> list[str]:
        teams = set(load_json(TEAMS_FP, []))
        for p in load_json(PLAYERS_FP, []):
            t = _norm_team_for_list(p)
            if t:
                teams.add(t)
        return sorted(teams)

# ---- utilit
def _norm_team(p: dict) -> str:
    return (p.get("team_name") or p.get("Team") or p.get("team") or "").strip()

def _players_by_team(team: str) -> list[dict]:
    players = load_json(PLAYERS_FP, [])
    t = (team or "").strip()
    return [p for p in players if _norm_team(p) == t]

def _ensure_df(rows: list[dict]) -> pd.DataFrame:
    """
    Normalisoi yleisimmät aliakset yhdenmukaisiksi sarakkeiksi:
    - Name, Team, DateOfBirth, Nationality, club_number
    - Siivoaa NaN/tyhjät merkkijonot
    - Nationality: list/tuple -> ", ".join(...)
    """
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)

    # Nimi -> Name
    if "name" in df.columns and "Name" not in df.columns:
        df.rename(columns={"name": "Name"}, inplace=True)

    # Tiimi -> Team (jos puuttuu, johdetaan rekordista)
    if "Team" not in df.columns:
        df["Team"] = df.apply(_norm_team, axis=1)

    # Syntymäaika alias -> DateOfBirth
    if "DateOfBirth" not in df.columns:
        for k in ["date_of_birth", "dob", "birthdate", "birth_date", "DOB"]:
            if k in df.columns:
                df.rename(columns={k: "DateOfBirth"}, inplace=True)
                break

    # Kansallisuus alias -> Nationality
    if "Nationality" not in df.columns:
        for k in ["nationality", "country", "Nation", "nation", "Country", "Citizenship", "citizenship"]:
            if k in df.columns:
                df.rename(columns={k: "Nationality"}, inplace=True)
                break

    # Pelinumero alias -> club_number
    if "club_number" not in df.columns:
        for k in ["number", "shirt_number", "ShirtNumber", "ClubNumber", "squadNumber", "squad_number"]:
            if k in df.columns:
                df.rename(columns={k: "club_number"}, inplace=True)
                break

    # Siistintä
    if "Nationality" in df.columns:
        def _norm_nat(v):
            if v is None:
                return ""
            if isinstance(v, (list, tuple, set)):
                # listat/tuplat -> "A, B"
                return ", ".join(str(x) for x in v if str(x).strip())
            return str(v)
        df["Nationality"] = df["Nationality"].apply(_norm_nat).fillna("").astype(str).str.strip()

    # club_number -> pidä numerot tai tyhjä
    if "club_number" in df.columns:
        def _norm_num(v):
            if v in (None, "", "nan", "NaN"):
                return ""
            try:
                n = int(float(v))
                return n if n > 0 else ""
            except Exception:
                return ""
        df["club_number"] = df["club_number"].apply(_norm_num)

    return df

def _age_from_dob(dob_str: str | None) -> int | None:
    if not dob_str:
        return None
    try:
        d = datetime.fromisoformat(str(dob_str)).date()
        today = date.today()
        return today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    except Exception:
        return None

def _slugify(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^A-Za-z0-9_\-]", "", s)
    return s or "player"

def _find_photo_for(player_row: dict) -> Path | None:
    """
    1) players.json -> photo_path
    2) DATA_DIR/player_photos -> slug/nimi osumana
    3) assets/player_photos/<Name>.png
    """
    raw = player_row.get("photo_path")
    if raw:
        p = Path(raw)
        if p.exists():
            return p

    photos_dir = DATA_DIR / "player_photos"
    if photos_dir.exists():
        base = _slugify(player_row.get("Name") or player_row.get("name") or "")
        for ext in (".png", ".jpg", ".jpeg"):
            candidates = list(photos_dir.glob(f"{base}*{ext}"))
            if candidates:
                return candidates[0]
        name_lower = (player_row.get("Name") or "").lower()
        for p in photos_dir.glob("*"):
            if name_lower and name_lower in p.stem.lower():
                return p

    assets_dir = Path(__file__).resolve().parent / "assets" / "player_photos"
    if assets_dir.exists():
        name = player_row.get("Name") or ""
        p = assets_dir / f"{name}.png"
        if p.exists():
            return p
    return None

def _save_players(updated: list[dict]) -> None:
    PLAYERS_FP.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")

def _update_player_photo(rec_id: str, photo_bytes: bytes, suggested_name: str) -> Path | None:
    photos_dir = DATA_DIR / "player_photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(suggested_name).suffix.lower() or ".png"
    safe = _slugify(suggested_name.rsplit(".", 1)[0])
    out = photos_dir / f"{safe}-{rec_id[:6]}{ext}"
    out.write_bytes(photo_bytes)

    data = load_json(PLAYERS_FP, [])
    for p in data:
        if str(p.get("id") or "") == str(rec_id):
            p["photo_path"] = str(out)
            break
    _save_players(data)
    return out

def _parse_iso(ts: str | None) -> datetime:
    try:
        return datetime.fromisoformat(ts or "")
    except Exception:
        return datetime.min

# 1–5 asteikko + migraatio 1–20 → 1–5
def _ratings_to_df(ratings) -> pd.DataFrame:
    if isinstance(ratings, str):
        try:
            ratings = json.loads(ratings)
        except Exception:
            ratings = []
    if not isinstance(ratings, list):
        ratings = []
    df = pd.DataFrame(ratings)
    if not {"attribute", "rating"}.issubset(df.columns):
        return pd.DataFrame(columns=["attribute", "rating", "comment"])

    s = pd.to_numeric(df["rating"], errors="coerce").fillna(1)
    # jos näkyy >5 arvoja, skaalataan vanhasta 1–20 asteikosta:
    if s.max() > 5:
        s = ((s - 1) // 4 + 1).clip(1, 5)
    df["rating"] = s.round().clip(1, 5).astype(int)
    if "comment" not in df.columns:
        df["comment"] = ""
    return df[["attribute","rating","comment"]]

# badge + kpi -tyylit
BADGE_CSS = """
<style>
.badges { display:flex; gap:.5rem; flex-wrap:wrap; }
.badge  { padding:.25rem .6rem; border-radius:999px; font-size:.85rem; font-weight:600;
          background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15); }
.kpi    { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08);
          padding:12px 14px; border-radius:12px; }
.kpi h4 { margin:0 0 6px 0; font-size:.9rem; opacity:.8; }
.kpi .val{ font-size:1.6rem; font-weight:700; }
</style>
"""

# ---------------- Player Preview (Scouting) ----------------
def show_player_preview():
    st.header("📸 Player Preview (Scouting)")
    st.caption(f"Data folder → {DATA_DIR}")
    _inject_css_once("BADGE_CSS_player_preview", BADGE_CSS)

    # 1) tiimin valinta
    teams = list_teams_all()
    if not teams:
        st.info("No teams yet. Add one in the sidebar.")
        return
    team = st.selectbox("Select Team", teams, key="preview_team")
    if not team:
        return

    # 2) pelaajat
    rows = _players_by_team(team)
    if not rows:
        st.info(f"No players found for team {team}.")
        return

    df = _ensure_df(rows)

    # id-aliakset
    if "id" not in df.columns and "Id" in df.columns:
        df.rename(columns={"Id": "id"}, inplace=True)

    # Age johdettuna DateOfBirthista
    if "DateOfBirth" in df.columns:
        df["Age"] = pd.to_datetime(df["DateOfBirth"], errors="coerce").apply(
            lambda bd: (date.today().year - bd.year - ((date.today().month, date.today().day) < (bd.month, bd.day)))
            if pd.notnull(bd) else None
        )

    # 3) pelaajan valinta
    names = df.get("Name", pd.Series(dtype=str)).fillna("").tolist()
    if not names:
        st.info("No players in this team.")
        return
    player_name = st.selectbox("Select Player", names, index=0, key="preview_player")
    if not player_name:
        return
    row = df[df["Name"] == player_name].iloc[0].to_dict()
    player_id = str(row.get("id") or "")

    # 4) yläkortti: kuva + ydintiedot
    c1, c2 = st.columns([1, 2])
    with c1:
        photo = _find_photo_for(row)
        if photo and photo.exists():
            st.image(str(photo), use_container_width=True)
        else:
            st.info("No photo. You can upload one below.")

        # --- FIXED: Update Photo -lohko ilman rikkinäistä try:ää ---
        with st.expander("Update Photo"):
            up = st.file_uploader(
                "Upload player photo (PNG/JPG)",
                type=["png", "jpg", "jpeg"],
                key="pp_upload"
            )
            if up is not None and player_id:
                out = _update_player_photo(
                    player_id,
                    up.read(),
                    suggested_name=f"{player_name}{Path(up.name).suffix}"
                )
                if out:
                    st.success("Photo saved.")
                    # EI ylimääräistä st.rerun(): nappi jo aiheuttaa yhden rerunin

    with c2:
        st.markdown(f"## {player_name}")

        prim = row.get("primary_position")
        secs = row.get("secondary_positions") or []
        if isinstance(secs, str):
            secs = [s.strip() for s in secs.split(",") if s.strip()]
        line = ""
        if prim:
            line += f"**Position:** {prim}"
        if secs:
            line += f"  •  _{', '.join(secs)}_"
        if line:
            st.write(line)

        info_cols = st.columns(3)
        with info_cols[0]:
            st.metric("Age", row.get("Age") or _age_from_dob(row.get("DateOfBirth")) or "-")
        with info_cols[1]:
            nat = row.get("Nationality") or "-"
            st.metric("Nationality", nat if nat else "-")
        with info_cols[2]:
            shirt = row.get("club_number")
            st.metric("Shirt #", shirt if shirt not in (None, "", 0) else "-")

        if row.get("notes"):
            st.write("**Notes:** ", row.get("notes"))

        if row.get("tags"):
            tags = row.get("tags")
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            if isinstance(tags, list) and tags:
                st.write("**Tags:** " + ", ".join(tags))

    st.markdown("---")

    # 5) Recent Match Reports for this player
    st.subheader("📝 Recent Match Reports")
    if not player_id:
        st.info("Player ID missing; cannot map reports.")
        return

    reports = load_json(REPORTS_FP, [])
    matches = {m.get("id"): m for m in load_json(MATCHES_FP, [])}
    my_reports = [r for r in reports if str(r.get("player_id")) == player_id]
    if not my_reports:
        st.info("No reports for this player yet. Create one in **Scout Match Reporter**.")
        return

    my_reports.sort(key=lambda r: _parse_iso(r.get("created_at")), reverse=True)

    for rep in my_reports:
        m = matches.get(rep.get("match_id"), {})
        dt = (m.get("datetime") or "")[:10]
        label = f"{m.get('home_team','?')} vs {m.get('away_team','?')}  ({dt})"
        with st.expander(label, expanded=False):
            # badge-metat
            badges = (
                f"<div class='badges'>"
                + (f"<span class='badge'>Position: {rep.get('position')}</span>" if rep.get("position") else "")
                + (f"<span class='badge'>Foot: {rep.get('foot')}</span>" if rep.get("foot") else "")
                + (f"<span class='badge'>Competition: {rep.get('competition')}</span>" if rep.get("competition") else "")
                + (f"<span class='badge'>Created: {(rep.get('created_at','')[:16]).replace('T',' ')}</span>" if rep.get("created_at") else "")
                + "</div>"
            )
            st.markdown(badges, unsafe_allow_html=True)

            if rep.get("general_comment"):
                st.markdown(f"**General Comment:** {rep.get('general_comment')}")

            df_r = _ratings_to_df(rep.get("ratings"))
            if df_r.empty:
                st.info("No attribute ratings in this report.")
                continue

            df_sorted = df_r.sort_values("rating", ascending=False).reset_index(drop=True)
            avg = df_sorted["rating"].mean()
            best_row  = df_sorted.iloc[0]
            worst_row = df_sorted.iloc[-1]

            # KPI-kortit
            k1, k2, k3 = st.columns(3)
            with k1:
                st.markdown("<div class='kpi'><h4>Average</h4><div class='val'>"
                            f"{avg:.1f}</div></div>", unsafe_allow_html=True)
            with k2:
                st.markdown("<div class='kpi'><h4>Best</h4><div class='val'>"
                            f"{best_row['attribute']} ({int(best_row['rating'])})</div></div>", unsafe_allow_html=True)
            with k3:
                st.markdown("<div class='kpi'><h4>Needs work</h4><div class='val'>"
                            f"{worst_row['attribute']} ({int(worst_row['rating'])})</div></div>", unsafe_allow_html=True)

            # Kompaktit kommentit (vain täytetyt)
            comments = [(r["attribute"], str(r.get("comment","")).strip()) for _, r in df_sorted.iterrows()]
            comm_nonempty = [(a,c) for a,c in comments if c]
            if comm_nonempty:
                st.markdown("**Notes by area:**")
                st.write("\n".join([f"- **{a}:** {c}" for a,c in comm_nonempty]))

            # Horisontaalinen bar 1–5
            fig = px.bar(
                df_sorted,
                x="rating",
                y="attribute",
                orientation="h",
                color="rating",
                color_continuous_scale="Blues",
                range_x=[1, 5],
                title=None,
                text="rating"
            )
            fig.update_layout(
                coloraxis_showscale=False,
                margin=dict(l=10,r=10,t=10,b=10),
                height=320
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(fig, use_container_width=True)

            # Taulukko
            st.dataframe(
                df_sorted.rename(columns={"attribute": "Attribute", "rating": "Rating", "comment": "Comment"}),
                use_container_width=True,
                hide_index=True,
            )

            # EI expanderia expanderin sisään → checkbox + container
            show_json = st.checkbox(
                "Show Ratings JSON",
                key=f"show_json_{rep.get('id') or rep.get('created_at') or id(rep)}"
            )
            if show_json:
                with st.container(border=True):
                    json_text = json.dumps(df_r.to_dict(orient="records"), ensure_ascii=False, indent=2)
                    st.code(json_text, language="json")

# Suora ajo
if __name__ == "__main__":
    show_player_preview()
