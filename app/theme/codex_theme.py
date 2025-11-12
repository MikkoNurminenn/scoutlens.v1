# File: app/theme/codex_theme.py
from __future__ import annotations

from typing import Dict, List, Literal, Mapping, Optional
import streamlit as st

ThemeName = Literal["auto", "dark", "light"]
ColorwayName = Literal["okabe_ito", "palette_10", "palette_12"]

# ----------------------------- Brand Palettes ----------------------------- #

# Dark theme (UI) tokens
PALETTE_DARK: Dict[str, str] = {
    # Brand
    "brand.primary.500": "#3B82F6",
    "brand.primary.600": "#2563EB",
    "brand.secondary.500": "#8B5CF6",
    "brand.accent.500": "#22C55E",

    # Status
    "status.success": "#10B981",
    "status.warning": "#F59E0B",
    "status.danger":  "#EF4444",
    "status.info":    "#0EA5E9",

    # Focus
    "focus": "#93C5FD",

    # Dark neutrals
    "bg.0": "#0B0F14",
    "bg.1": "#0F172A",
    "bg.2": "#1E293B",
    "border": "#334155",
    "text.1": "#F3F4F6",
    "text.2": "#9CA3AF",

    # Text on accent (ALWAYS LIGHT in dark)
    "fg.on_accent": "#F8FAFC",
}

# Light theme (UI) tokens
PALETTE_LIGHT: Dict[str, str] = {
    "brand.primary.500": "#3B82F6",
    "brand.primary.600": "#2563EB",
    "brand.secondary.500": "#8B5CF6",
    "brand.accent.500": "#22C55E",

    "status.success": "#16A34A",
    "status.warning": "#D97706",
    "status.danger":  "#DC2626",
    "status.info":    "#0284C7",

    "focus": "#2563EB",

    "bg.0": "#FFFFFF",
    "bg.1": "#F9FAFB",
    "bg.2": "#F3F4F6",
    "border": "#E5E7EB",
    "text.1": "#111827",
    "text.2": "#4B5563",

    # Text on accent on light bg is white for solid CTAs
    "fg.on_accent": "#FFFFFF",
}

# --------------------------- Dataviz Palettes ----------------------------- #

OKABE_ITO: List[str] = [
    "#0072B2", "#E69F00", "#009E73", "#56B4E9",
    "#D55E00", "#CC79A7", "#F0E442", "#000000",
]

PALETTE_10: List[str] = [
    "#4E79A7","#F28E2B","#E15759","#76B7B2","#59A14F",
    "#EDC948","#B07AA1","#FF9DA7","#9C755F","#BAB0AC",
]

PALETTE_12: List[str] = [
    "#20639B","#ED553B","#3CAEA3","#F6D55C","#173F5F","#EE8434",
    "#2AB7CA","#B91372","#7E1E9C","#F45D01","#73BFB8","#3F784C",
]

_COLORWAYS: Dict[ColorwayName, List[str]] = {
    "okabe_ito": OKABE_ITO,
    "palette_10": PALETTE_10,
    "palette_12": PALETTE_12,
}

# ------------------------------ Helpers ----------------------------------- #

def _merge_palettes(base: Mapping[str, str], override: Optional[Mapping[str, str]]) -> Dict[str, str]:
    """Shallow merge where override wins; keeps unknown keys untouched."""
    if not override:
        return dict(base)
    merged = dict(base)
    merged.update({k: v for k, v in override.items() if isinstance(v, str) and v})
    return merged


def _style_tag(tag_id: str, css: str) -> str:
    return f'<style id="{tag_id}">{css}</style>'


def _script_tag(tag_id: str, js: str) -> str:
    return f'<script id="{tag_id}">{js}</script>'


