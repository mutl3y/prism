"""Ansible-owned task-traversal primitives.

Traversal, include-target expansion, and dynamic-include collection using
Ansible FQCN-inclusive key sets.  These helpers are Ansible-specific; they
depend on the Ansible key constants imported below.
"""

from __future__ import annotations

from typing import Any

import yaml

from prism.scanner_plugins.policies.constants import (
    ROLE_INCLUDE_KEYS,
    TASK_BLOCK_KEYS,
    TASK_INCLUDE_KEYS,
    TASK_META_KEYS,
    TEMPLATED_INCLUDE_RE,
    WHEN_IN_LIST_RE,
)


def extract_constrained_when_values(task: dict, variable: str) -> list[str]:
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


def iter_task_mappings(data: object):
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            yield item
            for key in TASK_BLOCK_KEYS:
                nested = item.get(key)
                if nested is not None:
                    yield from iter_task_mappings(nested)


def expand_include_target_candidates(task: dict, include_target: str) -> list[str]:
    candidate = include_target.strip()
    if not candidate:
        return []
    if "{{" not in candidate and "{%" not in candidate:
        return [candidate]

    match = TEMPLATED_INCLUDE_RE.match(candidate)
    if not match:
        return []

    variable = (match.group("var") or "").strip()
    if not variable:
        return []
    allowed_values = extract_constrained_when_values(task, variable)
    if not allowed_values:
        return []

    prefix = (match.group("prefix") or "").strip()
    suffix = (match.group("suffix") or "").strip()
    return [f"{prefix}{value}{suffix}" for value in allowed_values]


def iter_task_include_targets(
    data: object,
    *,
    task_include_keys: set[str] | frozenset[str] = TASK_INCLUDE_KEYS,
) -> list[str]:
    targets: list[str] = []
    for task in iter_task_mappings(data):
        for key in task_include_keys:
            if key not in task:
                continue
            value = task[key]
            if isinstance(value, str):
                expanded = expand_include_target_candidates(task, value)
                if expanded:
                    targets.extend(expanded)
                else:
                    candidate = value.strip()
                    if candidate:
                        targets.append(candidate)
            elif isinstance(value, dict):
                file_value = value.get("file") or value.get("_raw_params")
                if isinstance(file_value, str):
                    expanded = expand_include_target_candidates(task, file_value)
                    if expanded:
                        targets.extend(expanded)
                    else:
                        candidate = file_value.strip()
                        if candidate:
                            targets.append(candidate)
    return targets


def iter_task_include_edges(
    data: object,
    *,
    task_include_keys: set[str] | frozenset[str] = TASK_INCLUDE_KEYS,
) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for task in iter_task_mappings(data):
        for key in task_include_keys:
            if key not in task:
                continue
            value = task[key]
            module_name = "import_tasks" if "import_tasks" in key else "include_tasks"
            if isinstance(value, str):
                expanded = expand_include_target_candidates(task, value)
                if expanded:
                    for candidate in expanded:
                        edges.append({"module": module_name, "target": candidate})
                else:
                    candidate = value.strip()
                    if candidate:
                        edges.append({"module": module_name, "target": candidate})
            elif isinstance(value, dict):
                file_value = value.get("file") or value.get("_raw_params")
                if not isinstance(file_value, str):
                    continue
                expanded = expand_include_target_candidates(task, file_value)
                if expanded:
                    for candidate in expanded:
                        edges.append({"module": module_name, "target": candidate})
                else:
                    candidate = file_value.strip()
                    if candidate:
                        edges.append({"module": module_name, "target": candidate})
    return edges


def iter_role_include_targets(
    task: dict,
    *,
    role_include_keys: set[str] | frozenset[str] = ROLE_INCLUDE_KEYS,
) -> list[str]:
    role_targets: list[str] = []
    for key in role_include_keys:
        if key not in task:
            continue
        value = task[key]
        ref: str | None = None
        if isinstance(value, str):
            ref = value
        elif isinstance(value, dict):
            candidate = value.get("name") or value.get("_raw_params")
            if isinstance(candidate, str):
                ref = candidate
        if not ref:
            continue
        ref = ref.strip()
        if not ref or "{{" in ref or "{%" in ref:
            continue
        role_targets.append(ref)
    return role_targets


