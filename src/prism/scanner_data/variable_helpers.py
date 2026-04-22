"""Shared variable-row helper utilities for scanner data shaping.

These helpers are consumed by scanner plugins and scanner_core.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from yaml import safe_dump

from prism.scanner_data.contracts_variables import VariableRow


def infer_variable_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if value is None:
        return "none"
    return "str"


def format_inline_yaml(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    rendered = safe_dump(value, default_flow_style=True).strip()
    return rendered.replace("\n...", "")


def is_sensitive_variable(name: str, value: Any) -> bool:
    lowered_name = name.lower()
    return any(
        token in lowered_name for token in ("password", "secret", "token", "key")
    )


def find_variable_line_in_yaml(path: Path | None, name: str) -> int | None:
    if path is None or not path.exists():
        return None
    pattern = re.compile(rf"^\s*{re.escape(name)}\s*:")
    try:
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if pattern.search(line):
                return line_no
    except OSError:
        return None
    return None


def build_static_variable_rows(
    *,
    role_root: Path,
    defaults_data: dict[str, Any],
    vars_data: dict[str, Any],
    defaults_sources: dict[str, Path],
    vars_sources: dict[str, Path],
) -> tuple[list[VariableRow], dict[str, VariableRow]]:
    """Build baseline rows from defaults/main.yml and vars/main.yml data."""
    rows: list[VariableRow] = []
    rows_by_name: dict[str, VariableRow] = {}

    for name in sorted(set(defaults_data) | set(vars_data)):
        has_default = name in defaults_data
        has_var = name in vars_data
        value = vars_data[name] if has_var else defaults_data.get(name)
        default_source_file = defaults_sources.get(name)
        vars_source_file = vars_sources.get(name)

        source = "defaults/main.yml"
        provenance_source_file = "defaults/main.yml"
        provenance_line = find_variable_line_in_yaml(default_source_file, name)
        provenance_confidence = 0.95
        uncertainty_reason: str | None = None
        is_ambiguous = False

        if default_source_file is not None:
            provenance_source_file = str(default_source_file.relative_to(role_root))

        if has_var and has_default:
            source = "defaults/main.yml + vars/main.yml override"
            provenance_source_file = (
                str(vars_source_file.relative_to(role_root))
                if vars_source_file is not None
                else "vars/main.yml"
            )
            provenance_line = find_variable_line_in_yaml(vars_source_file, name)
            provenance_confidence = 0.80
            uncertainty_reason = (
                "Defaults value is superseded by vars/main.yml precedence "
                "(informational)."
            )
            is_ambiguous = True
        elif has_var:
            source = "vars/main.yml"
            provenance_source_file = (
                str(vars_source_file.relative_to(role_root))
                if vars_source_file is not None
                else "vars/main.yml"
            )
            provenance_line = find_variable_line_in_yaml(vars_source_file, name)
            provenance_confidence = 0.90

        row: VariableRow = {
            "name": name,
            "type": infer_variable_type(value),
            "default": format_inline_yaml(value),
            "source": source,
            "documented": True,
            "required": False,
            "secret": is_sensitive_variable(name, value),
            "provenance_source_file": provenance_source_file,
            "provenance_line": provenance_line,
            "provenance_confidence": provenance_confidence,
            "uncertainty_reason": uncertainty_reason,
            "is_unresolved": False,
            "is_ambiguous": is_ambiguous,
        }
        rows.append(row)
        rows_by_name[name] = row

    return rows, rows_by_name


JINJA_IDENTIFIER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")


def collect_dynamic_include_var_tokens(
    dynamic_include_vars_refs: list[str],
    ignored_identifiers: set[str] | frozenset[str] | None = None,
) -> set[str]:
    """Collect unresolved Jinja identifier tokens from dynamic include_vars refs."""
    effective_ignored = (
        set() if ignored_identifiers is None else set(ignored_identifiers)
    )
    tokens: set[str] = set()
    for ref in dynamic_include_vars_refs:
        tokens.update(
            token
            for token in JINJA_IDENTIFIER_RE.findall(ref)
            if token.lower() not in effective_ignored
        )
    return tokens
