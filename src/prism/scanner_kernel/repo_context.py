"""Repo-level context graph helpers for scanner kernel orchestration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

import yaml


CONTEXT_VERSION = "1.0"
KERNEL_ENABLED_ENV_VAR = "PRISM_KERNEL_ENABLED"
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})


class RepoCrossRoleContext(TypedDict):
    """Typed repo context payload used by kernel plugin orchestration."""

    repo_url: str
    repo_ref: str
    role_paths: list[str]
    shared_variable_names: list[str]
    role_variable_index: dict[str, list[str]]
    context_version: str


def build_repo_context_graph(
    role_paths: list[str],
    repo_url: str = "",
    repo_ref: str = "",
) -> RepoCrossRoleContext | None:
    """Build sparse cross-role variable context graph when kernel is enabled."""
    if not is_kernel_enabled():
        return None

    role_variable_index: dict[str, list[str]] = {
        role_path: discover_role_variable_names(role_path) for role_path in role_paths
    }
    all_names: list[str] = []
    for names in role_variable_index.values():
        all_names.extend(names)

    counts: dict[str, int] = {}
    for name in all_names:
        counts[name] = counts.get(name, 0) + 1

    shared = sorted(name for name, count in counts.items() if count > 1)

    return {
        "repo_url": repo_url,
        "repo_ref": repo_ref,
        "role_paths": list(role_paths),
        "shared_variable_names": shared,
        "role_variable_index": role_variable_index,
        "context_version": CONTEXT_VERSION,
    }


def is_kernel_enabled() -> bool:
    return os.environ.get(KERNEL_ENABLED_ENV_VAR, "").lower() in _TRUTHY_VALUES


def discover_role_variable_names(role_path: str) -> list[str]:
    variable_names: list[str] = []
    for subdir in ("defaults", "vars"):
        dir_path = Path(role_path) / subdir
        if not dir_path.is_dir():
            continue
        for yml_file in sorted(dir_path.glob("*.yml")):
            variable_names.extend(_scan_yaml_keys(yml_file))
    return variable_names


def _scan_yaml_keys(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return []

    if not isinstance(data, dict):
        return []

    return [k for k in data if isinstance(k, str) and k.isidentifier()]


__all__ = [
    "build_repo_context_graph",
    "RepoCrossRoleContext",
    "CONTEXT_VERSION",
    "is_kernel_enabled",
    "discover_role_variable_names",
]
