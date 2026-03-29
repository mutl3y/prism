"""Public legacy-retirement error contract definitions.

This module centralizes user-facing legacy retirement codes/messages so
scanner and config loaders emit a consistent contract.
"""

from __future__ import annotations

LEGACY_SECTION_CONFIG_FILENAME = ".ansible_role_doc.yml"
LEGACY_RUNTIME_STYLE_SOURCE_ENV = "ANSIBLE_ROLE_DOC_STYLE_SOURCE"

LEGACY_SECTION_CONFIG_UNSUPPORTED = "LEGACY_SECTION_CONFIG_UNSUPPORTED"
LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE = (
    "Legacy section config file `.ansible_role_doc.yml` is no longer supported. "
    "Rename or migrate to `.prism.yml`."
)

LEGACY_RUNTIME_PATH_UNAVAILABLE = "LEGACY_RUNTIME_PATH_UNAVAILABLE"
LEGACY_RUNTIME_PATH_UNAVAILABLE_MESSAGE = (
    "Legacy ansible_role_doc compatibility path has been retired. "
    "Use canonical Prism behavior."
)


def format_legacy_retirement_error(code: str, message: str) -> str:
    """Return the stable public error payload for legacy retirement checks."""
    return f"{code}: {message}"


__all__ = [
    "LEGACY_SECTION_CONFIG_FILENAME",
    "LEGACY_RUNTIME_STYLE_SOURCE_ENV",
    "LEGACY_SECTION_CONFIG_UNSUPPORTED",
    "LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE",
    "LEGACY_RUNTIME_PATH_UNAVAILABLE",
    "LEGACY_RUNTIME_PATH_UNAVAILABLE_MESSAGE",
    "format_legacy_retirement_error",
]
