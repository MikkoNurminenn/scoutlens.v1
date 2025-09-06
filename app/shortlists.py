# app/shortlists.py — Shortlists (simple, fast)
from __future__ import annotations
from typing import Any, Dict, List

import streamlit as st

from supabase_client import get_client

# ---------- IO ----------
def _load_players() -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
    res = client.table("players").select("*").execute()
    return res.data or []


def _load_shortlists() -> Dict[str, List[str]]:
    client = get_client()
    if not client:
        return {}
    res = client.table("shortlists").select("name,player_id").execute()
    out: Dict[str, List[str]] = {}
    for r in res.data or []:
        name = r.get("name")
        pid = r.get("player_id")
        if name and pid is not None:
            out.setdefault(name, []).append(str(pid))
    return out


def _save_shortlists(data: Dict[str, List[str]]):
    client = get_client()
    if not client:
        return
    client.table("shortlists").delete().neq("name", "").execute()
    rows = []
    for name, ids in data.items():
        for pid in ids:
            rows.append({"name": name, "player_id": str(pid)})
    if rows:
        client.table("shortlists").insert(rows).execute()

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
                _save_shortlists(shortlists)
                st.success(f"Created '{nn}'")
                st.cache_data.clear(); st.rerun()
        if sel in shortlists and c2.button("Delete"):
            shortlists.pop(sel, None)
            _save_shortlists(shortlists)
            st.warning(f"Deleted '{sel}'")
            st.cache_data.clear(); st.rerun()

        # rename
        if sel in shortlists:
            rn = st.text_input("Rename", value=sel, key="sl_rename")
            if rn.strip() and rn.strip() != sel and st.button("Apply rename"):
                shortlists[rn.strip()] = shortlists.pop(sel)
                _save_shortlists(shortlists)
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
                    _save_shortlists(shortlists)
                    st.success(f"Added {added} players")
                    st.cache_data.clear(); st.rerun()
            if cclear.button("Clear list"):
                shortlists[sel] = []
                _save_shortlists(shortlists)
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
                        _save_shortlists(shortlists); st.rerun()
                    if rc3.button("⬇️", key=f"dn_{sel}_{i}", help="Move down") and i < len(items)-1:
                        items[i+1], items[i] = items[i], items[i+1]
                        _save_shortlists(shortlists); st.rerun()
                    if rc4.button("Remove", key=f"rm_{sel}_{i}"):
                        items.pop(i); _save_shortlists(shortlists); st.rerun()

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
