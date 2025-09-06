# app/shortlists.py — Shortlists (simple, fast)
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from app_paths import file_path
from storage import load_json, save_json

PLAYERS_FP     = file_path("players.json")
SHORTLISTS_FP  = file_path("shortlists.json")

# ---------- IO ----------
@st.cache_data(show_spinner=False)
def _load_players() -> List[Dict[str, Any]]:
    data = load_json(PLAYERS_FP, [])
    return data if isinstance(data, list) else []

def _load_shortlists() -> Dict[str, List[str]]:
    root = load_json(SHORTLISTS_FP, {})
    return root if isinstance(root, dict) else {}

# ---------- helpers ----------
def _player_name(p: Dict[str, Any]) -> str:
    return str(p.get("name") or p.get("Name") or "").strip()

def _player_team(p: Dict[str, Any]) -> str:
    return str(p.get("team_name") or p.get("Team") or p.get("team") or p.get("current_club") or "").strip()

def _player_pos(p: Dict[str, Any]) -> str:
    return str(p.get("position") or p.get("Preferred Position") or p.get("pos") or "").strip()

def _export_rows(players: List[Dict[str, Any]], names: List[str]) -> List[Dict[str, str]]:
    idx = { _player_name(p): p for p in players }
    out = []
    for n in names:
        p = idx.get(n, {})
        out.append({
            "Name": n,
            "Team": _player_team(p),
            "Position": _player_pos(p),
        })
    return out

# ---------- PAGE ----------
def show_shortlists():
    st.markdown("## ⭐ Shortlists")

    players = _load_players()
    shortlists = _load_shortlists()

    # left: lists, right: contents
    left, right = st.columns([1,2], gap="large")

    # ----- LEFT: lists -----
    with left:
        st.markdown("#### Lists")
        list_names = sorted(shortlists.keys())
        if not list_names:
            st.info("No shortlists yet. Create one below.")

        sel = st.selectbox("Select", list_names or ["—"], index=0 if list_names else 0, key="sl_sel_page")
        new_nm = st.text_input("New list name", placeholder="e.g. U23 Forwards")
        c1, c2 = st.columns([1,1])
        if c1.button("Create"):
            nn = new_nm.strip()
            if nn and nn not in shortlists:
                shortlists[nn] = []
                save_json(SHORTLISTS_FP, shortlists)
                st.success(f"Created '{nn}'")
                st.cache_data.clear(); st.rerun()
        if sel in shortlists and c2.button("Delete"):
            shortlists.pop(sel, None)
            save_json(SHORTLISTS_FP, shortlists)
            st.warning(f"Deleted '{sel}'")
            st.cache_data.clear(); st.rerun()

        # rename
        if sel in shortlists:
            rn = st.text_input("Rename", value=sel, key="sl_rename")
            if rn.strip() and rn.strip() != sel and st.button("Apply rename"):
                shortlists[rn.strip()] = shortlists.pop(sel)
                save_json(SHORTLISTS_FP, shortlists)
                st.success("Renamed")
                st.cache_data.clear(); st.rerun()

    # ----- RIGHT: items & manage -----
    with right:
        st.markdown("#### Players in list")
        if sel in shortlists:
            # quick add
            name_pool = sorted({ _player_name(p) for p in players if _player_name(p) })
            default_add = []
            add = st.multiselect("Add players", options=name_pool, default=default_add, key=f"sl_add_multi_{sel}")
            cadd, cclear = st.columns([1,1])
            if cadd.button("Add selected"):
                added = 0
                for n in add:
                    if n and n not in shortlists[sel]:
                        shortlists[sel].append(n)
                        added += 1
                if added:
                    save_json(SHORTLISTS_FP, shortlists)
                    st.success(f"Added {added} players")
                    st.cache_data.clear(); st.rerun()
            if cclear.button("Clear list"):
                shortlists[sel] = []
                save_json(SHORTLISTS_FP, shortlists)
                st.warning("Cleared")
                st.cache_data.clear(); st.rerun()

            st.divider()

            items = shortlists.get(sel, [])
            if not items:
                st.caption("List is empty.")
            else:
                # tiny controls per row
                for i, nm in enumerate(items):
                    rc1, rc2, rc3, rc4 = st.columns([6,1,1,1])
                    rc1.write(f"- **{nm}**")
                    if rc2.button("⬆️", key=f"up_{sel}_{i}", help="Move up") and i>0:
                        items[i-1], items[i] = items[i], items[i-1]
                        save_json(SHORTLISTS_FP, shortlists); st.rerun()
                    if rc3.button("⬇️", key=f"dn_{sel}_{i}", help="Move down") and i < len(items)-1:
                        items[i+1], items[i] = items[i], items[i+1]
                        save_json(SHORTLISTS_FP, shortlists); st.rerun()
                    if rc4.button("Remove", key=f"rm_{sel}_{i}"):
                        items.pop(i); save_json(SHORTLISTS_FP, shortlists); st.rerun()

                # export
                st.divider()
                rows = _export_rows(players, items)
                if rows:
                    import csv, io
                    buf = io.StringIO()
                    w = csv.DictWriter(buf, fieldnames=["Name","Team","Position"])
                    w.writeheader(); w.writerows(rows)
                    st.download_button("⬇️ Export CSV", data=buf.getvalue().encode("utf-8"),
                                       file_name=f"shortlist_{sel}.csv", mime="text/csv")
        else:
            st.caption("Pick or create a list on the left.")
