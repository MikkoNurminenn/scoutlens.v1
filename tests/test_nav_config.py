"""Consistency checks for sidebar navigation configuration."""

from __future__ import annotations

import ast
from pathlib import Path


APP_MODULE = Path(__file__).resolve().parents[1] / "app" / "app.py"


def _load_nav_config() -> dict[str, object]:
    """Parse ``app/app.py`` and extract navigation-related constants."""

    tree = ast.parse(APP_MODULE.read_text(encoding="utf-8"))
    desired = {"NAV_KEYS", "NAV_LABELS", "NAV_ICONS", "LEGACY_REMAP", "PAGE_FUNCS"}
    values: dict[str, object] = {}

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in desired:
                values[target.id] = node.value

    def _const_list(list_node: ast.AST) -> list[str]:
        if not isinstance(list_node, (ast.List, ast.Tuple)):
            raise AssertionError("Expected list/tuple literal")
        result = []
        for elt in list_node.elts:  # type: ignore[attr-defined]
            if not isinstance(elt, ast.Constant) or not isinstance(elt.value, str):
                raise AssertionError("Navigation keys must be string literals")
            result.append(elt.value)
        return result

    def _const_dict(dict_node: ast.AST) -> dict[str, str]:
        if not isinstance(dict_node, ast.Dict):
            raise AssertionError("Expected dict literal")
        result: dict[str, str] = {}
        for key, value in zip(dict_node.keys, dict_node.values, strict=True):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                raise AssertionError("Navigation mapping keys must be strings")
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                raise AssertionError("Navigation mapping values must be strings")
            result[key.value] = value.value
        return result

    def _dict_keys(dict_node: ast.AST) -> list[str]:
        if not isinstance(dict_node, ast.Dict):
            raise AssertionError("Expected dict literal")
        keys: list[str] = []
        for key in dict_node.keys:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                raise AssertionError("Navigation mapping keys must be strings")
            keys.append(key.value)
        return keys

    return {
        "NAV_KEYS": _const_list(values["NAV_KEYS"]),
        "NAV_LABELS": _const_dict(values["NAV_LABELS"]),
        "NAV_ICONS": _const_dict(values["NAV_ICONS"]),
        "LEGACY_REMAP": _const_dict(values["LEGACY_REMAP"]),
        "PAGE_FUNCS_KEYS": _dict_keys(values["PAGE_FUNCS"]),
    }


def test_nav_config_has_no_conflicts():
    config = _load_nav_config()

    nav_keys = config["NAV_KEYS"]
    nav_key_set = set(nav_keys)

    assert len(nav_keys) == len(nav_key_set), "NAV_KEYS contains duplicates"

    assert set(config["NAV_LABELS"]) == nav_key_set, "Missing NAV_LABELS entries"
    assert set(config["NAV_ICONS"]) == nav_key_set, "Missing NAV_ICONS entries"
    assert set(config["PAGE_FUNCS_KEYS"]) == nav_key_set, "Missing PAGE_FUNCS entries"

    legacy_targets = set(config["LEGACY_REMAP"].values())
    assert legacy_targets <= nav_key_set, "LEGACY_REMAP points to unknown pages"

