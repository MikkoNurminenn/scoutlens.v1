from __future__ import annotations

from typing import Dict, List
import streamlit as st

# Yksi totuuslähde: UI + dataviz käyttävät samoja semanttisia värejä.
PALETTE: Dict[str, str] = {
    # Brand (Codex)
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

    # Dark neutrals (Default UI)
    "dark.bg.0": "#0B0F14",
    "dark.bg.1": "#0F172A",
    "dark.bg.2": "#1E293B",
    "dark.border": "#334155",
    "dark.text.1": "#F3F4F6",
    "dark.text.2": "#9CA3AF",

    # Light neutrals (fallback)
    "light.bg.0": "#FFFFFF",
    "light.bg.1": "#F9FAFB",
    "light.bg.2": "#F3F4F6",
    "light.border": "#E5E7EB",
    "light.text.1": "#111827",
    "light.text.2": "#4B5563",
}

# Värisokeusturvallinen datapaletti (Okabe–Ito)
DATAVIZ_OKABE_ITO: List[str] = [
    "#0072B2", "#E69F00", "#009E73", "#56B4E9",
    "#D55E00", "#CC79A7", "#F0E442", "#000000",
]

# Vaihtoehtoinen 10-värinen
DATAVIZ_10: List[str] = [
    "#4E79A7","#F28E2B","#E15759","#76B7B2","#59A14F",
    "#EDC948","#B07AA1","#FF9DA7","#9C755F","#BAB0AC",
]

def _css_tokens() -> str:
    """CSS-muuttujat UI-yhtenäisyyteen. Miksi: yhden paikan brändäys."""
    return f"""
    <style id="codex-theme-tokens">
      :root {{
        --brand-primary-500: {PALETTE['brand.primary.500']};
        --brand-primary-600: {PALETTE['brand.primary.600']};
        --brand-secondary-500: {PALETTE['brand.secondary.500']};
        --brand-accent-500: {PALETTE['brand.accent.500']};
        --status-success: {PALETTE['status.success']};
        --status-warning: {PALETTE['status.warning']};
        --status-danger:  {PALETTE['status.danger']};
        --status-info:    {PALETTE['status.info']};
        --focus: {PALETTE['focus']};

        --bg-0: {PALETTE['dark.bg.0']};
        --bg-1: {PALETTE['dark.bg.1']};
        --bg-2: {PALETTE['dark.bg.2']};
        --border: {PALETTE['dark.border']};
        --text-1: {PALETTE['dark.text.1']};
        --text-2: {PALETTE['dark.text.2']};
      }}

      html[data-theme="light"] :root {{
        --bg-0: {PALETTE['light.bg.0']};
        --bg-1: {PALETTE['light.bg.1']};
        --bg-2: {PALETTE['light.bg.2']};
        --border: {PALETTE['light.border']};
        --text-1: {PALETTE['light.text.1']};
        --text-2: {PALETTE['light.text.2']};
      }}

      body, [data-testid="stAppViewContainer"] {{
        background: var(--bg-0);
        color: var(--text-1);
      }}
      section[data-testid="stSidebar"] {{ background: var(--bg-1); }}
      .sb-header-card {{ background: var(--bg-1); border: 1px solid var(--border); color: var(--text-1); }}
      .sb-title {{ color: var(--text-1); }}
      .sb-tagline {{ color: var(--text-2); }}
      .sb-footer-line {{ border-top: 1px solid var(--border); color: var(--text-2); }}
      .stButton>button {{
        background: var(--brand-primary-600);
        border: 1px solid var(--brand-primary-600);
        color: #fff;
      }}
      .stButton>button:hover {{ background: var(--brand-primary-500); }}
      a {{ color: var(--brand-primary-500); }}
      a:hover {{ color: var(--brand-primary-600); }}
      .stAlert[data-baseweb="notification"][kind="success"] {{ border-left: 4px solid var(--status-success); }}
      .stAlert[data-baseweb="notification"][kind="warning"] {{ border-left: 4px solid var(--status-warning); }}
      .stAlert[data-baseweb="notification"][kind="error"]   {{ border-left: 4px solid var(--status-danger); }}
      .stAlert[data-baseweb="notification"][kind="info"]    {{ border-left: 4px solid var(--status-info); }}
      *:focus {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
    </style>
    """

