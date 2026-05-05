"""Ansible task-structure keywords shared by bare and FQCN-inclusive key sets.

Block structural keys and task metadata keys have no FQCN variants —
`TASK_BLOCK_KEYS` and `TASK_META_KEYS` are identical in both the bare
vocabulary layer and the FQCN-inclusive traversal layer.  Canonical
definition lives here; both consumers re-export without modification.
"""

from __future__ import annotations

TASK_BLOCK_KEYS: tuple[str, ...] = ("block", "rescue", "always")
TASK_META_KEYS: frozenset[str] = frozenset(
    {
        "name",
        "when",
        "tags",
        "register",
        "notify",
        "vars",
        "become",
        "become_user",
        "become_method",
        "check_mode",
        "changed_when",
        "failed_when",
        "ignore_errors",
        "ignore_unreachable",
        "delegate_to",
        "run_once",
        "loop",
        "loop_control",
        "with_items",
        "with_dict",
        "with_fileglob",
        "with_first_found",
        "with_nested",
        "with_sequence",
        "environment",
        "args",
        "retries",
        "delay",
        "until",
        "throttle",
        "no_log",
    }
)

__all__ = [
    "TASK_BLOCK_KEYS",
    "TASK_META_KEYS",
]
