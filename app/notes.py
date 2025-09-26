# app/notes.py — Notes (read/write/search/tags/export)
from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import json
import pandas as pd
import streamlit as st
import json
from postgrest.exceptions import APIError
from app.ui import bootstrap_sidebar_auto_collapse

from app.supabase_client import get_client


bootstrap_sidebar_auto_collapse()

def _dbg(e: APIError, title="🔧 Supabase PostgREST -virhe"):
    with st.expander(title, expanded=True):
        st.code(
            f"code: {getattr(e,'code',None)}\n"
            f"message: {getattr(e,'message',str(e))}\n"
            f"details: {getattr(e,'details',None)}\n"
            f"hint: {getattr(e,'hint',None)}",
            "text",
        )

# ---------- IO ----------
@st.cache_data(show_spinner=False)
def _load_notes() -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
    try:
        res = client.table("notes").select("*").execute()
        data = res.data or []
        return data if isinstance(data, list) else []
    except APIError as e:
        _dbg(e)
        st.error("Notes-haku epäonnistui")
        return []


def _save_notes(data: List[Dict[str, Any]]) -> None:
    client = get_client()
    if not client:
        return
    try:
        client.table("notes").delete().neq("id", None).execute()
        if data:
            client.table("notes").insert(data).execute()
    except APIError as e:
        _dbg(e)
        st.error("Notes-tallennus epäonnistui")

# ---------- Utils ----------
def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _clean_tags(s: str) -> List[str]:
    if not s: return []
    out = []
    for part in s.replace(";", ",").split(","):
        t = part.strip()
        if t:
            out.append(t[:24])  # tiny cap
    # unique, preserve order
    seen = set(); res=[]
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower()); res.append(t)
    return res

