# add_player_form.py
import re
import unicodedata
import uuid
from datetime import date
from pathlib import Path

import streamlit as st

from postgrest.exceptions import APIError

from app.app_paths import DATA_DIR
from app.supabase_client import get_client

# ---------------------------
# Helpers
# ---------------------------
def _fetch_team_players(team: str) -> list[dict]:
    client = get_client()
    if not client or not team:
        return []
    try:
        res = (
            client.table("players")
            .select("id,name,date_of_birth,team_name,club_number")
            .eq("team_name", team)
            .execute()
        )
    except APIError as err:  # pragma: no cover - UI error handling
        st.error(f"Failed to load players from Supabase: {getattr(err, 'message', str(err))}")
        return []
    return [dict(row) for row in (res.data or [])]


def _resolve_team(team: str) -> dict | None:
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
    except APIError as err:  # pragma: no cover
        st.error(f"Failed to resolve team in Supabase: {getattr(err, 'message', str(err))}")
        return None
    rows = res.data or []
    return dict(rows[0]) if rows else None

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

def _push_to_master(team: str, record: dict) -> None:  # legacy helper retained
    """Clear cached data so new Supabase rows appear instantly in editors."""
    try:
        st.cache_data.clear()
    except Exception:
        pass

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

    existing_team = _fetch_team_players(team)
    existing_numbers = sorted({
        int(p.get("club_number") or 0)
        for p in existing_team
        if str(p.get("club_number", "")).isdigit()
    })

    with st.container():
        st.caption("Data source: Supabase · players table")
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
            save_btn = st.form_submit_button("💾 Tallenna pelaaja", use_container_width=True, type="primary")
        with right:
            save_add_btn = st.form_submit_button("💾 Tallenna ja lisää seuraava", use_container_width=True, type="primary")

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

            # Duplikaatti: sama nimi + DOB samassa joukkueessa
            dup = next(
                (
                    p
                    for p in existing_team
                    if _norm_name(p.get("name") or p.get("Name", "")) == nm
                    and str(p.get("date_of_birth") or "").split("T")[0] == dob.isoformat()
                ),
                None,
            )
            if dup:
                errors.append("Sama nimi ja syntymäpäivä löytyy jo tästä joukkueesta.")

            # Numeron varoitus (ei blokata)
            if club_number in existing_numbers and club_number != 0:
                st.info(f"Numero {club_number} on jo käytössä tässä joukkueessa.")

            if errors:
                for e in errors:
                    st.error(e)
                return

            client = get_client()
            if not client:
                st.error("Supabase client is not configured.")
                return

            team_row = _resolve_team(team)
            team_id = team_row.get("id") if team_row else None
            if team_id is None:
                try:
                    inserted = client.table("teams").insert({"name": team}).execute()
                    team_data = inserted.data or []
                    if team_data:
                        team_id = team_data[0].get("id")
                except APIError:
                    # If insert fails (likely due to unique constraint), try loading again
                    team_row = _resolve_team(team)
                    team_id = team_row.get("id") if team_row else None

            # Rakenna tietue Supabaseen
            rec_id = uuid.uuid4().hex
            secondary_positions = [p for p in secondary_pos if p]
            tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
            record = {
                "id": rec_id,
                "name": nm,
                "team_name": team,
                "team_id": team_id,
                "date_of_birth": dob.isoformat(),
                "nationality": (nationality or "").strip() or None,
                "height": int(height) if height else None,
                "weight": int(weight) if weight else None,
                "preferred_foot": _foot_label_to_value(preferred_foot_ui) or None,
                "club_number": int(club_number) if club_number else None,
                "primary_position": primary_pos,
                "secondary_positions": secondary_positions or None,
                "notes": (notes or "").strip() or None,
                "tags": tag_list or None,
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

            try:
                client.table("players").insert(record).execute()
            except APIError as err:
                st.error(f"Failed to save player to Supabase: {getattr(err, 'message', str(err))}")
                return

            _push_to_master(team, record)

            st.success(f"Pelaaja '{nm}' lisätty joukkueeseen {team}.")
            if save_add_btn:
                st.rerun()

if __name__ == "__main__":
    show_add_player_form()
