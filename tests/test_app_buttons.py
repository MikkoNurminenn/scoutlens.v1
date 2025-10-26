"""Static checks ensuring the sidebar button task stays solved."""

from __future__ import annotations

import ast
import re
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "starter" / "app.py"
SRC = APP_PATH.read_text(encoding="utf-8")


def _iter_calls(tree: ast.AST, name: str):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            attr = getattr(node.func, "attr", "")
            if attr == name:
                yield node


def test_no_collapsed_sidebar() -> None:
    tree = ast.parse(SRC)
    for call in _iter_calls(tree, "set_page_config"):
        for kw in call.keywords or []:
            if kw.arg == "initial_sidebar_state":
                if isinstance(kw.value, ast.Constant):
                    assert str(kw.value.value).lower() != "collapsed", (
                        "initial_sidebar_state must not be 'collapsed'"
                    )


def test_has_sidebar_block_and_buttons() -> None:
    assert re.search(r"with\s+st\.sidebar\s*:", SRC), "Expected a 'with st.sidebar:' block"
    buttons = re.findall(r"st\.button\s*\(", SRC)
    assert len(buttons) >= 2, "Expected at least two st.button(...) calls"


def test_unique_button_keys() -> None:
    keys = re.findall(r"st\.button\s*\([^)]*key\s*=\s*([\"\'])(.+?)\1", SRC)
    key_values = [key for _, key in keys]
    assert len(key_values) == len(set(key_values)), "All st.button keys must be unique"


def test_css_not_hiding_buttons() -> None:
    forbidden = re.compile(
        r"display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0|pointer-events\s*:\s*none",
        re.IGNORECASE,
    )
    assert not forbidden.search(SRC), "CSS must not hide/disable buttons"


def test_no_early_return_before_sidebar() -> None:
    sidebar_pos = SRC.find("with st.sidebar")
    return_match = re.search(r"^[ \t]*return\b", SRC, flags=re.MULTILINE)
    assert sidebar_pos != -1, "Missing 'with st.sidebar' block"
    assert not return_match or return_match.start() > sidebar_pos, (
        "Found a top-level 'return' before the sidebar block"
    )


def test_no_empty_on_sidebar() -> None:
    pattern = re.compile(r"\.empty\s*\(", re.IGNORECASE)
    assert not pattern.search(SRC), "Do not call .empty(); it may wipe sidebar content"
