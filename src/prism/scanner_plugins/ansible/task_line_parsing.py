"""Ansible-owned task-line parsing constants and helpers for fsrc."""

from __future__ import annotations

from prism.scanner_plugins.ansible.task_traversal_bare import (
    TEMPLATED_INCLUDE_RE,
    WHEN_IN_LIST_RE,
    extract_constrained_when_values,
)

TASK_INCLUDE_KEYS = {
    "include_tasks",
    "import_tasks",
    "ansible.builtin.include_tasks",
    "ansible.builtin.import_tasks",
}
ROLE_INCLUDE_KEYS = {
    "include_role",
    "import_role",
    "ansible.builtin.include_role",
    "ansible.builtin.import_role",
}
INCLUDE_VARS_KEYS = {"include_vars", "ansible.builtin.include_vars"}
SET_FACT_KEYS = {"set_fact", "ansible.builtin.set_fact"}
TASK_BLOCK_KEYS = ("block", "rescue", "always")
TASK_META_KEYS = {
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


def detect_task_module(task: dict) -> str | None:
    for include_key in TASK_INCLUDE_KEYS:
        if include_key in task:
            if "import_tasks" in include_key:
                return "import_tasks"
            return "include_tasks"

    for include_key in ROLE_INCLUDE_KEYS:
        if include_key in task:
            if "import_role" in include_key:
                return "import_role"
            return "include_role"

    for key in task:
        if key in TASK_META_KEYS or key in TASK_BLOCK_KEYS:
            continue
        if key.startswith("with_"):
            continue
        return key
    return None


__all__ = [
    "INCLUDE_VARS_KEYS",
    "ROLE_INCLUDE_KEYS",
    "SET_FACT_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_INCLUDE_KEYS",
    "WHEN_IN_LIST_RE",
    "TASK_META_KEYS",
    "TEMPLATED_INCLUDE_RE",
    "detect_task_module",
    "extract_constrained_when_values",
]
