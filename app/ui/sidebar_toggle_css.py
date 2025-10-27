from __future__ import annotations

import streamlit as st


def improve_collapsed_toggle_visibility() -> None:
    """Make Streamlit's built-in collapsed-sidebar toggle big, fixed and high-contrast."""
    st.markdown(
        """
        <style>
        /* Safe-area muuttujat lovinäytöille */
        :root {
          --sl-fab-left: calc(env(safe-area-inset-left, 0px) + 10px);
          --sl-fab-top:  calc(env(safe-area-inset-top, 0px) + 10px);
        }

        /* Streamlit on käyttänyt eri testID:itä versioissa:
           - stSidebarCollapsedControl  (uudemmat)
           - collapsedControl           (vanhemmat)
           Ota molemmat + fallback ARIA-labeliin, jossa esiintyy 'sidebar'.
        */
        :is(
          [data-testid="stSidebarCollapsedControl"],
          [data-testid="collapsedControl"],
          button[aria-label*="sidebar" i]
        ) {
          position: fixed !important;
          left: var(--sl-fab-left) !important;
          top:  var(--sl-fab-top)  !important;
          z-index: 2147483647 !important;
          /* Varmista että elementti ylipäätään näkyy */
          opacity: 1 !important;
          pointer-events: auto !important;
        }

        /* Varsinainen nappi sisällä */
        :is(
          [data-testid="stSidebarCollapsedControl"],
          [data-testid="collapsedControl"]
        ) button,
        button[aria-label*="sidebar" i] {
          width: 54px; height: 54px;
          border-radius: 14px;
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          background: rgba(255,255,255,0.16) !important;
          border: 1px solid rgba(255,255,255,0.28) !important;
          color: #fff !important;
          box-shadow: 0 8px 24px rgba(0,0,0,0.45);
          transition: transform .08s ease, background .15s ease;
        }
        :is(
          [data-testid="stSidebarCollapsedControl"],
          [data-testid="collapsedControl"]
        ) button:active,
        button[aria-label*="sidebar" i]:active {
          transform: scale(0.96);
        }

        /* Tee myös näkyvä kun headeri skrollaa */
        header { z-index: 1000; } /* alle FABin */

        /* Pieni lisäkoko mobiilissa */
        @media (max-width: 768px) {
          :is(
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="collapsedControl"]
          ) button,
          button[aria-label*="sidebar" i] {
            width: 58px; height: 58px;
          }
        }

        /* ----- Replace the black chevrons with a white hamburger icon ----- */

        /* Kohteet: eri Streamlit-versioiden "sidebar collapsed" -napit */
        :is([data-testid="stSidebarCollapsedControl"],
            [data-testid="collapsedControl"]) { position: fixed !important; }

        /* Piilota sisäiset ikonit (chevrons tms.) varmasti */
        :is([data-testid="stSidebarCollapsedControl"],
            [data-testid="collapsedControl"]) button > * {
          opacity: 0 !important;           /* älä näytä alkuperäistä kuvitusta */
        }

        /* Lisää oma valkoinen ikoni napin päälle */
        :is([data-testid="stSidebarCollapsedControl"],
            [data-testid="collapsedControl"]) button::before {
          content: "☰";                     /* hamburger-ikoni */
          position: absolute;
          inset: 0;
          display: block;
          text-align: center;
          line-height: 54px;                /* sama kuin napin korkeus */
          font-size: 24px;
          color: #fff;
          pointer-events: none;             /* klikkaus menee napille */
        }

        /* (Valinnainen) vaalea teema -> tumma ikoni */
        @media (prefers-color-scheme: light) {
          :is([data-testid="stSidebarCollapsedControl"],
              [data-testid="collapsedControl"]) button::before {
            color: #000;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
