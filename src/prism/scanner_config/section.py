"""Section configuration constants and metadata.

This module defines the filenames and markers used for README section
configuration within Ansible roles.
"""

from __future__ import annotations

DEFAULT_DOC_MARKER_PREFIX = "prism"
SECTION_CONFIG_FILENAME = ".prism.yml"
SECTION_CONFIG_FILENAMES = (SECTION_CONFIG_FILENAME,)

__all__ = [
    "DEFAULT_DOC_MARKER_PREFIX",
    "SECTION_CONFIG_FILENAME",
    "SECTION_CONFIG_FILENAMES",
]