def _fmt_ts(s: Optional[str]) -> str:
    if not s: return ""
    try:
        return datetime.fromisoformat(str(s)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(s)[:16].replace("T"," ")

# ---------- Main ----------
def show_notes():
    st.header("🗒️ Notes")

    # Load
    notes = _load_notes()

    # --- Add note ---
    st.subheader("Add a note")
    c1, c2 = st.columns([2.6, 1.4])
    with c1:
        text = st.text_area(
            "Note text",
            key="notes__new_text",
            height=120,
            placeholder="Observation, idea, follow-up…"
        )
    with c2:
        tags_str = st.text_input(
            "Tags (comma-separated)",
            key="notes__new_tags",
            placeholder="e.g. U23, LW, Brazil",
            autocomplete="off",
        )
        st.caption("Keep tags short; use commas to separate.")

    cc1, cc2, cc3 = st.columns([1,1,2.2])
    with cc1:
        if st.button("💾 Save note", key="notes__save", type="primary"):
            t = (text or "").strip()
            tags = _clean_tags(tags_str or "")
            if t:
                item = {"id": uuid.uuid4().hex, "created_at": _now_iso(), "text": t, "tags": tags}
                notes.append(item)
                _save_notes(notes)
                st.cache_data.clear()
                st.success("Saved.")
                st.rerun()
            else:
                st.warning("Write something first.")
    with cc2:
        if st.button("✖️ Clear", key="notes__clear", type="secondary"):
            st.session_state["notes__new_text"] = ""
            st.session_state["notes__new_tags"] = ""

    st.markdown("---")

    # --- Browse / search ---
    st.subheader("Browse")
    b1, b2, b3, b4 = st.columns([1.6, 1.2, 1.2, 1.0])
    with b1:
        raw_q = st.text_input(
            "Search text",
            key="notes__q",
            placeholder="find in text…",
            autocomplete="off",
        )
        q = (raw_q or "").strip().lower()
    # collect tag universe
    all_tags = []
    for n in notes:
        for t in n.get("tags", []):
            if t not in all_tags:
                all_tags.append(t)
    all_tags = sorted(all_tags, key=lambda s: s.lower())
    with b2:
        tag_sel = st.multiselect("Tags", options=all_tags, key="notes__tags")
    with b3:
        sort_order = st.selectbox("Sort", ["Newest first", "Oldest first"], key="notes__sort")
    with b4:
        if st.button("Reset filters", key="notes__reset", type="secondary"):
            st.session_state["notes__q"] = ""
            st.session_state["notes__tags"] = []
            st.session_state["notes__sort"] = "Newest first"
            st.rerun()

    d1, d2 = st.columns(2)
    with d1:
        from_date = st.date_input("From date", value=None, key="notes__from")
    with d2:
        to_date = st.date_input("To date", value=None, key="notes__to")

    # filter
    def _parse_dt(s: str) -> Optional[datetime]:
        try: return datetime.fromisoformat(s)
        except: return None

    filt = []
    for n in notes:
        ok = True
        if q:
            ok = q in (n.get("text","").lower())
        if ok and tag_sel:
            tags = n.get("tags", [])
            ok = any(t in tags for t in tag_sel)
        if ok and from_date:
            ts = _parse_dt(n.get("created_at",""))
            ok = (ts is not None) and (ts.date() >= from_date)
        if ok and to_date:
            ts = _parse_dt(n.get("created_at",""))
            ok = (ts is not None) and (ts.date() <= to_date)
        if ok:
            filt.append(n)

    reverse = (sort_order == "Newest first")
    filt.sort(key=lambda n: n.get("created_at",""), reverse=reverse)

    st.caption(f"{len(filt)} / {len(notes)} notes shown")

    # Pagination
    p1, p2 = st.columns([1.1, 1])
    with p1:
        page_size = st.selectbox("Rows per page", [10, 20, 50, 100], index=1, key="notes__pagesize")
    with p2:
        total = len(filt)
        pages = max(1, (total + int(page_size) - 1) // int(page_size))
        page = st.number_input("Page", min_value=1, max_value=int(pages), value=1, key="notes__page")
    start = (int(page)-1) * int(page_size)
    end = start + int(page_size)
    page_items = filt[start:end]

    # Bulk delete (optional)
    st.markdown("#### Bulk delete")
    if page_items:
        ids = [n["id"] for n in page_items]
        picks = st.multiselect("Select notes to delete", options=ids, format_func=lambda nid: next((f"{_fmt_ts(n['created_at'])}  •  {(n['text'][:40] + '…' if len(n['text'])>40 else n['text'])}" for n in page_items if n['id']==nid), nid), key="notes__bulk")
        st.warning("Type DELETE to confirm bulk deletion.", icon="⚠️")
        confirm = st.text_input(
            "Confirmation",
            key="notes__confirm",
            placeholder="DELETE",
            autocomplete="off",
        )
        if st.button(
            f"🗑️ Delete selected ({len(picks)})",
            disabled=(len(picks)==0 or confirm!="DELETE"),
            key="notes__bulk_del",
            type="secondary",
        ):
            kept = [n for n in notes if n.get("id") not in set(picks)]
            _save_notes(kept)
            st.cache_data.clear()
            st.success(f"Deleted {len(picks)} note(s).")
            st.rerun()

    st.markdown("---")

    # Render list
    if not page_items:
        st.info("No notes for current filters.")
    else:
        for n in page_items:
            with st.container(border=True):
                top = st.columns([2.4, 1.2, 0.9])
                with top[0]:
                    st.caption(_fmt_ts(n.get("created_at")))
                with top[1]:
                    tg = n.get("tags", []) or []
                    if tg:
                        st.caption(" ".join(f"`{t}`" for t in tg))
                with top[2]:
                    if st.button("🗑️ Delete", key=f"notes__del_{n['id']}", type="secondary"):
                        kept = [m for m in notes if m.get("id") != n["id"]]
                        _save_notes(kept)
                        st.cache_data.clear()
                        st.success("Deleted.")
                        st.rerun()

                # Text
                st.write(n.get("text",""))

                # Inline edit
                with st.expander("✏️ Edit"):
                    new_text = st.text_area("Edit text", value=n.get("text",""), key=f"notes__edit_text_{n['id']}", height=120)
                    new_tags = st.text_input(
                        "Edit tags (comma-separated)",
                        value=", ".join(n.get("tags", [])),
                        key=f"notes__edit_tags_{n['id']}",
                        autocomplete="off",
                    )
                    if st.button("💾 Save changes", key=f"notes__edit_save_{n['id']}", type="primary"):
                        n["text"] = (new_text or "").strip()
                        n["tags"] = _clean_tags(new_tags or "")
                        # write back (keep ordering)
                        updated = []
                        for m in notes:
                            updated.append(n if m.get("id")==n["id"] else m)
                        _save_notes(updated)
                        st.cache_data.clear()
                        st.success("Updated.")
                        st.rerun()

    # Export
    st.markdown("---")
    st.subheader("Export")
    # JSON
    st.download_button(
        "⬇️ Download JSON",
        data=json.dumps(filt, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="notes_filtered.json",
        mime="application/json",
        use_container_width=True,
        key="notes__dl_json"
    )
    # CSV
    try:
        df = pd.DataFrame(filt)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            data=csv,
            file_name="notes_filtered.csv",
            mime="text/csv",
            use_container_width=True,
            key="notes__dl_csv"
        )
    except Exception:
        pass

if __name__ == "__main__":
    show_notes()
