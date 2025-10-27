"""Font/icon pack loader utilities for ScoutLens UI."""
from __future__ import annotations

import streamlit as st

_FONT_AWESOME_HREF = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css"


def ensure_fontawesome() -> None:
    """Ensure Font Awesome stylesheet is available in the active document."""
    script = (
        """
<script id="sl-fontawesome-loader">
(function() {
  const w = window;
  const href = "__HREF__";
  const id = "sl-fontawesome";

  function getDoc() {
    try {
      if (w.parent && w.parent.document) return w.parent.document;
    } catch (err) {
      /* ignore */
    }
    return document;
  }

  const doc = getDoc();
  if (!doc || !doc.head) return;
  if (doc.getElementById(id)) return;

  const link = doc.createElement('link');
  link.id = id;
  link.rel = 'stylesheet';
  link.href = href;
  link.referrerPolicy = 'no-referrer';
  doc.head.appendChild(link);
})();
</script>
        """.strip()
    ).replace("__HREF__", _FONT_AWESOME_HREF)

    st.markdown(script, unsafe_allow_html=True)


__all__ = ["ensure_fontawesome"]