def iter_dynamic_role_include_targets(
    task: dict,
    *,
    role_include_keys: set[str] | frozenset[str] = ROLE_INCLUDE_KEYS,
) -> list[str]:
    dynamic_targets: list[str] = []
    for key in role_include_keys:
        if key not in task:
            continue
        value = task[key]
        ref: str | None = None
        if isinstance(value, str):
            ref = value
        elif isinstance(value, dict):
            candidate = value.get("name") or value.get("_raw_params")
            if isinstance(candidate, str):
                ref = candidate
        if not ref:
            continue
        ref = ref.strip()
        if ref and ("{{" in ref or "{%" in ref):
            dynamic_targets.append(ref)
    return dynamic_targets


def collect_unconstrained_dynamic_task_includes(
    *,
    role_root: Any,
    task_files: list[Any],
    load_yaml_file,
    task_include_keys: set[str] | frozenset[str] = TASK_INCLUDE_KEYS,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for task_file in task_files:
        data = load_yaml_file(task_file)
        relpath = str(task_file.relative_to(role_root))
        for task in iter_task_mappings(data):
            task_name = str(task.get("name") or "(unnamed task)")
            for include_key in task_include_keys:
                if include_key not in task:
                    continue
                include_target = task[include_key]
                include_path: str | None = None
                if isinstance(include_target, str):
                    include_path = include_target
                elif isinstance(include_target, dict):
                    candidate = include_target.get("file") or include_target.get(
                        "_raw_params"
                    )
                    if isinstance(candidate, str):
                        include_path = candidate

                if not include_path:
                    continue
                include_path = include_path.strip()
                if "{{" not in include_path and "{%" not in include_path:
                    continue
                if expand_include_target_candidates(task, include_path):
                    continue

                findings.append(
                    {
                        "file": relpath,
                        "task": task_name,
                        "module": (
                            "import_tasks"
                            if "import_tasks" in include_key
                            else "include_tasks"
                        ),
                        "target": include_path,
                    }
                )
    return findings


def collect_unconstrained_dynamic_role_includes(
    *,
    role_root: Any,
    task_files: list[Any],
    load_yaml_file,
    role_include_keys: set[str] | frozenset[str] = ROLE_INCLUDE_KEYS,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for task_file in task_files:
        data = load_yaml_file(task_file)
        relpath = str(task_file.relative_to(role_root))
        for task in iter_task_mappings(data):
            task_name = str(task.get("name") or "(unnamed task)")
            for include_key in role_include_keys:
                if include_key not in task:
                    continue
                include_target = task[include_key]
                role_ref: str | None = None
                if isinstance(include_target, str):
                    role_ref = include_target
                elif isinstance(include_target, dict):
                    candidate = include_target.get("name") or include_target.get(
                        "_raw_params"
                    )
                    if isinstance(candidate, str):
                        role_ref = candidate

                if not role_ref:
                    continue
                role_ref = role_ref.strip()
                if "{{" not in role_ref and "{%" not in role_ref:
                    continue
                if expand_include_target_candidates(task, role_ref):
                    continue

                findings.append(
                    {
                        "file": relpath,
                        "task": task_name,
                        "module": (
                            "import_role"
                            if "import_role" in include_key
                            else "include_role"
                        ),
                        "target": role_ref,
                    }
                )
    return findings


__all__ = [
    "TEMPLATED_INCLUDE_RE",
    "WHEN_IN_LIST_RE",
    "collect_unconstrained_dynamic_role_includes",
    "collect_unconstrained_dynamic_task_includes",
    "detect_task_module",
    "expand_include_target_candidates",
    "extract_constrained_when_values",
    "iter_dynamic_role_include_targets",
    "iter_role_include_targets",
    "iter_task_include_edges",
    "iter_task_include_targets",
    "iter_task_mappings",
]
