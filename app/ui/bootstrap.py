from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def bootstrap_global_ui() -> None:
    """Inject once-per-session UI helpers (sidebar FAB + CSS for native toggle)."""
    if st.session_state.get("_ui_bootstrapped"):
        return
    st.session_state["_ui_bootstrapped"] = True

    components.html(
        """
        <style>
          /* Korosta myös Streamlitin omaa »-nappia, kun se on näkyvissä */
          [data-testid="collapsedControl"] button,
          [data-testid="stSidebarCollapseButton"],
          button[aria-label*="sidebar" i]{
            width: 40px; height: 40px;
            border-radius: 12px;
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
            background: rgba(255,255,255,0.14);
            border: 1px solid rgba(255,255,255,0.28);
            color: #fff !important;
            box-shadow: 0 2px 10px rgba(0,0,0,0.35);
          }

          /* Meidän kelluva FAB (näkyy aina) */
          #sl-sidebar-fab{
            position: fixed;
            left: calc(env(safe-area-inset-left, 0px) + 10px);
            top:  calc(env(safe-area-inset-top, 0px) + 10px);
            width: 48px; height: 48px;
            border: none; border-radius: 14px;
            background: rgba(255,255,255,0.16);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            color:#fff; font-size:24px; line-height:48px; text-align:center;
            cursor:pointer; box-shadow:0 6px 20px rgba(0,0,0,0.45);
            z-index:2147483647; transition:transform .08s ease, background .15s ease;
          }
          #sl-sidebar-fab:active{ transform: scale(0.96); }
          @media (max-width:768px){
            #sl-sidebar-fab{ width:54px; height:54px; line-height:54px; font-size:26px; }
          }
        </style>

        <script>
        (function(){
          if (window.__sl_global_toggle_init) return;
          window.__sl_global_toggle_init = true;

          const doc = document;

          function ensureFab(){
            if (doc.getElementById('sl-sidebar-fab')) return;
            const b = doc.createElement('button');
            b.id = 'sl-sidebar-fab';
            b.type = 'button';
            b.title = 'Toggle sidebar';
            b.textContent = '☰';
            b.addEventListener('click', () => {
              const btn =
                doc.querySelector('[data-testid="collapsedControl"] button') ||
                doc.querySelector('[data-testid="stSidebarCollapseButton"]') ||
                Array.from(doc.querySelectorAll('button[aria-label]'))
                     .find(x => /sidebar/i.test(x.getAttribute('aria-label')||''));
              if (btn) btn.click();
            });
            doc.body.appendChild(b);
          }

          // Luo FAB heti ja pidä se hengissä rerunien yli
          ensureFab();

          // Etsi natiivinapin mount kun DOM muuttuu (S-rerunit)
          const mo = new MutationObserver(() => ensureFab());
          mo.observe(doc.body, {subtree:true, childList:true});

          // Lisäksi pollaa varmuuden vuoksi
          const iv = setInterval(ensureFab, 500);
          window.addEventListener('beforeunload', () => clearInterval(iv));
        })();
        </script>
        """,
        height=0,
    )
