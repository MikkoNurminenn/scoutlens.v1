#!/usr/bin/env python3
"""Pre-commit hook to block direct ``st.sidebar`` usage outside the sidebar module."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_FILES = {REPO_ROOT / "app" / "ui" / "sidebar.py"}


def _resolve_paths(args: Sequence[str]) -> List[Path]:
    if args:
        resolved: List[Path] = []
        for raw in args:
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = REPO_ROOT / candidate
            if candidate.exists():
                resolved.append(candidate)
        return resolved

    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [REPO_ROOT / Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def _find_violations(paths: Iterable[Path]) -> List[str]:
    violations: List[str] = []
    for path in paths:
        if path in ALLOWED_FILES:
            continue
        if not path.exists() or path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            continue

        lines: List[str] = text.splitlines()
        matches: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "st"
                    and node.attr == "sidebar"
                ):
                    lineno = getattr(node, "lineno", None)
                    if lineno is None:
                        continue
                    source_line = lines[lineno - 1].strip() if lineno - 1 < len(lines) else ""
                    matches.append(f"  line {lineno}: {source_line}")

        if matches:
            rel_path = path.relative_to(REPO_ROOT)
            violations.append(f"{rel_path}:\n" + "\n".join(matches))
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    paths = _resolve_paths(args)
    violations = _find_violations(paths)
    if violations:
        message = [
            "Direct st.sidebar usage is restricted to app/ui/sidebar.py.",
            "Update your code to use the centralized sidebar API.",
            "Violations detected:",
            *violations,
        ]
        print("\n".join(message), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
