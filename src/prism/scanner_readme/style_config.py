"""Style guide configuration and alias management for the fsrc lane."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from types import MappingProxyType
from typing import Any

from prism.scanner_data.style_aliases import (
    get_default_style_section_aliases_snapshot,
)

_STYLE_SECTION_ALIASES: dict[str, str] = get_default_style_section_aliases_snapshot()


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
    """Refresh module-level policy state after scanner policy reloads.

    WARNING: This function mutates global module state in-place (.clear + .update)
    and is NOT thread-safe. Concurrent calls or reads during refresh may observe
    a partially-updated alias table. Intended for single-threaded scanner execution
    only. The public STYLE_SECTION_ALIASES MappingProxyType reflects changes
    immediately since it wraps the same underlying dict.
    """
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
