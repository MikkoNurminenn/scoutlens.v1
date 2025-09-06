#!/usr/bin/env python3
"""Repo cleaner utility.

- Builds a file dependency graph based on AST imports.
- Detects orphan ``.py`` files (no other internal module imports them).
- Finds common build/cleanup artefacts.
- Moves all candidate files/directories to a timestamped backup folder.
- Optionally deletes the backup folder when ``--delete`` flag is provided.
- Prints a report of moved and ambiguous files.
"""

from __future__ import annotations

import argparse
import ast
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

# Patterns for cleanup artefacts
DIR_PATTERNS = {
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "dist",
    "build",
    ".ipynb_checkpoints",
    ".idea",
    ".vscode",
}
FILE_PATTERNS = {
    ".DS_Store",
}
SUFFIX_PATTERNS = {
    ".pyc",
    ".pyo",
}


def module_name_from_path(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    parts = list(rel.parts)
    parts[-1] = parts[-1][:-3]  # remove .py
    module = ".".join(parts)
    if module.endswith(".__init__"):
        module = module[: -len(".__init__")]
    return module


def build_module_map(root: Path) -> Tuple[Dict[str, Path], List[Path]]:
    module_map: Dict[str, Path] = {}
    py_files: List[Path] = []
    for path in root.rglob("*.py"):
        if path.name == "repo_cleaner.py":
            continue
        if any(part.startswith("backup_") for part in path.parts):
            continue
        module = module_name_from_path(root, path)
        module_map[module] = path
        py_files.append(path)
    return module_map, py_files


def resolve_imports(path: Path, current_module: str) -> Tuple[Optional[Set[str]], Optional[str]]:
    imports: Set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return None, f"SyntaxError: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            level = node.level or 0
            module_part = node.module or ""
            parent_parts = current_module.split(".")
            base_parts = parent_parts[:-level] if level else parent_parts
            base = ".".join(base_parts)
            if module_part:
                full_module = f"{base}.{module_part}" if base else module_part
            else:
                full_module = base
            for alias in node.names:
                if alias.name == "*":
                    imports.add(full_module)
                else:
                    target = f"{full_module}.{alias.name}" if full_module else alias.name
                    imports.add(target)
    return imports, None


def match_internal_module(module: str, module_map: Dict[str, Path]) -> Optional[Path]:
    parts = module.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in module_map:
            return module_map[candidate]
    return None


def find_orphans(root: Path) -> Tuple[List[Path], List[str]]:
    module_map, py_files = build_module_map(root)
    dependents: Dict[Path, Set[Path]] = {p: set() for p in py_files}
    ambiguous: List[str] = []

    for path in py_files:
        module = module_name_from_path(root, path)
        imports, error = resolve_imports(path, module)
        if imports is None:
            ambiguous.append(str(path.relative_to(root)))
            continue
        for imp in imports:
            target = match_internal_module(imp, module_map)
            if target and target != path:
                dependents[target].add(path)

    orphans = [p for p, deps in dependents.items() if not deps and p.name != "__init__.py"]
    return orphans, ambiguous


def find_artefacts(root: Path) -> List[Path]:
    artefacts: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        if any(part.startswith("backup_") for part in current.relative_to(root).parts):
            dirnames[:] = []
            continue
        # Directory artefacts
        for d in list(dirnames):
            if d in DIR_PATTERNS or d.endswith(".egg-info"):
                artefacts.append(current / d)
                dirnames.remove(d)
        # File artefacts
        for f in filenames:
            if f in FILE_PATTERNS or any(f.endswith(suf) for suf in SUFFIX_PATTERNS):
                artefacts.append(current / f)
    return artefacts


def move_candidates(root: Path, candidates: Iterable[Path], backup_dir: Path) -> List[Path]:
    moved: List[Path] = []
    for path in candidates:
        rel = path.relative_to(root)
        dest = backup_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))
        moved.append(rel)
    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean repository and move artefacts to backup.")
    parser.add_argument("--delete", action="store_true", help="Delete backup after moving candidates")
    args = parser.parse_args()

    root = Path.cwd()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = root / f"backup_{timestamp}"

    orphans, ambiguous = find_orphans(root)
    artefacts = find_artefacts(root)
    candidates = orphans + artefacts

    moved = move_candidates(root, candidates, backup_dir)

    print("Moved the following files/directories:")
    for p in moved:
        print(f"  {p}")

    if ambiguous:
        print("\nAmbiguous Python files (not moved):")
        for p in ambiguous:
            print(f"  {p}")
    else:
        print("\nNo ambiguous Python files detected.")

    if args.delete:
        shutil.rmtree(backup_dir, ignore_errors=True)
        print(f"\nBackup directory {backup_dir.name} deleted.")
    else:
        print(f"\nBackup directory created at {backup_dir}.")


if __name__ == "__main__":
    main()
