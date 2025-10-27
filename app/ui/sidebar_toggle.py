from __future__ import annotations

import streamlit as st


def render_sidebar_toggle() -> None:
    """Inject a high-visibility sidebar toggle (FAB) and enhance native toggle."""
    st.markdown(
        """
        <style>
        /* --- Enhance native collapsed control if present --- */
        [data-testid="collapsedControl"] { opacity: 1 !important; }
        [data-testid="collapsedControl"] button,
        button[aria-label*="sidebar" i],
        [data-testid="stSidebarCollapseButton"] {
          width: 40px; height: 40px;
          border-radius: 12px;
          backdrop-filter: blur(6px);
          -webkit-backdrop-filter: blur(6px);
          background: rgba(255,255,255,0.14);
          border: 1px solid rgba(255,255,255,0.28);
          color: #fff !important;
          box-shadow: 0 2px 10px rgba(0,0,0,0.35);
        }

        /* --- Our floating FAB --- */
        #sl-sidebar-fab {
          position: fixed;
          left: calc(env(safe-area-inset-left, 0px) + 10px);
          top:  calc(env(safe-area-inset-top, 0px) + 10px);
          width: 48px; height: 48px;
          border: none; border-radius: 14px;
          background: rgba(255,255,255,0.16);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          color: #fff; font-size: 24px; line-height: 48px;
          text-align: center; cursor: pointer;
          box-shadow: 0 6px 20px rgba(0,0,0,0.45);
          z-index: 2147483647;
          transition: transform .08s ease, background .15s ease;
        }
        #sl-sidebar-fab:active { transform: scale(0.96); }
        #sl-sidebar-fab:focus { outline: 2px solid rgba(255,255,255,0.7); outline-offset: 2px; }

        /* Gentle attention pulse on first loads */
        @keyframes sl-pulse {
          0% { box-shadow: 0 0 0 0 rgba(255,255,255,.45); }
          70%{ box-shadow: 0 0 0 14px rgba(255,255,255,0); }
          100%{ box-shadow: 0 0 0 0 rgba(255,255,255,0); }
        }
        .sl-pulse-once { animation: sl-pulse 1.6s ease-out 1; }

        /* Mobile: make it a bit larger */
        @media (max-width: 768px) {
          #sl-sidebar-fab { width: 54px; height: 54px; font-size: 26px; line-height: 54px; }
          [data-testid="collapsedControl"] button,
          button[aria-label*="sidebar" i],
          [data-testid="stSidebarCollapseButton"] { width: 44px; height: 44px; }
        }

        @media (prefers-color-scheme: light) {
          #sl-sidebar-fab { background: rgba(0,0,0,0.12); color: #000; }
          [data-testid="collapsedControl"] button,
          button[aria-label*="sidebar" i],
          [data-testid="stSidebarCollapseButton"] {
            background: rgba(0,0,0,0.08);
            color: #000 !important;
            border: 1px solid rgba(0,0,0,0.16);
          }
        }
        </style>

        <script id="sl-visible-sidebar-toggle">
        (function(){
          const w = window;
          if (w.__sl_visible_sidebar_toggle_init) return;
          w.__sl_visible_sidebar_toggle_init = true;

          function getDoc(){
            try { return (w.parent && w.parent.document) ? w.parent.document : w.document; }
            catch(e){ return w.document; }
          }
          const doc = getDoc();

          function findNativeToggle(){
            return (
              doc.querySelector('[data-testid="collapsedControl"] button') ||
              doc.querySelector('[data-testid="stSidebarCollapseButton"]') ||
              Array.from(doc.querySelectorAll('button[aria-label]'))
                   .find(b => /sidebar/i.test(b.getAttribute('aria-label')||''))
            );
          }

          function ensureFab(){
            if (doc.getElementById('sl-sidebar-fab')) return;
            const fab = doc.createElement('button');
            fab.id = 'sl-sidebar-fab';
            fab.type = 'button';
            fab.className = 'sl-pulse-once';
            fab.setAttribute('title', 'Toggle sidebar');
            fab.textContent = '☰';
            fab.addEventListener('click', () => {
              const nativeBtn = findNativeToggle();
              if (nativeBtn) nativeBtn.click();
            });
            doc.body.appendChild(fab);
          }

          const iv = setInterval(() => {
            ensureFab();
            if (findNativeToggle()) { clearInterval(iv); }
          }, 250);

          const mo = new MutationObserver(() => ensureFab());
          mo.observe(doc.body, {childList:true, subtree:true});
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )
