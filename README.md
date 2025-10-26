# Streamlit Sidebar Buttons – Debug Task

## Goal
Fix the provided Streamlit app so that sidebar buttons *always* render and remain visible while keeping custom styles.

## What’s broken (intentionally)
- Sidebar starts collapsed.
- Over-aggressive CSS hides `.stButton`.
- Buttons are conditionally skipped and there’s an early `return`.
- Duplicate `key` values.
- A placeholder is emptied after render.

## Acceptance Criteria
1. Sidebar renders **expanded** by default (no "collapsed").
2. At least **two** buttons inside `with st.sidebar:` block.
3. Each button has a **unique** `key`.
4. No CSS that hides/hard-disables buttons in the sidebar:
   - No `display:none`, `visibility:hidden`, `opacity:0`, `pointer-events:none` affecting sidebar buttons.
5. No early `return` before the sidebar block.
6. No `.empty()` calls that can clear sidebar content.
7. Keep custom styling, but scope it safely to sidebar buttons without hiding them.

## Commands
```bash
python -m venv .venv && source .venv/bin/activate     # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
pytest -q
streamlit run starter/app.py
```

## Tips

* Prefer `with st.sidebar:` block.
* Scope CSS to `section[data-testid="stSidebar"] ...` and avoid destructive properties.
* Keep logic outside brittle conditions; use session_state when needed.
