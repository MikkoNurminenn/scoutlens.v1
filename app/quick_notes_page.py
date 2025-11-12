# app/pages/quick_notes.py
"""Streamlit page for Quick Notes with improved UX, validation, and state handling.

UI concerns only; data is handled in `app.services.quick_notes`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from html import escape
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import csv
import streamlit as st

from app.services.quick_notes import (
    create_quick_note,
    delete_quick_note,
    get_player_note_counts,
    get_quick_note,
    list_players,
    list_quick_notes,
    update_quick_note,
)

# ---------------------------- Constants & Keys ---------------------------- #

CSS_PATH = Path(".streamlit") / "component.css"
PAGE_KEY_PREFIX = "qn_"
TOAST_TYPES = {"success": "✅", "warning": "⚠️", "error": "❌"}
PAGE_SIZE_OPTIONS = [10, 20, 50, 100]
CARD_CONTENT_LIMIT = 500

# State key helpers to avoid collisions and typos
def k(suffix: str) -> str:
    return PAGE_KEY_PREFIX + suffix

FILTER_Q_KEY = k("filter_q")
FILTER_PLAYER_KEY = k("filter_player")
FILTER_TAGS_KEY = k("filter_tags")
FILTER_FROM_KEY = k("filter_date_from")
FILTER_TO_KEY = k("filter_date_to")
PAGE_SIZE_KEY = k("page_size")
PENDING_WIDGET_SYNC_KEY = k("pending_widget_sync")

# ----------------------------- Data Models -------------------------------- #

@dataclass
class Filters:
    """In-memory filter state for the list view."""
    q: str = ""
    player_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


@dataclass
class Pagination:
    """Offset-based pagination state."""
    page: int = 1
    page_size: int = 20


# ---------------------------- Utility & State ----------------------------- #

def load_css() -> None:
    """Load component CSS exactly once; inform if not present."""
    flag = k("css_loaded")
    if st.session_state.get(flag):
        return
    if CSS_PATH.exists():
        css = CSS_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        st.session_state[flag] = True
    else:
        st.info("Quick Notes styles missing (.streamlit/component.css)")


def init_state() -> None:
    """Initialize session state with sensible defaults and URL hydration."""
    ss = st.session_state
    ss.setdefault(k("filters"), Filters())
    ss.setdefault(k("pagination"), Pagination())
    ss.setdefault(k("modal_new"), False)
    ss.setdefault(k("modal_edit_id"), None)
    ss.setdefault(k("modal_delete_id"), None)
    ss.setdefault(k("toast"), {"type": None, "msg": ""})
    ss.setdefault(k("last_notes"), [])
    ss.setdefault(k("expanded_notes"), set())  # note IDs that are expanded

    # URL -> State hydration (idempotent)
    _hydrate_from_query_params()

    # Mirror state into widget keys
    filters: Filters = ss[k("filters")]
    ss.setdefault(FILTER_Q_KEY, filters.q)
    ss.setdefault(FILTER_PLAYER_KEY, filters.player_id or "")
    ss.setdefault(FILTER_TAGS_KEY, _format_tags_csv(filters.tags))
    ss.setdefault(FILTER_FROM_KEY, filters.date_from.date() if filters.date_from else None)
    ss.setdefault(FILTER_TO_KEY, filters.date_to.date() if filters.date_to else None)

    pagination: Pagination = ss[k("pagination")]
    ss.setdefault(PAGE_SIZE_KEY, pagination.page_size)

    _apply_pending_widget_state()


def _apply_pending_widget_state() -> None:
    """Apply queued widget value updates before rendering inputs."""
    pending = st.session_state.pop(PENDING_WIDGET_SYNC_KEY, None)
    if not pending:
        return
    for key, value in pending.items():
        st.session_state[key] = value


def _queue_widget_state(updates: Dict[str, Any]) -> None:
    """Queue widget value updates to be applied on the next run."""
    if not updates:
        return
    pending = st.session_state.setdefault(PENDING_WIDGET_SYNC_KEY, {})
    pending.update(updates)


def set_toast(message: str, kind: str = "success") -> None:
    """Queue a toast for the next render tick."""
    st.session_state[k("toast")] = {"type": kind, "msg": message}


def pop_toast() -> None:
    """Display queued toast, if any."""
    toast = st.session_state.get(k("toast"), {})
    if toast.get("msg") and toast.get("type"):
        icon = TOAST_TYPES.get(toast["type"], "ℹ️")
        st.toast(toast["msg"], icon=icon)
    st.session_state[k("toast")] = {"type": None, "msg": ""}


def _local_timezone() -> ZoneInfo:
    """Determine local tz from session or system; fallback to UTC."""
    tz_name = st.session_state.get("user_timezone")
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            # Why: end-user can pass an invalid tz via settings.
            set_toast(f"Tuntematon aikavyöhyke: {tz_name}", "warning")
    try:
        return ZoneInfo(str(datetime.now().astimezone().tzinfo))
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def format_ts(value: Optional[datetime]) -> str:
    """Human-friendly timestamp in Finnish."""
    if value is None:
        return "-"
    tz = _local_timezone()
    dt = value if value.tzinfo else value.replace(tzinfo=ZoneInfo("UTC"))
    local = dt.astimezone(tz)
    today = datetime.now(tz).date()
    if local.date() == today:
        return local.strftime("tänään, klo %H:%M")
    if local.date() == today - timedelta(days=1):
        return local.strftime("eilen, klo %H:%M")
    return local.strftime("%d.%m.%Y %H:%M")


# ------------------------------ Rendering --------------------------------- #

def render_header(players: List[Dict[str, Any]], counts: Dict[str, int]) -> None:
    st.title("🗒️ Quick Notes")
    total_notes = sum(counts.values())
    st.caption(
        f"{len(players)} pelaajaa, {total_notes} muistiinpanoa."
        if total_notes
        else "Ei muistiinpanoja vielä."
    )


def render_actions(players: List[Dict[str, Any]]) -> None:
    cols = st.columns([1, 1, 3])
    with cols[0]:
        if st.button(
            "➕ Uusi muistiinpano",
            type="primary",
            use_container_width=True,
            disabled=not players,
        ):
            st.session_state[k("modal_new")] = True
    with cols[1]:
        if st.button("🔄 Päivitä", use_container_width=True):
            st.rerun()
    with cols[2]:
        _render_export_button()


def _render_export_button() -> None:
    """Export currently listed notes (last fetch) to CSV."""
    notes = st.session_state.get(k("last_notes"), [])
    if not notes:
        st.button("⤓ Vie CSV", disabled=True, use_container_width=True)
        return
    csv_bytes = _notes_to_csv_bytes(notes)
    st.download_button(
        "⤓ Vie CSV",
        data=csv_bytes,
        file_name="quick_notes.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_filters(players: List[Dict[str, Any]]) -> None:
    filters: Filters = st.session_state[k("filters")]
    player_options = [("", "Kaikki")] + [
        (player.get("id") or "", player.get("name") or "Nimetön pelaaja")
        for player in players
    ]
    default_index = next(
        (idx for idx, option in enumerate(player_options) if option[0] == (filters.player_id or "")),
        0,
    )

    with st.form(k("filters_form")):
        st.markdown("### Suodattimet")
        col_a, col_b = st.columns([2, 1])
        with col_a:
            q = st.text_input(
                "Haku",
                placeholder="Etsi otsikosta tai sisällöstä",
                key=FILTER_Q_KEY,
            )
        with col_b:
            player_ids = [option[0] for option in player_options]
            player_labels = {option[0]: option[1] for option in player_options}
            try:
                index = player_ids.index(st.session_state.get(FILTER_PLAYER_KEY, player_ids[0]))
            except ValueError:
                index = default_index
            selected_player = st.selectbox(
                "Pelaaja",
                options=player_ids,
                index=index,
                format_func=lambda value: player_labels.get(value, "Tuntematon"),
                key=FILTER_PLAYER_KEY,
            )

        tags_str = st.text_input(
            "Tagit (pilkuilla eroteltu)",
            placeholder="esim. pressing, U21",
            key=FILTER_TAGS_KEY,
        )

        col_c, col_d = st.columns(2)
        with col_c:
            date_from = st.date_input("Alkaen", format="DD.MM.YYYY", key=FILTER_FROM_KEY)
        with col_d:
            date_to = st.date_input("Asti", format="DD.MM.YYYY", key=FILTER_TO_KEY)

        apply = st.form_submit_button("Käytä", use_container_width=True, type="primary")
        reset = st.form_submit_button("Tyhjennä", use_container_width=True)

    if apply:
        # Validate date range
        if date_from and date_to and date_from > date_to:
            set_toast("Päivämääräalue on virheellinen (Alkaen > Asti).", "warning")
        else:
            _apply_filters(q, selected_player or None, tags_str, date_from, date_to)
            _sync_query_params()
    elif reset:
        _reset_filters()
        _sync_query_params()


def render_notes_list(
    players: List[Dict[str, Any]],
    notes: List[Dict[str, Any]],
    total: int,
) -> None:
    st.session_state[k("last_notes")] = notes
    player_lookup = {player["id"]: player.get("name", "") for player in players}

    _render_pagination_controls(total)

    if not notes:
        st.info("Suodattimiin sopivia muistiinpanoja ei löytynyt.")
        return

    for note in notes:
        render_note_card(note, player_lookup)


def render_note_card(note: Dict[str, Any], player_lookup: Dict[str, str]) -> None:
    player_name = player_lookup.get(note.get("player_id"), "Tuntematon pelaaja")
    tags = note.get("tags") or []
    updated_at = _coerce_datetime(note.get("updated_at"))

    expanded: set[str] = st.session_state.get(k("expanded_notes"), set())
    note_id = str(note.get("id", "")) or ""

    with st.container():
        st.markdown(
            _note_card_html(
                title=note.get("title") or "(Ei otsikkoa)",
                content=note.get("content", ""),
                player_name=player_name,
                updated_label=format_ts(updated_at),
                tags=tags,
                expanded=(note_id in expanded),
            ),
            unsafe_allow_html=True,
        )
        action_cols = st.columns([1, 1, 1, 4])
        with action_cols[0]:
            toggle_label = "Piilota" if note_id in expanded else "Näytä koko"
            if st.button(toggle_label, key=f"{k('toggle_')}{note_id}", use_container_width=True):
                if note_id in expanded:
                    expanded.remove(note_id)
                else:
                    expanded.add(note_id)
                st.session_state[k("expanded_notes")] = expanded
        with action_cols[1]:
            if st.button("✏️ Muokkaa", key=f"{k('edit_')}{note_id}", use_container_width=True):
                st.session_state[k("modal_edit_id")] = note_id
        with action_cols[2]:
            if st.button("🗑️ Poista", key=f"{k('delete_')}{note_id}", use_container_width=True):
                st.session_state[k("modal_delete_id")] = note_id


def _note_card_html(
    *,
    title: str,
    content: str,
    player_name: str,
    updated_label: str,
    tags: Iterable[str],
    expanded: bool = False,
) -> str:
    shown = content if expanded else truncate_text(content, CARD_CONTENT_LIMIT)
    content_html = escape(shown).replace("\n", "<br>")
    tag_html = "".join(f'<span class="sl-tag">{escape(tag)}</span>' for tag in tags if tag)
    return f"""
    <div class="sl-note-card">
        <div class="sl-note-card__header">
            <h3 class="sl-note-card__title">{escape(title)}</h3>
            <span class="sl-note-card__subtitle">{escape(player_name)}</span>
        </div>
        <div class="sl-note-card__content">{content_html}</div>
        <div class="sl-note-card__meta">{escape(updated_label)}</div>
        <div class="sl-note-card__tags">{tag_html}</div>
    </div>
    """


def _render_pagination_controls(total: int) -> None:
    pagination: Pagination = st.session_state[k("pagination")]
    total_pages = max((total - 1) // pagination.page_size + 1, 1)
    pagination.page = min(max(pagination.page, 1), total_pages)

    col_size, col_prev, col_next, col_info = st.columns([1, 1, 1, 2])
    with col_size:
        try:
            size_index = PAGE_SIZE_OPTIONS.index(pagination.page_size)
        except ValueError:
            pagination.page_size = PAGE_SIZE_OPTIONS[1]
            size_index = PAGE_SIZE_OPTIONS.index(pagination.page_size)
        st.session_state[PAGE_SIZE_KEY] = pagination.page_size
        selected_size = st.selectbox(
            "Rivimäärä",
            options=PAGE_SIZE_OPTIONS,
            index=size_index,
            key=PAGE_SIZE_KEY,
        )
        if selected_size != pagination.page_size:
            pagination.page_size = selected_size
            pagination.page = 1
            _sync_query_params()
    with col_prev:
        if st.button("← Edellinen", disabled=pagination.page <= 1, use_container_width=True):
            pagination.page = max(pagination.page - 1, 1)
            _sync_query_params()
    with col_next:
        if st.button("Seuraava →", disabled=pagination.page >= total_pages, use_container_width=True):
            pagination.page = min(pagination.page + 1, total_pages)
            _sync_query_params()
    with col_info:
        st.write(f"Sivu {pagination.page} / {total_pages} (yhteensä {total} muistiinpanoa)")


# -------------------------------- Modals ---------------------------------- #

def modal_new(players: List[Dict[str, Any]]) -> None:
    if not st.session_state.get(k("modal_new")):
        return
    st.subheader("Uusi muistiinpano")
    st.caption("Täytä tiedot ja tallenna muistiinpano.")
    _note_form(players, on_submit=_create_note, submit_label="Luo", form_key_suffix="new")


def modal_edit(players: List[Dict[str, Any]]) -> None:
    note_id = st.session_state.get(k("modal_edit_id"))
    if not note_id:
        return
    note = _get_note_from_cache(str(note_id))
    if note is None:
        st.warning("Muistiinpanoa ei voitu ladata muokattavaksi.")
        if st.button("Sulje", key=f"{k('close_missing_note')}", use_container_width=True):
            st.session_state[k("modal_edit_id")] = None
        return
    st.subheader("Muokkaa muistiinpanoa")
    _note_form(
        players,
        on_submit=lambda data: _update_note(str(note_id), data),
        submit_label="Tallenna",
        initial=note,
        form_key_suffix=f"edit_{note_id}",
    )


def modal_delete() -> None:
    note_id = st.session_state.get(k("modal_delete_id"))
    if not note_id:
        return
    st.error("Oletko varma, että haluat poistaa muistiinpanon? Toimintoa ei voi perua.")
    cols = st.columns(2)
    with cols[0]:
        if st.button("Poista", type="primary", use_container_width=True, key=f"{k('confirm_delete')}"):
            if _delete_note(str(note_id)):
                st.session_state[k("modal_delete_id")] = None
                st.rerun()
    with cols[1]:
        if st.button("Peruuta", use_container_width=True, key=f"{k('cancel_delete')}"):
            st.session_state[k("modal_delete_id")] = None


def _note_form(
    players: List[Dict[str, Any]],
    *,
    on_submit,
    submit_label: str,
    initial: Optional[Dict[str, Any]] = None,
    form_key_suffix: str,
) -> None:
    initial = initial or {}
    player_options = [
        (player.get("id") or "", player.get("name") or "Nimetön pelaaja")
        for player in players
    ]
    if not player_options:
        st.info("Lisää pelaaja ennen muistiinpanojen luontia.")
        if st.button("Sulje", use_container_width=True):
            _close_modals()
        return
    initial_player_id = initial.get("player_id") or player_options[0][0]
    initial_index = next(
        (idx for idx, option in enumerate(player_options) if option[0] == initial_player_id),
        0,
    )

    form_key = f"{k('note_form_')}{form_key_suffix}"
    with st.form(form_key):
        title = st.text_input("Otsikko", value=initial.get("title") or "")
        content = st.text_area("Sisältö", value=initial.get("content") or "", height=200)
        selected_option = st.selectbox(
            "Pelaaja", options=player_options, index=initial_index, format_func=lambda opt: opt[1]
        )
        tags_str = st.text_input(
            "Tagit", value=_format_tags_csv(initial.get("tags") or []), placeholder="pressing, scouting"
        )
        submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
        cancel = st.form_submit_button("Peruuta", use_container_width=True)

    if submitted:
        # Validate payload (why: avoid backend errors with trivial issues)
        payload = {
            "title": title.strip(),
            "content": content.strip(),
            "player_id": selected_option[0] or None,
            "tags": _parse_tags(tags_str),
        }
        if not payload["player_id"]:
            set_toast("Pelaaja on pakollinen.", "warning")
            return
        if not payload["content"]:
            set_toast("Muistiinpanon sisältö on pakollinen.", "warning")
            return
        if on_submit(payload):
            st.rerun()
    elif cancel:
        _close_modals()


# ------------------------------ Filters/State ----------------------------- #

def _apply_filters(
    q: str,
    player_id: Optional[str],
    tags_csv: str,
    date_from: Optional[date],
    date_to: Optional[date],
) -> None:
    filters: Filters = st.session_state[k("filters")]
    filters.q = q.strip()
    filters.player_id = player_id
    filters.tags = _parse_tags(tags_csv)
    filters.date_from = _combine_date(date_from, time.min)
    filters.date_to = _combine_date(date_to, time.max)

    _queue_widget_state(
        {
            FILTER_Q_KEY: filters.q,
            FILTER_PLAYER_KEY: player_id or "",
            FILTER_TAGS_KEY: _format_tags_csv(filters.tags),
            FILTER_FROM_KEY: date_from,
            FILTER_TO_KEY: date_to,
        }
    )

    pagination: Pagination = st.session_state[k("pagination")]
    pagination.page = 1


def _reset_filters() -> None:
    st.session_state[k("filters")] = Filters()
    pagination: Pagination = st.session_state[k("pagination")]
    pagination.page = 1
    _queue_widget_state(
        {
            FILTER_Q_KEY: "",
            FILTER_PLAYER_KEY: "",
            FILTER_TAGS_KEY: "",
            FILTER_FROM_KEY: None,
            FILTER_TO_KEY: None,
        }
    )


def _combine_date(value: Optional[date], fallback_time: time) -> Optional[datetime]:
    if not value:
        return None
    tz = _local_timezone()
    return datetime.combine(value, fallback_time, tzinfo=tz)


def _format_tags_csv(tags: Iterable[str]) -> str:
    return ", ".join(tag for tag in tags if tag)


def _parse_tags(raw: str) -> List[str]:
    if not raw:
        return []
    items = [part.strip() for part in raw.replace(";", ",").split(",")]
    seen = set()
    result: List[str] = []
    for item in items:
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(item[:48])
    return result


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _get_note_from_cache(note_id: str) -> Optional[Dict[str, Any]]:
    notes = st.session_state.get(k("last_notes"), [])
    for note in notes:
        if str(note.get("id")) == note_id:
            return note
    try:
        return get_quick_note(note_id)
    except RuntimeError as exc:
        set_toast(str(exc), "error")
        return None


def _create_note(payload: Dict[str, Any]) -> bool:
    try:
        create_quick_note(payload)
    except (RuntimeError, ValueError) as exc:
        set_toast(str(exc), "error")
        return False
    set_toast("Muistiinpano luotu", "success")
    _close_modals()
    return True


def _update_note(note_id: str, payload: Dict[str, Any]) -> bool:
    try:
        update_quick_note(note_id, payload)
    except (RuntimeError, ValueError) as exc:
        set_toast(str(exc), "error")
        return False
    set_toast("Muistiinpano päivitetty", "success")
    _close_modals()
    return True


def _delete_note(note_id: str) -> bool:
    try:
        delete_quick_note(note_id)
    except (RuntimeError, ValueError) as exc:
        set_toast(str(exc), "error")
        return False
    set_toast("Muistiinpano poistettu", "success")
    return True


def _close_modals() -> None:
    st.session_state[k("modal_new")] = False
    st.session_state[k("modal_edit_id")] = None
    st.session_state[k("modal_delete_id")] = None


def fetch_notes() -> Tuple[List[Dict[str, Any]], int]:
    """Fetch filtered notes from the service with pagination."""
    filters: Filters = st.session_state[k("filters")]
    pagination: Pagination = st.session_state[k("pagination")]
    offset = (pagination.page - 1) * pagination.page_size
    try:
        return list_quick_notes(
            filters.q,
            filters.player_id,
            filters.tags,
            filters.date_from,
            filters.date_to,
            pagination.page_size,
            offset,
        )
    except RuntimeError as exc:
        set_toast(str(exc), "error")
        return [], 0


# --------------------------- URL Query Params ----------------------------- #

def _hydrate_from_query_params() -> None:
    """On first load, pull filters/pagination from ?q=&player=&tags=&from=&to=&page=&size=."""
    qp = st.query_params
    if st.session_state.get(k("qp_hydrated")):
        return
    st.session_state[k("qp_hydrated")] = True

    filters: Filters = st.session_state[k("filters")]
    pagination: Pagination = st.session_state[k("pagination")]

    # Filters
    if "q" in qp:
        filters.q = qp.get("q", "")
    if "player" in qp:
        filters.player_id = qp.get("player") or None
    if "tags" in qp:
        filters.tags = _parse_tags(qp.get("tags", ""))
    tz = _local_timezone()
    fmt = "%Y-%m-%d"
    if "from" in qp:
        try:
            d = datetime.strptime(qp.get("from", ""), fmt).date()
            filters.date_from = datetime.combine(d, time.min, tzinfo=tz)
        except ValueError:
            pass
    if "to" in qp:
        try:
            d = datetime.strptime(qp.get("to", ""), fmt).date()
            filters.date_to = datetime.combine(d, time.max, tzinfo=tz)
        except ValueError:
            pass

    # Pagination
    try:
        pagination.page = max(int(qp.get("page", 1)), 1)
    except (TypeError, ValueError):
        pagination.page = 1
    try:
        size = int(qp.get("size", pagination.page_size))
        pagination.page_size = size if size in PAGE_SIZE_OPTIONS else pagination.page_size
    except (TypeError, ValueError):
        pass


def _sync_query_params() -> None:
    """Push current filters/pagination to URL for shareable views."""
    filters: Filters = st.session_state[k("filters")]
    pagination: Pagination = st.session_state[k("pagination")]

    qp: Dict[str, str] = {}
    if filters.q:
        qp["q"] = filters.q
    if filters.player_id:
        qp["player"] = filters.player_id
    if filters.tags:
        qp["tags"] = _format_tags_csv(filters.tags)
    if filters.date_from:
        qp["from"] = filters.date_from.date().isoformat()
    if filters.date_to:
        qp["to"] = filters.date_to.date().isoformat()

    qp["page"] = str(max(pagination.page, 1))
    qp["size"] = str(pagination.page_size)

    st.query_params.clear()
    st.query_params.update(qp)


# ------------------------------- Export ----------------------------------- #

def _notes_to_csv_bytes(notes: List[Dict[str, Any]]) -> bytes:
    """Serialize notes to CSV (UTF-8)."""
    fieldnames = ["id", "title", "content", "player_id", "tags", "updated_at", "created_at"]
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for n in notes:
        row = {
            "id": n.get("id", ""),
            "title": n.get("title", ""),
            "content": n.get("content", ""),
            "player_id": n.get("player_id", ""),
            "tags": _format_tags_csv(n.get("tags") or []),
            "updated_at": n.get("updated_at", ""),
            "created_at": n.get("created_at", ""),
        }
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


# --------------------------------- Page ----------------------------------- #

def show_quick_notes_page() -> None:
    st.set_page_config(page_title="Quick Notes", page_icon="🗒️", layout="wide")
    load_css()
    init_state()
    pop_toast()

    try:
        players = list_players()
    except RuntimeError as exc:
        set_toast(str(exc), "error")
        players = []

    try:
        counts = get_player_note_counts()
    except RuntimeError as exc:
        set_toast(str(exc), "error")
        counts = {}

    render_header(players, counts)
    render_actions(players)
    render_filters(players)
    notes, total = fetch_notes()
    render_notes_list(players, notes, total)
    modal_new(players)
    modal_edit(players)
    modal_delete()


if __name__ == "__main__":  # pragma: no cover - manual run helper
    show_quick_notes_page()
