"""Streamlit page implementation for Quick Notes.

The UI is intentionally modular so that the view logic stays approachable and
any data related concerns are handled in ``app.services.quick_notes``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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

CSS_PATH = Path(".streamlit") / "component.css"
PAGE_KEY_PREFIX = "qn_"
TOAST_TYPES = {"success": "✅", "warning": "⚠️", "error": "❌"}
PAGE_SIZE_OPTIONS = [10, 20, 50, 100]
CARD_CONTENT_LIMIT = 500

FILTER_Q_KEY = PAGE_KEY_PREFIX + "filter_q"
FILTER_PLAYER_KEY = PAGE_KEY_PREFIX + "filter_player"
FILTER_TAGS_KEY = PAGE_KEY_PREFIX + "filter_tags"
FILTER_FROM_KEY = PAGE_KEY_PREFIX + "filter_date_from"
FILTER_TO_KEY = PAGE_KEY_PREFIX + "filter_date_to"
PAGE_SIZE_KEY = PAGE_KEY_PREFIX + "page_size"


@dataclass
class Filters:
    q: str = ""
    player_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


@dataclass
class Pagination:
    page: int = 1
    page_size: int = 20


def load_css() -> None:
    flag = PAGE_KEY_PREFIX + "css_loaded"
    if st.session_state.get(flag):
        return
    if CSS_PATH.exists():
        css = CSS_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        st.session_state[flag] = True
    else:
        st.info("Quick Notes styles missing (.streamlit/component.css)")


def init_state() -> None:
    ss = st.session_state
    ss.setdefault(PAGE_KEY_PREFIX + "filters", Filters())
    ss.setdefault(PAGE_KEY_PREFIX + "pagination", Pagination())
    ss.setdefault(PAGE_KEY_PREFIX + "modal_new", False)
    ss.setdefault(PAGE_KEY_PREFIX + "modal_edit_id", None)
    ss.setdefault(PAGE_KEY_PREFIX + "modal_delete_id", None)
    ss.setdefault(PAGE_KEY_PREFIX + "toast", {"type": None, "msg": ""})
    ss.setdefault(PAGE_KEY_PREFIX + "last_notes", [])
    filters: Filters = ss[PAGE_KEY_PREFIX + "filters"]
    ss.setdefault(FILTER_Q_KEY, filters.q)
    ss.setdefault(FILTER_PLAYER_KEY, filters.player_id or "")
    ss.setdefault(FILTER_TAGS_KEY, _format_tags_csv(filters.tags))
    ss.setdefault(FILTER_FROM_KEY, filters.date_from.date() if filters.date_from else None)
    ss.setdefault(FILTER_TO_KEY, filters.date_to.date() if filters.date_to else None)
    pagination: Pagination = ss[PAGE_KEY_PREFIX + "pagination"]
    ss.setdefault(PAGE_SIZE_KEY, pagination.page_size)


def set_toast(message: str, kind: str = "success") -> None:
    st.session_state[PAGE_KEY_PREFIX + "toast"] = {"type": kind, "msg": message}


def pop_toast() -> None:
    toast = st.session_state.get(PAGE_KEY_PREFIX + "toast", {})
    if toast.get("msg") and toast.get("type"):
        icon = TOAST_TYPES.get(toast["type"], "ℹ️")
        st.toast(toast["msg"], icon=icon)
    st.session_state[PAGE_KEY_PREFIX + "toast"] = {"type": None, "msg": ""}


def _local_timezone() -> ZoneInfo:
    tz_name = st.session_state.get("user_timezone")
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            set_toast(f"Tuntematon aikavyöhyke: {tz_name}", "warning")
    try:
        return ZoneInfo(str(datetime.now().astimezone().tzinfo))
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def format_ts(value: Optional[datetime]) -> str:
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


def render_filters(players: List[Dict[str, Any]]) -> None:
    filters: Filters = st.session_state[PAGE_KEY_PREFIX + "filters"]
    player_options = [("", "Kaikki")] + [
        (player.get("id") or "", player.get("name") or "Nimetön pelaaja")
        for player in players
    ]
    default_index = next(
        (idx for idx, option in enumerate(player_options) if option[0] == (filters.player_id or "")),
        0,
    )

    with st.form(PAGE_KEY_PREFIX + "filters_form"):
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
            date_from = st.date_input(
                "Alkaen",
                format="DD.MM.YYYY",
                key=FILTER_FROM_KEY,
            )
        with col_d:
            date_to = st.date_input(
                "Asti",
                format="DD.MM.YYYY",
                key=FILTER_TO_KEY,
            )

        apply = st.form_submit_button("Käytä", use_container_width=True, type="primary")
        reset = st.form_submit_button("Tyhjennä", use_container_width=True)

    if apply:
        _apply_filters(q, selected_player or None, tags_str, date_from, date_to)
    elif reset:
        _reset_filters()


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
            st.session_state[PAGE_KEY_PREFIX + "modal_new"] = True
    with cols[1]:
        if st.button("🔄 Päivitä", use_container_width=True):
            st.rerun()


def render_notes_list(
    players: List[Dict[str, Any]],
    notes: List[Dict[str, Any]],
    total: int,
) -> None:
    st.session_state[PAGE_KEY_PREFIX + "last_notes"] = notes
    player_lookup = {player["id"]: player.get("name", "") for player in players}

    pagination: Pagination = st.session_state[PAGE_KEY_PREFIX + "pagination"]
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

    with st.container():
        st.markdown(
            _note_card_html(
                title=note.get("title") or "(Ei otsikkoa)",
                content=note.get("content", ""),
                player_name=player_name,
                updated_label=format_ts(updated_at),
                tags=tags,
            ),
            unsafe_allow_html=True,
        )
        action_cols = st.columns([1, 1, 5])
        with action_cols[0]:
            if st.button(
                "✏️ Muokkaa",
                key=f"{PAGE_KEY_PREFIX}edit_{note['id']}",
                use_container_width=True,
            ):
                st.session_state[PAGE_KEY_PREFIX + "modal_edit_id"] = note["id"]
        with action_cols[1]:
            if st.button(
                "🗑️ Poista",
                key=f"{PAGE_KEY_PREFIX}delete_{note['id']}",
                use_container_width=True,
            ):
                st.session_state[PAGE_KEY_PREFIX + "modal_delete_id"] = note["id"]


def _note_card_html(
    *,
    title: str,
    content: str,
    player_name: str,
    updated_label: str,
    tags: Iterable[str],
) -> str:
    truncated = truncate_text(content, CARD_CONTENT_LIMIT)
    content_html = escape(truncated).replace("\n", "<br>")
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
    pagination: Pagination = st.session_state[PAGE_KEY_PREFIX + "pagination"]
    total_pages = max((total - 1) // pagination.page_size + 1, 1)
    pagination.page = min(pagination.page, total_pages)

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
    with col_prev:
        if st.button("← Edellinen", disabled=pagination.page <= 1, use_container_width=True):
            pagination.page = max(pagination.page - 1, 1)
    with col_next:
        if st.button(
            "Seuraava →",
            disabled=pagination.page >= total_pages,
            use_container_width=True,
        ):
            pagination.page = min(pagination.page + 1, total_pages)
    with col_info:
        st.write(f"Sivu {pagination.page} / {total_pages} (yhteensä {total} muistiinpanoa)")


def modal_new(players: List[Dict[str, Any]]) -> None:
    if not st.session_state.get(PAGE_KEY_PREFIX + "modal_new"):
        return
    st.subheader("Uusi muistiinpano")
    st.caption("Täytä tiedot ja tallenna muistiinpano.")
    _note_form(
        players,
        on_submit=_create_note,
        submit_label="Luo",
        form_key_suffix="new",
    )


def modal_edit(players: List[Dict[str, Any]]) -> None:
    note_id = st.session_state.get(PAGE_KEY_PREFIX + "modal_edit_id")
    if not note_id:
        return
    note = _get_note_from_cache(note_id)
    if note is None:
        st.warning("Muistiinpanoa ei voitu ladata muokattavaksi.")
        if st.button(
            "Sulje",
            key=f"{PAGE_KEY_PREFIX}close_missing_note",
            use_container_width=True,
        ):
            st.session_state[PAGE_KEY_PREFIX + "modal_edit_id"] = None
        return
    st.subheader("Muokkaa muistiinpanoa")
    _note_form(
        players,
        on_submit=lambda data: _update_note(note_id, data),
        submit_label="Tallenna",
        initial=note,
        form_key_suffix=f"edit_{note_id}",
    )


def modal_delete() -> None:
    note_id = st.session_state.get(PAGE_KEY_PREFIX + "modal_delete_id")
    if not note_id:
        return
    st.error("Oletko varma, että haluat poistaa muistiinpanon? Toimintoa ei voi perua.")
    cols = st.columns(2)
    with cols[0]:
        if st.button(
            "Poista",
            type="primary",
            use_container_width=True,
            key=f"{PAGE_KEY_PREFIX}confirm_delete",
        ):
            if _delete_note(note_id):
                st.session_state[PAGE_KEY_PREFIX + "modal_delete_id"] = None
                st.rerun()
    with cols[1]:
        if st.button(
            "Peruuta",
            use_container_width=True,
            key=f"{PAGE_KEY_PREFIX}cancel_delete",
        ):
            st.session_state[PAGE_KEY_PREFIX + "modal_delete_id"] = None


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

    form_key = f"{PAGE_KEY_PREFIX}note_form_{form_key_suffix}"
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
        payload = {
            "title": title,
            "content": content,
            "player_id": selected_option[0] or None,
            "tags": _parse_tags(tags_str),
        }
        if on_submit(payload):
            st.rerun()
    elif cancel:
        _close_modals()


def _apply_filters(
    q: str,
    player_id: Optional[str],
    tags_csv: str,
    date_from: Optional[date],
    date_to: Optional[date],
) -> None:
    filters: Filters = st.session_state[PAGE_KEY_PREFIX + "filters"]
    filters.q = q.strip()
    filters.player_id = player_id
    filters.tags = _parse_tags(tags_csv)
    filters.date_from = _combine_date(date_from, time.min)
    filters.date_to = _combine_date(date_to, time.max)

    st.session_state[FILTER_Q_KEY] = filters.q
    st.session_state[FILTER_PLAYER_KEY] = player_id or ""
    st.session_state[FILTER_TAGS_KEY] = _format_tags_csv(filters.tags)
    st.session_state[FILTER_FROM_KEY] = date_from
    st.session_state[FILTER_TO_KEY] = date_to

    pagination: Pagination = st.session_state[PAGE_KEY_PREFIX + "pagination"]
    pagination.page = 1


def _reset_filters() -> None:
    st.session_state[PAGE_KEY_PREFIX + "filters"] = Filters()
    pagination: Pagination = st.session_state[PAGE_KEY_PREFIX + "pagination"]
    pagination.page = 1
    st.session_state[FILTER_Q_KEY] = ""
    st.session_state[FILTER_PLAYER_KEY] = ""
    st.session_state[FILTER_TAGS_KEY] = ""
    st.session_state[FILTER_FROM_KEY] = None
    st.session_state[FILTER_TO_KEY] = None


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
    result = []
    for item in items:
        if not item:
            continue
        key = item.lower()
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
    notes = st.session_state.get(PAGE_KEY_PREFIX + "last_notes", [])
    for note in notes:
        if note.get("id") == note_id:
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
    st.session_state[PAGE_KEY_PREFIX + "modal_new"] = False
    st.session_state[PAGE_KEY_PREFIX + "modal_edit_id"] = None
    st.session_state[PAGE_KEY_PREFIX + "modal_delete_id"] = None


def fetch_notes() -> Tuple[List[Dict[str, Any]], int]:
    filters: Filters = st.session_state[PAGE_KEY_PREFIX + "filters"]
    pagination: Pagination = st.session_state[PAGE_KEY_PREFIX + "pagination"]
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
