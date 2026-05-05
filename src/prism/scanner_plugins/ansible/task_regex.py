"""Ansible-syntax compiled regex patterns.

Patterns here express Ansible-specific surface syntax (Jinja-templated
include targets, in-list ``when`` constraints). YAML-shape patterns
(named-list-item, key/value, list-item shape) live in
``scanner_plugins.parsers.yaml.line_shape``.
"""

from __future__ import annotations

import re

WHEN_IN_LIST_RE = re.compile(
    r"^\s*(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s+in\s+(?P<values>\[[^\]]*\])\s*$"
)
TEMPLATED_INCLUDE_RE = re.compile(
    r"^\s*(?P<prefix>[^{}]*)\{\{\s*(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*\}\}(?P<suffix>[^{}]*)\s*$"
)

__all__ = [
    "TEMPLATED_INCLUDE_RE",
    "WHEN_IN_LIST_RE",
]
