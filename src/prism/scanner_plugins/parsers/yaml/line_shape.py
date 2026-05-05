"""YAML line-shape regex patterns.

Platform-neutral patterns describing YAML surface shape: named list items
(``- name: value``), key/value lines, and list-item-mapping lines. These
are syntax-level regex shared by the comment-driven documentation parser
and Ansible default policy plugins; they make no Ansible-specific
keyword assumptions.
"""

from __future__ import annotations

import re

TASK_ENTRY_RE = re.compile(r"^\s*-\s+name:\s*\S")
YAML_LIKE_KEY_VALUE_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_-]*\s*:\s*\S")
YAML_LIKE_LIST_ITEM_RE = re.compile(r"^\s*-\s+[A-Za-z_][A-Za-z0-9_-]*\s*:\s*\S")

__all__ = [
    "TASK_ENTRY_RE",
    "YAML_LIKE_KEY_VALUE_RE",
    "YAML_LIKE_LIST_ITEM_RE",
]
