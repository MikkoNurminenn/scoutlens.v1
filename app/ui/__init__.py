"""Lightweight UI helpers with safe optional imports."""

from importlib import import_module
from typing import Callable, Optional


def _load_callable(module_name: str, attr: str) -> Optional[Callable]:
    try:
        module = import_module(module_name)
        fn = getattr(module, attr, None)
        return fn if callable(fn) else None
    except Exception:
        return None


def bootstrap_sidebar_auto_collapse() -> None:
    """Attempt to run an optional sidebar bootstrap without crashing."""
    candidates = [
        ("app.ui.sidebar", "bootstrap_sidebar_auto_collapse"),
        ("app.ui.bootstrap", "bootstrap_sidebar_auto_collapse"),
        ("app.ui.layout", "bootstrap_sidebar_auto_collapse"),
    ]
    for mod, attr in candidates:
        fn = _load_callable(mod, attr)
        if fn:
            fn()
            return
    # no-op if nothing found


__all__ = ["bootstrap_sidebar_auto_collapse"]