def _build_css_tokens(
    dark: Mapping[str, str],
    light: Mapping[str, str],
) -> str:
    """Build CSS variables for both themes + minimal UI bindings (buttons/links/alerts)."""
    css = f"""
:root {{
  color-scheme: light dark;

  /* brand */
  --brand-primary-500: {dark['brand.primary.500']};
  --brand-primary-600: {dark['brand.primary.600']};
  --brand-secondary-500: {dark['brand.secondary.500']};
  --brand-accent-500: {dark['brand.accent.500']};

  /* status */
  --status-success: {dark['status.success']};
  --status-warning: {dark['status.warning']};
  --status-danger:  {dark['status.danger']};
  --status-info:    {dark['status.info']};
  --focus: {dark['focus']};

  /* dark defaults (used when [data-theme] != light) */
  --bg-0: {dark['bg.0']};
  --bg-1: {dark['bg.1']};
  --bg-2: {dark['bg.2']};
  --border: {dark['border']};
  --text-1: {dark['text.1']};
  --text-2: {dark['text.2']};
  --fg-on-accent: {dark['fg.on_accent']};
}}

/* Explicit light theme override */
:root[data-theme="light"], html[data-theme="light"] {{
  --bg-0: {light['bg.0']};
  --bg-1: {light['bg.1']};
  --bg-2: {light['bg.2']};
  --border: {light['border']};
  --text-1: {light['text.1']};
  --text-2: {light['text.2']};
  --fg-on-accent: {light['fg.on_accent']};
}}

/* Base bindings */
body, [data-testid="stAppViewContainer"] {{
  background: var(--bg-0);
  color: var(--text-1);
}}
section[data-testid="stSidebar"] {{ background: var(--bg-1); }}
a {{ color: var(--brand-primary-500); }}
a:hover {{ color: var(--brand-primary-600); }}

/* Buttons: Streamlit primary + generic */
:where(.stButton, .stDownloadButton) > button[kind="primary"],
:where(.stButton, .stDownloadButton) > button[data-testid="baseButton-primary"],
:where(.stButton) > button:not([kind]) {{
  background: var(--brand-primary-600);
  border: 1px solid var(--brand-primary-600);
  color: var(--fg-on-accent) !important; /* safety */
}}
:where(.stButton, .stDownloadButton) > button:is(:hover, :focus-visible) {{
  background: var(--brand-primary-500);
  color: var(--fg-on-accent) !important;
}}
:where(.stButton) > button:disabled {{
  opacity: .65; cursor: not-allowed; box-shadow: none; transform: none;
}}

/* Alerts (left border by kind) */
.stAlert[data-baseweb="notification"][kind="success"] {{ border-left: 4px solid var(--status-success); }}
.stAlert[data-baseweb="notification"][kind="warning"] {{ border-left: 4px solid var(--status-warning); }}
.stAlert[data-baseweb="notification"][kind="error"]   {{ border-left: 4px solid var(--status-danger); }}
.stAlert[data-baseweb="notification"][kind="info"]    {{ border-left: 4px solid var(--status-info); }}

/* Focus visibility */
*:focus {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
"""
    return css


def _force_theme_script(theme: ThemeName) -> str:
    """Optionally force theme by writing to documentElement."""
    if theme == "auto":
        return ""
    # Set both in iframe and parent (Streamlit runs in iframe sometimes)
    return """
(function(){
  try {
    const apply = (doc) => {
      if (!doc || !doc.documentElement) return;
      doc.documentElement.dataset.slTheme = '%(t)s';
      doc.documentElement.style.colorScheme = '%(cs)s';
      doc.documentElement.setAttribute('data-theme', '%(t)s');
    };
    apply(document);
    if (window.parent && window.parent !== window && window.parent.document) {
      apply(window.parent.document);
    }
  } catch(_) {}
})();""".replace("%(t)s", "dark" if theme == "dark" else "light").replace(
        "%(cs)s", "dark" if theme == "dark" else "light"
    )

# ------------------------------ Public API -------------------------------- #

