from __future__ import annotations

import json
import re
from contextlib import nullcontext
from html import escape
from typing import Mapping, Sequence

import streamlit as st


_NAV_ICON_SCRIPT = r"""
<script id="sl-nav-iconify">
(function(){
  const w = window;
  function getDoc(){
    try {
      return (w.parent && w.parent.document) ? w.parent.document : document;
    } catch (err) {
      return document;
    }
  }
  function getNavRoot(doc){
    if (!doc) return null;
    return doc.querySelector('#sl-sidebar-nav') || doc.querySelector('section[data-testid="stSidebar"] .sl-nav');
  }
  function ensureIconData(){
    const data = w.__SL_NAV_ICON_DATA;
    if (!data || typeof data !== 'object') return {};
    return data;
  }
  function createIconSpan(doc, html){
    const span = doc.createElement('span');
    span.className = 'sb-nav-icon';
    span.setAttribute('aria-hidden', 'true');
    span.innerHTML = html;
    return span;
  }
  function createLabelSpan(doc, label){
    const span = doc.createElement('span');
    span.className = 'sb-nav-label';
    span.textContent = label;
    return span;
  }
  function apply(doc){
    const navRoot = getNavRoot(doc);
    if (!navRoot) return;
    const iconData = ensureIconData();
    const buttons = navRoot.querySelectorAll('.stButton > button');
    buttons.forEach((btn) => {
      if (!btn || btn.dataset.slNavIconReady === '1') {
        return;
      }
      const raw = btn.textContent || '';
      const labelText = raw.replace(/^\s+/, '').replace(/\s+$/, '');
      const iconHtml = iconData[labelText];
      if (iconHtml) {
        btn.innerHTML = '';
        btn.dataset.slNavIconReady = '1';
        btn.setAttribute('data-sl-has-icon', '1');
        if (labelText) {
          btn.setAttribute('aria-label', labelText);
        }
        const iconSpan = createIconSpan(doc, iconHtml);
        const labelSpan = createLabelSpan(doc, labelText);
        btn.appendChild(iconSpan);
        btn.appendChild(labelSpan);
        if (w.lucide && typeof w.lucide.createIcons === 'function') {
          try { w.lucide.createIcons({ root: iconSpan }); } catch (err) { /* noop */ }
        }
        return;
      }
      const glyphs = Array.from(raw.replace(/^\s+/, ''));
      if (!glyphs.length) {
        btn.dataset.slNavIconReady = '1';
        return;
      }
      const iconChar = glyphs[0];
      const code = iconChar.codePointAt(0) || 0;
      if (code < 0xf000 || code > 0xfaff) {
        btn.dataset.slNavIconReady = '1';
        return;
      }
      const remainder = raw.substring(iconChar.length).replace(/^\s+/, '');
      const label = remainder || raw.substring(iconChar.length).replace(/^\s+/, '');
      btn.textContent = '';
      btn.dataset.slNavIconReady = '1';
      btn.setAttribute('data-sl-has-icon', '1');
      if (label) {
        btn.setAttribute('aria-label', label);
      }
      const iconSpan = createIconSpan(doc, iconChar);
      iconSpan.textContent = iconChar;
      const labelSpan = createLabelSpan(doc, label);
      btn.appendChild(iconSpan);
      btn.appendChild(labelSpan);
    });
  }
  function ensureObserver(){
    const doc = getDoc();
    if (!doc) return;
    const navRoot = getNavRoot(doc) || doc.querySelector('section[data-testid="stSidebar"]');
    if (!navRoot) {
      setTimeout(ensureObserver, 120);
      return;
    }
    apply(doc);
    if (w.__slNavIconObserver) {
      return;
    }
    const observer = new MutationObserver(() => apply(doc));
    observer.observe(navRoot, { childList: true, subtree: true });
    w.__slNavIconObserver = observer;
  }
  if (w.__slNavIconRefresh) {
    try { w.__slNavIconRefresh(); } catch (err) { /* noop */ }
    return;
  }
  w.__slNavIconRefresh = function(){
    const doc = getDoc();
    if (!doc) return;
    apply(doc);
  };
  ensureObserver();
})();
</script>
"""


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

    aria_label = heading or "Sidebar navigation"

    icon_payload: dict[str, str] = {}

    with ctx:
        if heading:
            st.subheader(heading)
        st.markdown(
            f"<nav id=\"sl-sidebar-nav\" class=\"sl-nav\" role=\"navigation\" aria-label=\"{escape(aria_label)}\">",
            unsafe_allow_html=True,
        )

        for name in options:
            label = (display_map.get(name) if display_map else name) or name
            icon = (icon_map.get(name) if icon_map else "")
            if icon and not icon.startswith("fa-"):
                icon_payload[label] = icon

            if icon and icon.startswith("fa-"):
                button_label = label
            elif icon and "<" in icon:
                button_label = label
            elif icon:
                button_label = f"{icon}\u2009{label}"
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

        st.markdown("</nav>", unsafe_allow_html=True)

        data_json = json.dumps(icon_payload).replace("</", "<\\/")
        st.markdown(
            f"<script id='sl-nav-icon-data'>window.__SL_NAV_ICON_DATA = {data_json};</script>",
            unsafe_allow_html=True,
        )
        st.markdown(_NAV_ICON_SCRIPT, unsafe_allow_html=True)

    return st.session_state[state_key]


__all__ = ["render_sidebar_nav"]
