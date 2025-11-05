from __future__ import annotations

import contextlib
import re
from pathlib import Path
from typing import Any, Optional, Union
import uuid

import streamlit as st


_CSS_FLAG_KEY = "_sl_buttons_css_loaded"
_ALLOWED_VARIANTS = {"primary", "secondary", "outline", "ghost", "success", "danger"}
_ALLOWED_SIZES = {"sm", "md", "lg"}


def load_buttons_css(path: Optional[Union[str, Path]] = None) -> None:
    """Inject ScoutLens button CSS once per session."""
    if st.session_state.get(_CSS_FLAG_KEY):
        return

    css_path = Path(path) if path is not None else Path(__file__).with_name("buttons.css")
    with contextlib.suppress(OSError):
        css_text = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)
        st.session_state[_CSS_FLAG_KEY] = True


def _ensure_css_loaded() -> None:
    load_buttons_css()


def _wrap_open(container: Any, variant: str, size: str) -> None:
    container.markdown(
        f'<div class="sl-btn sl-{variant} sl-{size}">',
        unsafe_allow_html=True,
    )


def _wrap_close(container: Any) -> None:
    container.markdown("</div>", unsafe_allow_html=True)


def _label_with_icon(label: str, icon: Optional[str]) -> str:
    return f"{icon}  {label}" if icon else label


def _normalize_variant(variant: str) -> str:
    return variant if variant in _ALLOWED_VARIANTS else "primary"


def _normalize_size(size: str) -> str:
    return size if size in _ALLOWED_SIZES else "md"


def _resolve_state_key(label: str, key: Optional[str]) -> str:
    base = str(key) if key is not None else label
    slug = re.sub(r"[^0-9a-zA-Z]+", "-", base).strip("-").lower() or "button"
    hashed = uuid.uuid5(uuid.NAMESPACE_URL, base).hex[:8]
    return f"_sl-{slug}-{hashed}"


def _safe_rerun() -> None:
    rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun_fn:
        rerun_fn()


def sl_confirm_dialog(
    message: str = "Are you sure?",
    *,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
    key: Optional[str] = None,
    open_key: Optional[str] = None,
    result_key: Optional[str] = None,
) -> None:
    """Render a confirmation dialog when ``st.dialog`` is available, otherwise inline."""
    _ensure_css_loaded()

    base_key = key or f"_sl_confirm_{uuid.uuid4().hex}"
    open_state_key = open_key or f"{base_key}__open"
    result_state_key = result_key or f"{base_key}__result"

    if not st.session_state.get(open_state_key):
        return

    def _handle_confirm(value: bool) -> None:
        st.session_state[result_state_key] = value
        st.session_state[open_state_key] = False
        _safe_rerun()

    if hasattr(st, "dialog"):
        try:
            dialog_decorator = st.dialog("Confirm action", key=f"{base_key}__dialog")
        except TypeError:  # older Streamlit versions without key param support
            dialog_decorator = st.dialog("Confirm action")

        @dialog_decorator
        def _dialog_content() -> None:
            st.write(message)
            col_ok, col_cancel = st.columns(2)
            _wrap_open(col_ok, "danger", "md")
            confirmed = col_ok.button(confirm_text, key=f"{base_key}__ok", use_container_width=True)
            _wrap_close(col_ok)
            _wrap_open(col_cancel, "secondary", "md")
            cancelled = col_cancel.button(cancel_text, key=f"{base_key}__cancel", use_container_width=True)
            _wrap_close(col_cancel)
            if confirmed:
                _handle_confirm(True)
            if cancelled:
                _handle_confirm(False)

        _dialog_content()
        return

    placeholder = st.empty()
    with placeholder.container():
        st.write(message)
        col_ok, col_cancel = st.columns(2)
        _wrap_open(col_ok, "danger", "md")
        confirmed = col_ok.button(confirm_text, key=f"{base_key}__ok")
        _wrap_close(col_ok)
        _wrap_open(col_cancel, "secondary", "md")
        cancelled = col_cancel.button(cancel_text, key=f"{base_key}__cancel")
        _wrap_close(col_cancel)

    if confirmed:
        placeholder.empty()
        _handle_confirm(True)
    if cancelled:
        placeholder.empty()
        _handle_confirm(False)