def apply_theme(
    theme: ThemeName = "auto",
    *,
    force: bool = False,
    colorway: ColorwayName = "okabe_ito",
    overrides_dark: Optional[Mapping[str, str]] = None,
    overrides_light: Optional[Mapping[str, str]] = None,
) -> None:
    """
    Apply unified UI + dataviz theme.

    Parameters
    ----------
    theme : "auto" | "dark" | "light"
        Visual theme preference. "auto" respects existing page setting.
    force : bool
        If True, injects JS to set `data-theme` & `color-scheme` explicitly.
    colorway : one of {"okabe_ito","palette_10","palette_12"}
        Default categorical color cycle for charts.
    overrides_dark / overrides_light : Mapping[str,str]
        Optional per-theme token overrides (e.g. tweak brand.primary.600).
    """
    dark = _merge_palettes(PALETTE_DARK, overrides_dark)
    light = _merge_palettes(PALETTE_LIGHT, overrides_light)

    # Inject theme forcing script first (optional)
    if force and theme in ("dark", "light"):
        st.markdown(_script_tag("codex-force-theme", _force_theme_script(theme)), unsafe_allow_html=True)

    # Inject CSS tokens (idempotent by tag id)
    css = _build_css_tokens(dark, light)
    st.markdown(_style_tag("codex-theme-tokens", css), unsafe_allow_html=True)

    # ---------------- Dataviz: Plotly / Altair / Matplotlib ---------------- #
    palette = _COLORWAYS[colorway]

    # Plotly template
    try:
        import plotly.io as pio  # type: ignore
        # choose token set by effective theme (dark unless explicitly light)
        effective = light if (theme == "light") else dark
        pio.templates["codex_theme"] = {
            "layout": {
                "paper_bgcolor": effective["bg.1"],
                "plot_bgcolor": effective["bg.2"],
                "font": {"color": effective["text.1"]},
                "colorway": palette,
                "xaxis": {"gridcolor": effective["border"], "zerolinecolor": effective["border"]},
                "yaxis": {"gridcolor": effective["border"], "zerolinecolor": effective["border"]},
            }
        }
        pio.templates.default = "codex_theme"
    except Exception:
        pass  # Plotly optional

    # Altair theme
    try:
        import altair as alt  # type: ignore

        def _codex_altair() -> dict:
            eff = light if (theme == "light") else dark
            return {
                "config": {
                    "background": eff["bg.2"],
                    "view": {"stroke": eff["border"]},
                    "axis": {
                        "labelColor": eff["text.1"],
                        "titleColor": eff["text.1"],
                        "gridColor": eff["border"],
                        "domainColor": eff["border"],
                    },
                    "legend": {"labelColor": eff["text.1"], "titleColor": eff["text.1"]},
                    "title": {"color": eff["text.1"]},
                    "range": {"category": palette},
                }
            }

        alt.themes.register("codex_theme", _codex_altair)  # type: ignore
        alt.themes.enable("codex_theme")  # type: ignore
    except Exception:
        pass  # Altair optional

    # Matplotlib rcParams
    try:
        import matplotlib as mpl  # type: ignore
        eff = light if (theme == "light") else dark
        mpl.rcParams.update({
            "figure.facecolor": eff["bg.1"],
            "axes.facecolor": eff["bg.2"],
            "axes.edgecolor": eff["border"],
            "axes.labelcolor": eff["text.1"],
            "xtick.color": eff["text.1"],
            "ytick.color": eff["text.1"],
            "grid.color": eff["border"],
            "text.color": eff["text.1"],
            "axes.prop_cycle": mpl.cycler(color=palette),
        })
    except Exception:
        pass  # Matplotlib optional


def get_color(token: str, default: str = "") -> str:
    """
    Return a color by semantic token. Dark palette is the source of truth.
    Use overrides via `apply_theme(...overrides_dark/light=...)` when needed.
    """
    return PALETTE_DARK.get(token) or PALETTE_LIGHT.get(token, default)
