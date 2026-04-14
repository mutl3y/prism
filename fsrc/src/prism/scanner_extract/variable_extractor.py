"""Compatibility variable extraction helpers for fsrc package export parity."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from prism.scanner_plugins.defaults import resolve_variable_extractor_policy_plugin
from prism.scanner_extract.task_file_traversal import (
    _collect_task_files,
    _load_yaml_file,
)
from prism.scanner_io.loader import load_yaml_file


def _resolve_plugin_registry(di: object | None = None):
    if di is None:
        return None
    registry = getattr(di, "plugin_registry", None)
    if registry is not None:
        return registry
    scan_options = getattr(di, "_scan_options", None)
    if isinstance(scan_options, dict):
        return scan_options.get("plugin_registry")
    return None


def _resolve_policy_with_registry(resolver, di: object | None = None):
    registry = _resolve_plugin_registry(di)
    if registry is None:
        return resolver(di)
    try:
        return resolver(di, registry=registry)
    except TypeError:
        return resolver(di)


def _get_variable_extractor_policy(di: object | None = None):
    return _resolve_policy_with_registry(resolve_variable_extractor_policy_plugin, di)


DEFAULT_TARGET_RE = re.compile(r"\b(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*\|\s*default\b")
JINJA_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)")
JINJA_IDENTIFIER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
VAULT_KEY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*!vault\b", re.MULTILINE)
IGNORED_IDENTIFIERS: set[str] = set()


def looks_secret_name(name: str) -> bool:
    token = name.lower()
    return any(marker in token for marker in ("password", "secret", "token", "key"))


def resembles_password_like(value: str) -> bool:
    candidate = value.strip().lower()
    return bool(candidate) and ("password" in candidate or candidate.startswith("$6$"))


def extract_default_target_var(text: str) -> str | None:
    match = DEFAULT_TARGET_RE.search(text or "")
    if not match:
        return None
    return match.group("var")


def collect_include_vars_files(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[Path]:
    return _get_variable_extractor_policy(di).collect_include_vars_files(
        role_path=role_path,
        exclude_paths=exclude_paths,
        collect_task_files=_collect_task_files,
        load_yaml_file=_load_yaml_file,
    )


def load_seed_variables(
    paths: list[str] | None,
    *,
    di: object | None = None,
) -> tuple[dict[str, Any], set[str], dict[str, str]]:
    seed_values: dict[str, Any] = {}
    seed_secrets: set[str] = set()
    seed_sources: dict[str, str] = {}
    if not paths:
        return seed_values, seed_secrets, seed_sources

    for raw_path in paths:
        candidate = Path(raw_path)
        if not candidate.is_file():
            continue
        try:
            loaded = load_yaml_file(candidate, di=di)
        except Exception:
            continue
        if not isinstance(loaded, dict):
            continue
        for name, value in loaded.items():
            if not isinstance(name, str):
                continue
            seed_values[name] = value
            seed_sources[name] = str(candidate)
            if looks_secret_name(name):
                seed_secrets.add(name)

    return seed_values, seed_secrets, seed_sources


def refresh_policy_derived_state(_policy: dict[str, Any]) -> None:
    """Compatibility no-op for parity with src variable extractor API."""
    return None
