"""Ansible-specific regex patterns and constants.

Located in ``scanner_plugins.ansible`` as the single authoritative source
for Ansible extraction constants. Imported by variable_discovery and
extract_utils to avoid circular delegation.
"""

from __future__ import annotations

from prism.scanner_data.patterns_jinja import JINJA_IDENTIFIER_RE

__all__ = [
    "JINJA_IDENTIFIER_RE",
]
