from __future__ import annotations

from streamlit.components.v1 import html as _html


def sl_fix_sidebar_toggle(
    *,
    bg: str = "#ffffff",
    fg: str = "#0b1020",
    border: str = "1px solid rgba(15,23,42,.22)",
    ring: str = "rgba(99,102,241,.35)",
    size_rem: float = 2.75,
    rotate_closed_deg: int = 180,
    enable_badge: bool = False,
    badge_text: str = "Open",
) -> None:
    """
    Force the sidebar toggle button to white when collapsed (and optionally always).
    Inline styles beat all CSS. Works across Streamlit versions.
    """
    w = h = int(size_rem * 16)
    badge_js = f"""
      if ({str(enable_badge).lower()}) {{
        if (!btn.dataset.slBadge) {{
          const b = doc.createElement('span');
          b.textContent = "{badge_text}";
          Object.assign(b.style, {{
            position: 'absolute', left: (btnRect.right + 8) + 'px', top: (btnRect.top + btnRect.height/2) + 'px',
            transform: 'translateY(-50%)', padding: '4px 8px', font: '600 11px/1 Inter,system-ui,sans-serif',
            letterSpacing: '.06em', color: '{fg}', background: 'rgba(0,0,0,.35)',
            borderRadius: '999px', border: '1px solid {ring}', backdropFilter:'blur(4px)', zIndex: 1301
          }});
          b.className = 'sl-open-badge';
          doc.body.appendChild(b);
          btn.dataset.slBadge = '1';
        }}
      }}
    """
    js = f"""
(function() {{
  const doc = (window.parent && window.parent.document) ? window.parent.document : document;

  function styleBtn(btn) {{
    if (!btn) return;
    // container fixes
    const host = btn.closest('[data-testid="stSidebarCollapseButton"]') || btn.parentElement;
    if (host) {{
      host.style.position = 'fixed';
      host.style.zIndex = 1300;
      host.style.top = 'max(0.75rem, env(safe-area-inset-top))';
      host.style.left = 'max(0.75rem, env(safe-area-inset-left))';
      host.style.width = '{w}px';
      host.style.height = '{h}px';
      host.style.padding = '0';
    }}

    // inline styles: always win
    btn.style.all = 'unset';
    btn.style.position = 'fixed';
    btn.style.top = 'max(0.75rem, env(safe-area-inset-top))';
    btn.style.left = 'max(0.75rem, env(safe-area-inset-left))';
    btn.style.width = '{w}px';
    btn.style.height = '{h}px';
    btn.style.display = 'inline-flex';
    btn.style.alignItems = 'center';
    btn.style.justifyContent = 'center';
    btn.style.borderRadius = '999px';
    btn.style.background = '{bg}';
    btn.style.color = '{fg}';
    btn.style.border = '{border}';
    btn.style.boxShadow = '0 16px 36px rgba(15,23,42,.28), inset 0 0 0 .6px rgba(255,255,255,.45)';
    btn.style.backdropFilter = 'blur(6px)';
    btn.style.cursor = 'pointer';
    btn.style.transition = 'transform .18s ease, box-shadow .18s ease, border-color .18s ease';
    btn.onmouseenter = () => {{
      btn.style.transform = 'translateY(-1px)';
      btn.style.boxShadow = '0 20px 42px rgba(15,23,42,.32), inset 0 0 0 .8px rgba(255,255,255,.55), 0 0 0 3px {ring}';
      btn.style.outline = 'none';
      btn.style.border = '1px solid rgba(99,102,241,.55)';
    }};
    btn.onmouseleave = () => {{
      btn.style.transform = 'none';
      btn.style.boxShadow = '0 16px 36px rgba(15,23,42,.28), inset 0 0 0 .6px rgba(255,255,255,.45)';
      btn.style.border = '{border}';
    }};

    // icon color + rotation on collapsed
    const svg = btn.querySelector('svg');
    const collapsed = doc.body.classList.contains('stSidebarCollapsedControl');
    if (svg) {{
      svg.style.fill = 'currentColor';
      svg.style.stroke = 'currentColor';
      svg.style.width = '1.3rem';
      svg.style.height = '1.3rem';
      svg.style.transform = collapsed ? 'rotate({rotate_closed_deg}deg)' : 'rotate(0deg)';
      svg.style.transition = 'transform .18s ease';
      svg.querySelectorAll('*').forEach(n => {{
        n.style.fill = 'currentColor';
        n.style.stroke = 'currentColor';
      }});
    }}

    // optional badge
    const btnRect = btn.getBoundingClientRect();
    {badge_js}
  }}

  function apply() {{
    const candidates = doc.querySelectorAll('[data-testid="stSidebarCollapseButton"] button, button[data-testid="stSidebarCollapseButton"]');
    if (!candidates.length) return;
    candidates.forEach(styleBtn);
  }}

  // Initial
  apply();

  // Re-apply on any DOM mutation / class change
  const mo = new MutationObserver(() => apply());
  mo.observe(doc.body, {{ subtree: true, childList: true, attributes: true, attributeFilter: ['class','style'] }});

  // Also after load & on clicks
  window.addEventListener('load', apply);
  doc.addEventListener('click', (e) => {{
    if (e.target && e.target.closest('[data-testid="stSidebarCollapseButton"]')) {{
      setTimeout(apply, 0);
    }}
  }});
}})();
    """
    _html(f"<script>{{js}}</script>", height=0, width=0)