def _force_dark_theme_script() -> str:
    """Pakota dark-tila. Miksi: yhtenäinen kontrasti tiheässä datassa."""
    return """
    <script id="codex-force-dark">
      (function(){
        const w = window;
        if (w.__codexForceDark) return;
        w.__codexForceDark = true;
        const doc = (w.parent && w.parent.document) ? w.parent.document : document;
        if (!doc || !doc.documentElement) return;
        doc.documentElement.dataset.slTheme = 'dark';
        doc.documentElement.style.colorScheme = 'dark';
        doc.documentElement.setAttribute('data-theme', 'dark');
      })();
    </script>
    """

def apply_theme() -> None:
    """Kutsu kerran appin alussa. Miksi: synkronoi UI ja kaaviot."""
    st.markdown(_force_dark_theme_script(), unsafe_allow_html=True)
    st.markdown(_css_tokens(), unsafe_allow_html=True)

    # Plotly
    try:
        import plotly.io as pio  # type: ignore
        pio.templates["codex_dark"] = {
            "layout": {
                "paper_bgcolor": PALETTE["dark.bg.1"],
                "plot_bgcolor": PALETTE["dark.bg.2"],
                "font": {"color": PALETTE["dark.text.1"]},
                "colorway": DATAVIZ_OKABE_ITO,
                "xaxis": {"gridcolor": PALETTE["dark.border"], "zerolinecolor": PALETTE["dark.border"]},
                "yaxis": {"gridcolor": PALETTE["dark.border"], "zerolinecolor": PALETTE["dark.border"]},
            }
        }
        pio.templates.default = "codex_dark"
    except Exception:
        pass  # ei Plotlya asennettuna

    # Altair
    try:
        import altair as alt  # type: ignore

        def _codex_altair_theme() -> dict:
            return {
                "config": {
                    "background": PALETTE["dark.bg.2"],
                    "view": {"stroke": PALETTE["dark.border"]},
                    "axis": {
                        "labelColor": PALETTE["dark.text.1"],
                        "titleColor": PALETTE["dark.text.1"],
                        "gridColor": PALETTE["dark.border"],
                        "domainColor": PALETTE["dark.border"],
                    },
                    "legend": {"labelColor": PALETTE["dark.text.1"], "titleColor": PALETTE["dark.text.1"]},
                    "title": {"color": PALETTE["dark.text.1"]},
                    "range": {"category": DATAVIZ_OKABE_ITO},
                }
            }

        alt.themes.register("codex_dark", _codex_altair_theme)  # type: ignore
        alt.themes.enable("codex_dark")  # type: ignore
    except Exception:
        pass

    # Matplotlib
    try:
        import matplotlib as mpl  # type: ignore
        mpl.rcParams.update({
            "figure.facecolor": PALETTE["dark.bg.1"],
            "axes.facecolor": PALETTE["dark.bg.2"],
            "axes.edgecolor": PALETTE["dark.border"],
            "axes.labelcolor": PALETTE["dark.text.1"],
            "xtick.color": PALETTE["dark.text.1"],
            "ytick.color": PALETTE["dark.text.1"],
            "grid.color": PALETTE["dark.border"],
            "text.color": PALETTE["dark.text.1"],
            "axes.prop_cycle": mpl.cycler(color=DATAVIZ_OKABE_ITO),
        })
    except Exception:
        pass

def get_color(token: str, default: str = "") -> str:
    """Palauta väri token-avaimella. Miksi: välttää kovakoodaukset."""
    return PALETTE.get(token, default)
