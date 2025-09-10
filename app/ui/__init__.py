"""UI helpers shared across ScoutLens pages."""

from __future__ import annotations

import streamlit as st


def bootstrap_sidebar_auto_collapse() -> None:
    """If session flag is set, click the header hamburger to close sidebar once."""
    if st.session_state.get("_collapse_sidebar"):
        st.session_state._collapse_sidebar = False
        st.markdown(
            """
            <script>
            // Use multiple selectors because Streamlit header DOM changes occasionally
            const selectors = [
              'button[aria-label="Main menu"]',
              'button[title="Main menu"]',
              'button[kind="headerNoPadding"]',
              'button[data-testid="baseButton-headerNoPadding"]'
            ];
            function findToggleBtn() {
              const root = window.parent?.document || document;
              for (const sel of selectors) {
                const btn = root.querySelector(sel);
                if (btn) return btn;
              }
              const header = (window.parent?.document || document).querySelector('header');
              if (header) return header.querySelector('button');
              return null;
            }
            function tryClose(attempt=0) {
              const btn = findToggleBtn();
              if (btn) { btn.click(); }
              else if (attempt < 40) { setTimeout(() => tryClose(attempt + 1), 50); }
            }
            tryClose();
            </script>
            """,
            unsafe_allow_html=True,
        )

