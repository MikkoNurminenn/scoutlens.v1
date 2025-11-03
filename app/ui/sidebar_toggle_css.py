from __future__ import annotations
import streamlit as st

def improve_collapsed_toggle_visibility() -> None:
    """Make Streamlit's collapsed-sidebar toggle big, fixed and high-contrast on every page."""
    st.markdown(
        """
        <style>
        :root{
          --sl-fab-left: calc(env(safe-area-inset-left, 0px) + 10px);
          --sl-fab-top:  calc(env(safe-area-inset-top, 0px) + 10px);
          --sl-fab-size: 56px;
        }

        /* Target both old/new testIDs + ARIA fallback */
        :is(
          [data-testid="stSidebarCollapsedControl"],
          [data-testid="collapsedControl"],
          button[aria-label*="sidebar" i]
        ){
          position: fixed !important;
          left: var(--sl-fab-left) !important;
          top:  var(--sl-fab-top)  !important;
          z-index: 2147483647 !important;
          opacity: 1 !important;
          pointer-events: auto !important;
          width: var(--sl-fab-size) !important;
          height: var(--sl-fab-size) !important;
          border-radius: 14px !important;
          background: rgba(255,255,255,0.16) !important;
          border: 1px solid rgba(255,255,255,0.28) !important;
          box-shadow: 0 8px 24px rgba(0,0,0,0.45) !important;
          backdrop-filter: blur(8px) !important;
          -webkit-backdrop-filter: blur(8px) !important;
        }

        /* If wrapper contains a button, normalize it */
        :is(
          [data-testid="stSidebarCollapsedControl"] button,
          [data-testid="collapsedControl"] button
        ){
          all: unset;
          position: relative !important;
          display: block !important;
          width: 100% !important; height: 100% !important;
          border-radius: 14px !important;
          cursor: pointer !important;
        }

        /* Force any SVG icon to white */
        :is(
          [data-testid="stSidebarCollapsedControl"],
          [data-testid="collapsedControl"]
        ) svg,
        :is(
          [data-testid="stSidebarCollapsedControl"],
          [data-testid="collapsedControl"]
        ) svg * ,
        button[aria-label*="sidebar" i] svg,
        button[aria-label*="sidebar" i] svg * {
          fill: #fff !important;
          stroke: #fff !important;
        }

        /* Fallback invert if icon uses mask/image */
        :is(
          [data-testid="stSidebarCollapsedControl"],
          [data-testid="collapsedControl"],
          button[aria-label*="sidebar" i]
        ){ filter: invert(1) hue-rotate(180deg) contrast(1.1) !important; }

        /* Last resort: hide original glyphs and overlay hamburger */
        :is(
          [data-testid="stSidebarCollapsedControl"],
          [data-testid="collapsedControl"],
          button[aria-label*="sidebar" i]
        ) * {
          color: transparent !important;
          fill: transparent !important;
          stroke: transparent !important;
        }
        :is(
          [data-testid="stSidebarCollapsedControl"],
          [data-testid="collapsedControl"],
          button[aria-label*="sidebar" i]
        )::before,
        :is(
          [data-testid="stSidebarCollapsedControl"] button,
          [data-testid="collapsedControl"] button
        )::before{
          content: "☰";
          position: absolute; inset: 0;
          display: block; text-align: center;
          line-height: var(--sl-fab-size);
          font-size: 24px;
          color: #fff;
          pointer-events: none;
        }

        /* Light theme adjustments */
        @media (prefers-color-scheme: light){
          :is(
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="collapsedControl"],
            button[aria-label*="sidebar" i]
          )::before{ color:#000; }
          :is(
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="collapsedControl"],
            button[aria-label*="sidebar" i]
          ){
            background: rgba(0,0,0,0.08) !important;
            border-color: rgba(0,0,0,0.18) !important;
            filter: none !important;
          }
        }

        @media (max-width: 768px){
          :root { --sl-fab-size: 60px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
