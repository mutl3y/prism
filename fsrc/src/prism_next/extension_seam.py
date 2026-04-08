"""Default-off extension seam for Prism FSRC scaffolding.

This seam is additive and intentionally inert unless explicitly enabled.
"""

from __future__ import annotations

import os
from typing import Any

from prism.scanner_core.extension_registry import ExtensionRegistry, HookPoint

FSRC_EXTENSION_SEAM_ENABLED_ENV_VAR: str = "PRISM_FSRC_EXTENSION_SEAM_ENABLED"

_TRUTHY = {"1", "true", "yes", "on"}


def is_fsrc_extension_seam_enabled() -> bool:
    """Return True only when the explicit FSRC seam flag is truthy."""
    raw = os.getenv(FSRC_EXTENSION_SEAM_ENABLED_ENV_VAR, "")
    return raw.strip().lower() in _TRUTHY


def maybe_call_extension_processors(
    registry: ExtensionRegistry,
    hook_point: HookPoint,
    *args: Any,
    **kwargs: Any,
) -> list[Any]:
    """Call extension processors only when the FSRC seam is explicitly enabled."""
    if not is_fsrc_extension_seam_enabled():
        return []
    return registry.call_processors(hook_point, *args, **kwargs)
