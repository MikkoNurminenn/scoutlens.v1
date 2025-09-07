# add_player_form.py
import json
import re
import unicodedata
import uuid
from datetime import date
from pathlib import Path

import streamlit as st
import pandas as pd  # NEW

from app.app_paths import file_path, DATA_DIR
from app.data_utils import (
    load_master, save_master
)

PLAYERS_FP = file_path("players.json")

# ---------------------------
# Helpers
# ---------------------------
def _load_players() -> list:
    try:
        if PLAYERS_FP.exists():
            return json.loads(PLAYERS_FP.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def _save_players(data: list) -> None:
    PLAYERS_FP.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _norm_name(s: str) -> str:
    s = (s or "").strip()
    parts = [p.capitalize() if len(p) > 1 else p.upper() for p in s.split()]
    return " ".join(parts)

def _slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or "player"

def _age_from_dob(d: date) -> int:
    today = date.today()
    return today.year - d.year - ((today.month, today.day) < (d.month, d.day))

def _foot_label_to_value(lbl: str) -> str:
    return {"Oikea": "Right", "Vasen": "Left", "Molemmat": "Both", "": ""}.get(lbl, lbl)

def _normalize_nat(v) -> str:  # NEW
    if v is None:
        return ""
    if isinstance(v, (list, tuple, set)):
        return ", ".join(str(x).strip() for x in v if str(x).strip())
    return str(v).strip()

def _next_free_id(existing_ids):  # NEW
    existing = set(int(x) for x in existing_ids if pd.notna(x))
    idx = 1
    while idx in existing:
        idx += 1
    return idx

def _ensure_min_master(df: pd.DataFrame) -> pd.DataFrame:  # NEW
    cols = [
        "PlayerID","Name","Nationality","DateOfBirth",
        "PreferredFoot","ClubNumber","Position","ScoutRating"
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = 0 if c in ("PlayerID","ClubNumber","ScoutRating") else ""
    return df

def _push_to_master(team: str, record: dict) -> None:  # NEW
    """
    Synkkaa lomakkeesta lisätty pelaaja myös tiimin masteriin,
    jotta Player Editor näkee sen heti.
    Matchaa rivin (Name, DateOfBirth) perusteella — jos löytyy, päivittää rivin;
    muuten lisää uuden ja antaa vapaan PlayerID:n.
    """
    df = load_master(team)
    if df is None or df.empty:
        df = pd.DataFrame(columns=[
            "PlayerID","Name","Nationality","DateOfBirth",
            "PreferredFoot","ClubNumber","Position","ScoutRating"
        ])

    df = _ensure_min_master(df)

    name = _norm_name(record.get("name",""))
    dob  = (record.get("date_of_birth") or "").split("T")[0]
    nat  = _normalize_nat(record.get("nationality",""))
    foot = record.get("preferred_foot","") or ""
    num  = int(record.get("club_number") or 0)
    pos  = record.get("primary_position") or record.get("position") or ""
    sr   = int(record.get("scout_rating") or 0)

    # Etsi olemassa oleva rivi (sama nimi + DOB)
    mask = (df["Name"].astype(str).str.strip().str.lower() == name.lower()) & \
           (df["DateOfBirth"].astype(str).str.strip() == dob)
    if mask.any():
        idx = df.index[mask][0]
        df.at[idx, "Nationality"]   = nat
        df.at[idx, "PreferredFoot"] = foot
        df.at[idx, "ClubNumber"]    = num
        df.at[idx, "Position"]      = pos
        # Päivitä ScoutRating vain jos olemassa (ei pakko)
        if "ScoutRating" in df.columns:
            df.at[idx, "ScoutRating"] = sr
    else:
        # Uusi rivi
        next_id = _next_free_id(pd.to_numeric(df["PlayerID"], errors="coerce").fillna(0).astype(int).tolist())
        new_row = {
            "PlayerID": next_id,
            "Name": name,
            "Nationality": nat,
            "DateOfBirth": dob,
            "PreferredFoot": foot,
            "ClubNumber": num,
            "Position": pos,
            "ScoutRating": sr,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    save_master(df, team)

POSITIONS_PRIMARY = [
    "GK","RB","RWB","CB","LB","LWB","DM","CM","AM","RW","LW","ST"
]

# ---------------------------
# UI
# ---------------------------
def show_add_player_form():
    st.header("➕ Add Player")

    team = st.session_state.get("selected_team")
    if not team:
        st.warning("Valitse ensin joukkue sivupalkista (⚽ Team & Season).")
        return

    players = _load_players()
    existing_team = [p for p in players if (p.get("team_name") or p.get("Team") or p.get("team")) == team]
    existing_numbers = sorted({
        int(p.get("club_number") or 0)
        for p in existing_team
        if str(p.get("club_number","")).isdigit()
    })

    with st.container():
        st.caption(f"Data: {PLAYERS_FP}")
        st.markdown(f"**Joukkue:** {team}")

    with st.form("add_player_form", clear_on_submit=False):
        st.subheader("Perustiedot")
        c1, c2, c3 = st.columns([2,1.2,1])
        with c1:
            name = st.text_input("Nimi *", placeholder="Etunimi Sukunimi")
        with c2:
            dob = st.date_input("Syntymäpäivä *", value=date(2004, 1, 1), min_value=date(1970,1,1), max_value=date.today())
            st.caption(f"Ikä: {_age_from_dob(dob)} v")
        with c3:
            nationality = st.text_input("Kansallisuus", placeholder="ARG / BRA / URU ...")

        c4, c5, c6 = st.columns([1,1,1])
        with c4:
            default_idx = POSITIONS_PRIMARY.index("CM") if "CM" in POSITIONS_PRIMARY else 0
            primary_pos = st.selectbox("Pelipaikka (ensisijainen)", POSITIONS_PRIMARY, index=default_idx)
        with c5:
            secondary_pos = st.multiselect("Pelipaikat (toissijaiset)", [p for p in POSITIONS_PRIMARY if p != primary_pos])
        with c6:
            preferred_foot_ui = st.selectbox("Vahvempi jalka", ["", "Oikea", "Vasen", "Molemmat"])

        st.subheader("Fyysiset tiedot")
        c7, c8, c9 = st.columns([1,1,1])
        with c7:
            height = st.number_input("Pituus (cm)", min_value=0, max_value=250, step=1, value=0, help="0 = ei tietoa")
        with c8:
            weight = st.number_input("Paino (kg)", min_value=0, max_value=200, step=1, value=0, help="0 = ei tietoa")
        with c9:
            club_number = st.number_input("Pelinumero", min_value=0, max_value=99, step=1, value=0)

        with st.expander("Lisätiedot (valinnainen)"):
            notes = st.text_area("Muistiinpanot")
            tags = st.text_input("Tunnisteet (pilkulla eroteltuna)", placeholder="U23, trial, high-potential")

        st.subheader("Kuva (valinnainen)")
        photo = st.file_uploader("Lataa pelaajakuva (PNG/JPG)", type=["png","jpg","jpeg"])

        left, right = st.columns([1,1])
        with left:
            save_btn = st.form_submit_button("💾 Tallenna pelaaja", use_container_width=True)
        with right:
            save_add_btn = st.form_submit_button("💾 Tallenna ja lisää seuraava", use_container_width=True)

        # ---------------------------
        # Validation & Save
        # ---------------------------
        if save_btn or save_add_btn:
            errors = []

            nm = _norm_name(name)
            if not nm:
                errors.append("Nimi on pakollinen.")

            age = _age_from_dob(dob)
            if age < 12 or age > 45:
                st.warning("Tarkista syntymävuosi: poikkeuksellinen ikä skouttikontekstissa.")

            if height and (height < 120 or height > 220):
                st.warning("Pituus näyttää poikkeavalta. Tarkista yksikkö (cm).")
            if weight and (weight < 40 or weight > 120):
                st.warning("Paino näyttää poikkeavalta. Tarkista yksikkö (kg).")

            # Duplikaatti: sama nimi + DOB samassa joukkueessa (players.json)
            dup = next((p for p in existing_team
                        if _norm_name(p.get("name") or p.get("Name","")) == nm
                        and (p.get("date_of_birth") or p.get("DateOfBirth","")).split("T")[0] == dob.isoformat()), None)
            if dup:
                errors.append("Sama nimi ja syntymäpäivä löytyy jo tästä joukkueesta.")

            # Numeron varoitus (ei blokata)
            if club_number in existing_numbers and club_number != 0:
                st.info(f"Numero {club_number} on jo käytössä tässä joukkueessa.")

            if errors:
                for e in errors:
                    st.error(e)
                return

            # Rakenna tietue
            rec_id = uuid.uuid4().hex
            record = {
                "id": rec_id,
                "name": nm,
                "team_name": team,
                "date_of_birth": dob.isoformat(),
                "nationality": (nationality or "").strip(),
                "height": int(height or 0),
                "weight": int(weight or 0),
                "preferred_foot": _foot_label_to_value(preferred_foot_ui),
                "club_number": int(club_number or 0),
                "primary_position": primary_pos,
                "secondary_positions": secondary_pos,
                "notes": (notes or "").strip(),
                "tags": [t.strip() for t in (tags or "").split(",") if t.strip()],
            }

            # Tallenna kuva (jos annettu)
            if photo is not None:
                photos_dir = DATA_DIR / "player_photos"
                photos_dir.mkdir(parents=True, exist_ok=True)
                ext = Path(photo.name).suffix.lower() or ".png"
                safe_name = _slugify(f"{nm}-{rec_id[:6]}")
                out_path = photos_dir / f"{safe_name}{ext}"
                out_path.write_bytes(photo.read())
                record["photo_path"] = str(out_path)

            # 1) Kirjoita players.json
            players = _load_players()
            players.append(record)
            _save_players(players)

            # 2) Puske myös masteriin → näkyy heti Player Editorissa
            _push_to_master(team, record)

            st.success(f"Pelaaja '{nm}' lisätty joukkueeseen {team}.")
            if save_add_btn:
                st.rerun()

if __name__ == "__main__":
    show_add_player_form()
