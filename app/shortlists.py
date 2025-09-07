# app/shortlists.py — Shortlists (simple, fast)
from __future__ import annotations
from typing import Any, Dict, List

import streamlit as st
from postgrest.exceptions import APIError
import traceback

from supabase_client import get_client
from utils.supa import first_row


# ---------- Debug helper ----------
def _pgrest_debug(e: APIError, title: str = "🔧 Supabase PostgREST -virhe (debug)"):
    """Näytä PostgREST-virheen kentät expanderissa kaatamatta sovellusta."""
    with st.expander(title, expanded=True):
        st.code(
            f"""code:    {getattr(e, 'code', None)}
message: {getattr(e, 'message', str(e))}
details: {getattr(e, 'details', None)}
hint:    {getattr(e, 'hint', None)}""",
            language="text",
        )


# ---------- IO ----------
def _load_players() -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
    try:
        res = client.table("players").select("*").execute()
        return res.data or []
    except APIError as e:
        _pgrest_debug(e)
        return []
    except Exception:
        return []


def _load_shortlists() -> Dict[str, List[str]]:
    client = get_client()
    if not client:
        return {}
    try:
        res = (
            client.table("shortlists")
            .select("id,name,items:shortlist_items(player_id)")
            .execute()
        )
        out: Dict[str, List[str]] = {}
        for r in res.data or []:
            name = (r.get("name") or "").strip()
            if not name:
                continue
            items = r.get("items") or []
            out[name] = [str(it.get("player_id")) for it in items if it.get("player_id")]
        return out
    except APIError as e:
        _pgrest_debug(e)
        return {}
    except Exception:
        return {}


def _save_shortlists(data: Dict[str, List[str]]):
    client = get_client()
    if not client:
        return
    try:
        client.table("shortlist_items").delete().neq("id", "").execute()
        client.table("shortlists").delete().neq("id", "").execute()
        for name, ids in data.items():
            res = client.table("shortlists").insert({"name": name}).execute()
            sl_id = (first_row(res) or {}).get("id")
            if sl_id and ids:
                rows = [{"shortlist_id": sl_id, "player_id": pid} for pid in ids]
                client.table("shortlist_items").insert(rows).execute()
    except APIError as e:
        _pgrest_debug(e)
        st.error("❌ Save failed")
        st.code("".join(traceback.format_exc()), language="text")
        raise
    except Exception:
        st.error("❌ Save failed")
        st.code("".join(traceback.format_exc()), language="text")
        raise


# ---------- helpers ----------
def _player_name(p: Dict[str, Any]) -> str:
    return str(p.get("name") or p.get("Name") or "").strip()

def _player_club(p: Dict[str, Any]) -> str:
    return str(p.get("current_club") or "").strip()

def _player_pos(p: Dict[str, Any]) -> str:
    return str(p.get("position") or p.get("Preferred Position") or p.get("pos") or "").strip()

def _export_rows(players: List[Dict[str, Any]], ids: List[str]) -> List[Dict[str, str]]:
    idx = {str(p.get("id")): p for p in players}
    out = []
    for pid in ids:
        p = idx.get(str(pid), {})
        out.append({
            "Name": _player_name(p),
            "Club": _player_club(p),
            "Position": _player_pos(p),
        })
    return out


# ---------- PAGE ----------
def show_shortlists():
    st.markdown("## ⭐ Shortlists")

    players = _load_players()
    shortlists = _load_shortlists()

    # left: lists, right: contents
    left, right = st.columns([1, 2], gap="large")

    # ----- LEFT: lists -----
    with left:
        st.markdown("#### Lists")
        list_names = sorted(shortlists.keys())
        if not list_names:
            st.info("No shortlists yet. Create one below.")

        sel = st.selectbox("Select", list_names or ["—"], index=0 if list_names else 0, key="sl_sel_page")
        new_nm = st.text_input("New list name", placeholder="e.g. U23 Forwards")
        c1, c2 = st.columns([1, 1])
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
            name_to_id = {
                _player_name(p): str(p.get("id"))
                for p in players
                if _player_name(p) and p.get("id")
            }
            name_pool = sorted(name_to_id.keys())
            add = st.multiselect(
                "Add players",
                options=name_pool,
                default=[],
                key=f"sl_add_multi_{sel}",
            )
            cadd, cclear = st.columns([1, 1])
            if cadd.button("Add selected"):
                added = 0
                for n in add:
                    pid = name_to_id.get(n)
                    if pid and pid not in shortlists[sel]:
                        shortlists[sel].append(pid)
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
            players_by_id = {str(p.get("id")): p for p in players}
            if not items:
                st.caption("List is empty.")
            else:
                # tiny controls per row
                for i, pid in enumerate(items):
                    rc1, rc2, rc3, rc4 = st.columns([6, 1, 1, 1])
                    nm = _player_name(players_by_id.get(pid, {})) or pid
                    rc1.write(f"- **{nm}**")
                    if rc2.button("⬆️", key=f"up_{sel}_{i}", help="Move up") and i > 0:
                        items[i - 1], items[i] = items[i], items[i - 1]
                        _save_shortlists(shortlists); st.rerun()
                    if rc3.button("⬇️", key=f"dn_{sel}_{i}", help="Move down") and i < len(items) - 1:
                        items[i + 1], items[i] = items[i], items[i + 1]
                        _save_shortlists(shortlists); st.rerun()
                    if rc4.button("Remove", key=f"rm_{sel}_{i}"):
                        items.pop(i); _save_shortlists(shortlists); st.rerun()

                # export
                st.divider()
                rows = _export_rows(players, items)
                if rows:
                    import csv, io
                    buf = io.StringIO()
                    w = csv.DictWriter(buf, fieldnames=["Name", "Club", "Position"])
                    w.writeheader(); w.writerows(rows)
                    st.download_button(
                        "⬇️ Export CSV",
                        data=buf.getvalue().encode("utf-8"),
                        file_name=f"shortlist_{sel}.csv",
                        mime="text/csv",
                    )
        else:
            st.caption("Pick or create a list on the left.")
