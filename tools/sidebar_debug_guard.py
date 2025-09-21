"""Runtime helper to detect sidebar usage outside the dedicated module."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Callable, Iterable, Optional

import streamlit as st

_DEFAULT_ALLOWED = (Path(__file__).resolve().parents[1] / "app" / "ui" / "sidebar.py",)


class SidebarDebugGuard:
    """Wraps ``st.sidebar`` and reports calls made from disallowed files."""

    def __init__(
        self,
        *,
        allowed_paths: Optional[Iterable[Path]] = None,
        strict: bool = False,
        reporter: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._original = getattr(st, "sidebar")
        self._allowed = {
            Path(p).resolve()
            for p in (allowed_paths if allowed_paths is not None else _DEFAULT_ALLOWED)
        }
        self._strict = strict
        self._reporter = reporter or self._default_reporter
        self._installed = False

    # ------------------------------------------------------------------
    def activate(self) -> None:
        """Replace ``st.sidebar`` with this guard instance."""

        if self._installed:
            return
        setattr(st, "sidebar", self)
        self._installed = True

    def deactivate(self) -> None:
        """Restore the original ``st.sidebar`` object."""

        if not self._installed:
            return
        setattr(st, "sidebar", self._original)
        self._installed = False

    def __enter__(self) -> "SidebarDebugGuard":  # pragma: no cover - dev helper
        self.activate()
        return self

    def __exit__(self, *exc: object) -> None:  # pragma: no cover - dev helper
        self.deactivate()

    # ------------------------------------------------------------------
    def __getattr__(self, name: str):
        target = getattr(self._original, name)
        if callable(target):
            def wrapped(*args, **kwargs):
                violation = self._check_callsite(name)
                if violation is not None:
                    if self._strict:
                        raise RuntimeError(violation)
                    self._reporter(violation)
                return target(*args, **kwargs)

            wrapped.__name__ = getattr(target, "__name__", name)
            wrapped.__doc__ = getattr(target, "__doc__")
            return wrapped
        return target

    # ------------------------------------------------------------------
    def _check_callsite(self, name: str) -> str | None:
        stack = inspect.stack()[2:]  # skip wrapper frames
        caller = None
        for frame_info in stack:
            path = Path(frame_info.filename).resolve()
            if path in self._allowed:
                return None
            if caller is None:
                caller = frame_info

        location = "<unknown>"
        if caller and caller.filename:
            path = Path(caller.filename).resolve()
            location = f"{path}:{caller.lineno}"
        allowed = ", ".join(str(p) for p in sorted(self._allowed))
        return (
            f"st.sidebar.{name} was called from {location}.\n"
            f"Allowed sidebar writers: {allowed}"
        )

    @staticmethod
    def _default_reporter(message: str) -> None:
        try:
            st.warning(message)
        except Exception:
            print(message)


def install_sidebar_debug_guard(*, strict: bool = False) -> SidebarDebugGuard:
    """Install the sidebar debug guard and return it for optional teardown."""

    guard = SidebarDebugGuard(strict=strict)
    guard.activate()
    return guard


__all__ = ["SidebarDebugGuard", "install_sidebar_debug_guard"]
