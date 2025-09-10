import time
from contextlib import contextmanager
import streamlit as st


def _is_debug() -> bool:
    try:
        return bool(st.secrets.get("DEBUG_PERF")) or st.session_state.get("DEBUG_PERF")
    except Exception:
        return False


@contextmanager
def track(label: str):
    start = time.perf_counter()
    yield
    dur = (time.perf_counter() - start) * 1000
    st.session_state.setdefault("_perf", []).append((label, dur))


def render_perf() -> None:
    if not _is_debug():
        st.session_state.pop("_perf", None)
        return
    entries = st.session_state.get("_perf", [])
    if entries:
        with st.expander("⏱ Perf", expanded=False):
            for name, dur in entries:
                st.write(f"{name}: {dur:.1f} ms")
    st.session_state["_perf"] = []
