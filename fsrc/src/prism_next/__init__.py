"""Prism FSRC scaffold package.

Wave 1 intentionally provides additive, default-off seams only.
"""

from .extension_seam import (
    FSRC_EXTENSION_SEAM_ENABLED_ENV_VAR,
    is_fsrc_extension_seam_enabled,
    maybe_call_extension_processors,
)

__all__ = [
    "FSRC_EXTENSION_SEAM_ENABLED_ENV_VAR",
    "is_fsrc_extension_seam_enabled",
    "maybe_call_extension_processors",
]
