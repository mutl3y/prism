"""Constants and compiled regex patterns for default policy implementations."""

from __future__ import annotations

import re

from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
    DEFAULT_DOC_MARKER_PREFIX,
)

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

COMMENT_CONTINUATION_RE = re.compile(r"^\s*#\s?(.*)$")
COMMENTED_TASK_ENTRY_RE = re.compile(r"^\s*-\s+name:\s*\S")
TASK_ENTRY_RE = re.compile(r"^\s*-\s+name:\s*\S")
YAML_LIKE_KEY_VALUE_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_-]*\s*:\s*\S")
YAML_LIKE_LIST_ITEM_RE = re.compile(r"^\s*-\s+[A-Za-z_][A-Za-z0-9_-]*\s*:\s*\S")

WHEN_IN_LIST_RE = re.compile(
    r"^\s*(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s+in\s+(?P<values>\[[^\]]*\])\s*$"
)
TEMPLATED_INCLUDE_RE = re.compile(
    r"^\s*(?P<prefix>[^{}]*)\{\{\s*(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*\}\}(?P<suffix>[^{}]*)\s*$"
)

__all__ = [
    "COMMENT_CONTINUATION_RE",
    "COMMENTED_TASK_ENTRY_RE",
    "DEFAULT_DOC_MARKER_PREFIX",
    "INCLUDE_VARS_KEYS",
    "ROLE_INCLUDE_KEYS",
    "SET_FACT_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_ENTRY_RE",
    "TASK_INCLUDE_KEYS",
    "TASK_META_KEYS",
    "TEMPLATED_INCLUDE_RE",
    "WHEN_IN_LIST_RE",
    "YAML_LIKE_KEY_VALUE_RE",
    "YAML_LIKE_LIST_ITEM_RE",
]