def sl_button(
    label: str,
    *,
    variant: str = "primary",
    size: str = "md",
    icon: Optional[str] = None,
    disabled: bool = False,
    key: Optional[str] = None,
    help: Optional[str] = None,
    sidebar: bool = False,
    use_container_width: bool = True,
    confirm: bool = False,
    confirm_message: Optional[str] = None,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
) -> bool:
    """Render a ScoutLens-styled button."""
    _ensure_css_loaded()

    variant = _normalize_variant(variant)
    size = _normalize_size(size)
    container = st.sidebar if sidebar else st
    text = _label_with_icon(label, icon)
    base_state_key = _resolve_state_key(label, key)
    confirm_open_key = f"{base_state_key}__confirm_open"
    confirm_result_key = f"{base_state_key}__confirm_result"

    if confirm:
        result = st.session_state.pop(confirm_result_key, None)
        if result is not None:
            return bool(result)

    _wrap_open(container, variant, size)
    clicked = container.button(
        text,
        key=key,
        help=help,
        disabled=disabled,
        use_container_width=use_container_width,
    )
    _wrap_close(container)

    if disabled:
        return False

    if confirm:
        if clicked:
            st.session_state[confirm_open_key] = True
        if st.session_state.get(confirm_open_key):
            message_text = confirm_message or f"Confirm \u201c{label}\u201d?"
            sl_confirm_dialog(
                message_text,
                confirm_text=confirm_text,
                cancel_text=cancel_text,
                key=base_state_key,
                open_key=confirm_open_key,
                result_key=confirm_result_key,
            )
        return False

    return clicked


def sl_submit_button(
    label: str = "Submit",
    *,
    variant: str = "primary",
    size: str = "md",
    icon: Optional[str] = None,
    disabled: bool = False,
    help: Optional[str] = None,
    use_container_width: bool = True,
    confirm: bool = False,
    confirm_message: Optional[str] = None,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
    key: Optional[str] = None,
) -> bool:
    """Render a ScoutLens styled submit button for use inside ``st.form``."""
    _ensure_css_loaded()

    variant = _normalize_variant(variant)
    size = _normalize_size(size)
    text = _label_with_icon(label, icon)
    base_state_key = _resolve_state_key(label, key)
    confirm_open_key = f"{base_state_key}__confirm_open"
    confirm_result_key = f"{base_state_key}__confirm_result"

    if confirm:
        result = st.session_state.pop(confirm_result_key, None)
        if result is not None:
            return bool(result)

    _wrap_open(st, variant, size)
    submitted = st.form_submit_button(
        text,
        disabled=disabled,
        help=help,
        use_container_width=use_container_width,
        type="primary",
        key=key,
    )
    _wrap_close(st)

    if disabled:
        return False

    if confirm:
        if submitted:
            st.session_state[confirm_open_key] = True
        if st.session_state.get(confirm_open_key):
            message_text = confirm_message or f"Confirm \u201c{label}\u201d?"
            sl_confirm_dialog(
                message_text,
                confirm_text=confirm_text,
                cancel_text=cancel_text,
                key=base_state_key,
                open_key=confirm_open_key,
                result_key=confirm_result_key,
            )
        return False

    return submitted


def sl_download_button(
    label: str,
    data: Union[str, bytes, Any],
    *,
    file_name: Optional[str] = None,
    mime: Optional[str] = None,
    variant: str = "secondary",
    size: str = "md",
    icon: Optional[str] = None,
    disabled: bool = False,
    help: Optional[str] = None,
    key: Optional[str] = None,
    sidebar: bool = False,
    use_container_width: bool = True,
) -> bool:
    """Render a ScoutLens styled download button."""
    _ensure_css_loaded()

    variant = _normalize_variant(variant)
    size = _normalize_size(size)
    container = st.sidebar if sidebar else st
    text = _label_with_icon(label, icon)

    _wrap_open(container, variant, size)
    clicked = container.download_button(
        label=text,
        data=data,
        file_name=file_name,
        mime=mime,
        disabled=disabled,
        help=help,
        key=key,
        use_container_width=use_container_width,
    )
    _wrap_close(container)

    return bool(clicked) and not disabled


def sl_link_button(
    label: str,
    url: str,
    *,
    variant: str = "outline",
    size: str = "md",
    icon: Optional[str] = None,
    disabled: bool = False,
    help: Optional[str] = None,
    key: Optional[str] = None,
    sidebar: bool = False,
    use_container_width: bool = True,
) -> bool:
    """Render a ScoutLens styled link button."""
    _ensure_css_loaded()

    variant = _normalize_variant(variant)
    size = _normalize_size(size)
    container = st.sidebar if sidebar else st
    text = _label_with_icon(label, icon)

    _wrap_open(container, variant, size)
    clicked = False
    if hasattr(st, "link_button"):
        clicked = container.link_button(
            text,
            url,
            help=help,
            disabled=disabled,
            key=key,
            use_container_width=use_container_width,
        )
    else:
        attrs = "aria-disabled=\"true\"" if disabled else ""
        style = "pointer-events: none; opacity: 0.55;" if disabled else ""
        href = url if not disabled else "#"
        container.markdown(
            f'<a class="sl-faux-link" href="{href}" target="_blank" rel="noopener" style="{style}" {attrs}>{text}</a>',
            unsafe_allow_html=True,
        )
    _wrap_close(container)

    return bool(clicked) and not disabled
