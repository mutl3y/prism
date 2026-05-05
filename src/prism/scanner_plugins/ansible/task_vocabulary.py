"""Ansible task-keyword vocabulary.

Canonical home for the bare (non-FQCN) Ansible task keyword sets used by
the Ansible default policy plugins. The FQCN-inclusive supersets live in
`scanner_plugins.ansible.task_traversal_bare` and the canonical Ansible
plugin (`scanner_plugins.ansible.extract_policies`).
"""

from __future__ import annotations

from prism.scanner_plugins.ansible.task_keywords import (
    TASK_BLOCK_KEYS as TASK_BLOCK_KEYS,
)
from prism.scanner_plugins.ansible.task_keywords import TASK_META_KEYS as TASK_META_KEYS

TASK_INCLUDE_KEYS: frozenset[str] = frozenset(
    {
        "include_tasks",
        "import_tasks",
    }
)
ROLE_INCLUDE_KEYS: frozenset[str] = frozenset(
    {
        "include_role",
        "import_role",
    }
)
INCLUDE_VARS_KEYS: frozenset[str] = frozenset({"include_vars"})
SET_FACT_KEYS: frozenset[str] = frozenset({"set_fact"})


__all__ = [
    "INCLUDE_VARS_KEYS",
    "ROLE_INCLUDE_KEYS",
    "SET_FACT_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_INCLUDE_KEYS",
    "TASK_META_KEYS",
]
