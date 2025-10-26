from __future__ import annotations

import re
from contextlib import nullcontext
from typing import Mapping, Sequence

import streamlit as st


def render_sidebar_nav(
    options: Sequence[str],
    state_key: str = "nav_page",
    *,
    display_map: Mapping[str, str] | None = None,
    icon_map: Mapping[str, str] | None = None,
    heading: str | None = "Navigation",
    container=None,
    rerun_on_click: bool = True,
) -> str:
    """Render button-based sidebar navigation with optional label/icon maps."""
    if not options:
        raise ValueError("render_sidebar_nav requires at least one option")

    if state_key not in st.session_state:
        st.session_state[state_key] = options[0]

    selected = st.session_state[state_key]
    target = container if container is not None else st.sidebar
    ctx = target if hasattr(target, "__enter__") else nullcontext()

    with ctx:
        if heading:
            st.subheader(heading)
        st.markdown('<div class="sl-nav">', unsafe_allow_html=True)

        for name in options:
            label = (display_map.get(name) if display_map else name) or name
            icon = (icon_map.get(name) if icon_map else "")
            if icon and icon.startswith("fa-"):
                button_label = label
            elif icon:
                button_label = f"{icon}  {label}"
            else:
                button_label = label

            key_suffix = re.sub(r"[^0-9a-zA-Z_-]+", "_", name).strip("_") or "item"
            key = f"navbtn_{state_key}_{key_suffix}"
            is_active = name == selected

            clicked = st.button(
                button_label,
                key=key,
                use_container_width=True,
                disabled=is_active,
            )
            if clicked and not is_active:
                st.session_state[state_key] = name
                if rerun_on_click:
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    return st.session_state[state_key]


__all__ = ["render_sidebar_nav"]
