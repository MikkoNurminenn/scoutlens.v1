from __future__ import annotations

from typing import Dict
import html

import streamlit as st

# --- Suositukset (nopea yhteenveto) ---
# Tabler Icons (MIT): erittäin laaja, moderni outline + filled, data-appeihin sopiva.
# Lucide (MIT): Feather-fork, kevyt, yhtenäinen nimeäminen, helppo CDN-käyttö.
# Remix Icon (Apache-2.0): line+fill-parit, laaja valikoima sovellusikoneita.
# Heroicons (MIT): Tailwind-tyyli, outline+solid; hyvä jos pidät pehmeämmästä geometriasta.
# Phosphor (MIT): monipaksuudet (thin–bold), hyvä jos tarvitset painotusta tilojen mukaan.

# --- 1) Lucide-CDN (helppokäyttöinen, ei offline) ---
_LUCIDE_INIT = """
<link id="lucide-css" rel="preconnect" href="https://unpkg.com" />
<script id="lucide-js" src="https://unpkg.com/lucide@latest"></script>
<style id="lucide-style">
  .cx-icon { display:inline-block; vertical-align:text-bottom; line-height:1; }
  .cx-icon svg { width: 1em; height: 1em; stroke: currentColor; }
</style>
<script id="lucide-run">
  (function(){
    const w = window;
    if (w.__cxLucideReady) { try { lucide && lucide.createIcons(); } catch(_){}; return; }
    w.__cxLucideReady = true;
    function run(){ try { lucide && lucide.createIcons(); } catch(_){} }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run, {once:true});
    else run();
    // Re-render on Streamlit DOM updates
    const obs = new MutationObserver(run);
    obs.observe(document.body, {subtree:true, childList:true});
    w.addEventListener("beforeunload", () => { try { obs.disconnect(); } catch(_){} });
  })();
</script>
"""


def use_lucide() -> None:
    """Injektoi Lucide-CDN:n; käytä lucide('search') tms. ikonin piirtämiseen."""
    st.markdown(_LUCIDE_INIT, unsafe_allow_html=True)


def lucide(name: str, *, size: int = 18) -> str:
    """Palauta <i data-lucide='name'> ikoni; käytä HTML:ssä."""
    safe = html.escape(name)
    # font-size kontrolloi kokoa; 1em == size px
    return f"<i class='cx-icon' data-lucide='{safe}' style='font-size:{size}px' aria-hidden='true'></i>"


# --- 2) Offline inline-SVG fallback (pieni setti perusikoneita) ---
# Huom: nämä eivät ole 1:1 Tabler-polkuja vaan kevyet, siistit outline-kuvat.
INLINE_SVG_PATHS: Dict[str, str] = {
    "home":      "<path d='M3 11 L12 3 L21 11 M5 9 V21 H10 V14 H14 V21 H19 V9' fill='none'/>",
    "database":  "<ellipse cx='12' cy='5' rx='8' ry='3'/><path d='M4 5 V15 C4 17 8 19 12 19 C16 19 20 17 20 15 V5'/>",
    "search":    "<circle cx='11' cy='11' r='6'/><path d='M16 16 L21 21'/>",
    "bell":      "<path d='M6 10 C6 6.7 8.7 4 12 4 C15.3 4 18 6.7 18 10 V14 L20 16 H4 L6 14 Z'/><path d='M10 18 C10.6 19.2 11.7 20 13 20'/>",
    "gear":      "<path d='M12 8 A4 4 0 1 0 12 16 A4 4 0 1 0 12 8 Z' fill='none'/>"
                  "<path d='M12 2 V4 M12 20 V22 M2 12 H4 M20 12 H22 M4.9 4.9 L6.3 6.3 M17.7 17.7 L19.1 19.1 M4.9 19.1 L6.3 17.7 M17.7 6.3 L19.1 4.9'/>",
    "user":      "<circle cx='12' cy='8' r='4'/><path d='M4 20 C4 16.8 7.6 15 12 15 C16.4 15 20 16.8 20 20'/>",
    "logout":    "<path d='M15 12 H3'/><path d='M7 8 L3 12 L7 16'/><path d='M10 4 H17 C18.1 4 19 4.9 19 6 V18 C19 19.1 18.1 20 17 20 H10'/>",
}


def inline_icon(name: str, *, size: int = 18, stroke: float = 1.8) -> str:
    """Palauta inline-SVG ikoni nimen perusteella (offline)."""
    p = INLINE_SVG_PATHS.get(name)
    if not p:
        # siisti fallback: pieni ympyrä
        p = "<circle cx='12' cy='12' r='9'/>"
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' "
        "viewBox='0 0 24 24' fill='none' stroke='currentColor' "
        f"stroke-width='{stroke}' stroke-linecap='round' stroke-linejoin='round' "
        f"width='{size}' height='{size}' role='img' aria-label='{html.escape(name)}'>"
        f"{p}</svg>"
    )


__all__ = ["use_lucide", "lucide", "inline_icon", "INLINE_SVG_PATHS"]
