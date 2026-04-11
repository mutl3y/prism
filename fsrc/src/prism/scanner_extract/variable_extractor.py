"""Compatibility variable extraction helpers for fsrc package export parity."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from prism.scanner_extract.task_line_parsing import INCLUDE_VARS_KEYS
from prism.scanner_extract.task_file_traversal import (
    _collect_task_files,
    _load_yaml_file,
)

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
) -> list[Path]:
    role_root = Path(role_path).resolve()
    include_files: set[Path] = set()
    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        data = _load_yaml_file(task_file)
        if not isinstance(data, list):
            continue
        for task in data:
            if not isinstance(task, dict):
                continue
            for key in INCLUDE_VARS_KEYS:
                if key not in task:
                    continue
                value = task.get(key)
                if isinstance(value, str):
                    include_path = (task_file.parent / value).resolve()
                    if include_path.is_file():
                        include_files.add(include_path)
                elif isinstance(value, dict):
                    file_value = value.get("file") or value.get("_raw_params")
                    if isinstance(file_value, str):
                        include_path = (task_file.parent / file_value).resolve()
                        if include_path.is_file():
                            include_files.add(include_path)
    return sorted(include_files)


def load_seed_variables(
    paths: list[str] | None,
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
            loaded = yaml.safe_load(candidate.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
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
