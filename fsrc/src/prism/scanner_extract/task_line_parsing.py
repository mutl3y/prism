"""Task-file line parsing constants and marker helpers for fsrc."""

from __future__ import annotations

import re

import yaml

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

DEFAULT_DOC_MARKER_PREFIX = "prism"


def _normalize_marker_prefix(marker_prefix: str | None) -> str:
    if not isinstance(marker_prefix, str):
        return DEFAULT_DOC_MARKER_PREFIX
    prefix = marker_prefix.strip()
    if not prefix:
        return DEFAULT_DOC_MARKER_PREFIX
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
        return DEFAULT_DOC_MARKER_PREFIX
    return prefix


def _build_marker_line_re(marker_prefix: str):
    escaped_prefix = re.escape(_normalize_marker_prefix(marker_prefix))
    return re.compile(
        rf"^\s*#\s*{escaped_prefix}\s*~\s*(?P<label>[a-z0-9_-]+)\s*:?\s*(?P<body>.*)$",
        flags=re.IGNORECASE,
    )


def get_marker_line_re(marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX):
    return _build_marker_line_re(marker_prefix)


ROLE_NOTES_RE = _build_marker_line_re(DEFAULT_DOC_MARKER_PREFIX)
TASK_NOTES_LONG_RE = _build_marker_line_re(DEFAULT_DOC_MARKER_PREFIX)
ROLE_NOTES_SHORT_RE = ROLE_NOTES_RE
TASK_NOTES_SHORT_RE = TASK_NOTES_LONG_RE
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


def _extract_constrained_when_values(task: dict, variable: str) -> list[str]:
    when_value = task.get("when")
    conditions: list[str] = []
    if isinstance(when_value, str):
        conditions.append(when_value)
    elif isinstance(when_value, list):
        conditions.extend(item for item in when_value if isinstance(item, str))

    values: list[str] = []
    for condition in conditions:
        match = WHEN_IN_LIST_RE.match(condition.strip())
        if not match:
            continue
        if (match.group("var") or "").strip() != variable:
            continue
        parsed = yaml.safe_load(match.group("values"))
        if not isinstance(parsed, list):
            continue
        for item in parsed:
            if isinstance(item, str):
                values.append(item)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
