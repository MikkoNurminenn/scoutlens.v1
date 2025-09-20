"""Streamlit multipage entry for the Notes view."""
from __future__ import annotations

from app.quick_notes_page import show_quick_notes_page


def main() -> None:
    show_quick_notes_page()


if __name__ == "__main__":  # pragma: no cover
    main()
