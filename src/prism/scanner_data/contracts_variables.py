"""Minimal variable contracts for fsrc scanner-core migration slices."""

from __future__ import annotations

from typing import Any, TypedDict


class VariableRow(TypedDict):
    """Canonical variable insight row shape used by fsrc scanner core."""

    name: str
    type: str
    default: str
    source: str
    documented: bool
    required: bool
    secret: bool
    provenance_source_file: str | None
    provenance_line: int | None
    provenance_confidence: float
    uncertainty_reason: str | None
    is_unresolved: bool
    is_ambiguous: bool


class ReferenceContext(TypedDict):
    """Reference-context payload for inferred variable row construction."""

    seed_values: dict[str, Any]
    seed_secrets: set[str]
    seed_sources: dict[str, str]
    dynamic_include_vars_refs: list[str]
    dynamic_include_var_tokens: set[str]
    dynamic_task_include_tokens: set[str]
    referenced_names: set[str]
