"""Style guide configuration and alias management for the fsrc lane."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from types import MappingProxyType
from typing import Any


_STYLE_SECTION_ALIASES: dict[str, str] = {
    "galaxy info": "galaxy_info",
    "requirements": "requirements",
    "role purpose and capabilities": "purpose",
    "role notes": "role_notes",
    "inputs variables summary": "variable_summary",
    "task module usage summary": "task_summary",
    "inferred example usage": "example_usage",
    "role variables": "role_variables",
    "role contents summary": "role_contents",
    "auto detected role features": "features",
    "comparison against local baseline role": "comparison",
    "detected usages of the default() filter": "default_filters",
    "scanner report": "scanner_report",
}

STYLE_SECTION_ALIASES: Mapping[str, str] = MappingProxyType(_STYLE_SECTION_ALIASES)
_SECTION_ALIAS_OVERRIDE: ContextVar[dict[str, str] | None] = ContextVar(
    "prism_style_section_alias_override",
    default=None,
)


@contextmanager
def style_section_aliases_scope(section_aliases: dict[str, str] | None):
    """Apply request-scoped style aliases for style parsing and rendering."""
    token: Token[dict[str, str] | None] = _SECTION_ALIAS_OVERRIDE.set(section_aliases)
    try:
        yield
    finally:
        _SECTION_ALIAS_OVERRIDE.reset(token)


def get_style_section_aliases_snapshot() -> dict[str, str]:
    """Return a stable alias snapshot for callers that require read consistency."""
    scoped_aliases = _SECTION_ALIAS_OVERRIDE.get()
    if isinstance(scoped_aliases, dict):
        return dict(scoped_aliases)
    return dict(_STYLE_SECTION_ALIASES)


def refresh_policy_derived_state(policy: dict[str, Any]) -> None:
    """Refresh module-level policy state after scanner policy reloads."""
    section_aliases = policy.get("section_aliases")
    if isinstance(section_aliases, dict):
        _STYLE_SECTION_ALIASES.clear()
        _STYLE_SECTION_ALIASES.update(
            {
                str(key): str(value)
                for key, value in section_aliases.items()
                if isinstance(key, str) and isinstance(value, str)
            }
        )
