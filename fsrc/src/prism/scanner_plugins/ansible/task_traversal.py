"""Ansible-owned task traversal policy helpers for fsrc."""

from __future__ import annotations

from typing import Any

from prism.scanner_plugins.ansible import task_line_parsing as tlp


def _iter_task_mappings(data: object):
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            yield item
            for key in tlp.TASK_BLOCK_KEYS:
                nested = item.get(key)
                if nested is not None:
                    yield from _iter_task_mappings(nested)


def _iter_task_include_targets(data: object) -> list[str]:
    targets: list[str] = []
    for task in _iter_task_mappings(data):
        for key in tlp.TASK_INCLUDE_KEYS:
            if key not in task:
                continue
            value = task[key]
            if isinstance(value, str):
                expanded = _expand_include_target_candidates(task, value)
                if expanded:
                    targets.extend(expanded)
                else:
                    candidate = value.strip()
                    if candidate:
                        targets.append(candidate)
            elif isinstance(value, dict):
                file_value = value.get("file") or value.get("_raw_params")
                if isinstance(file_value, str):
                    expanded = _expand_include_target_candidates(task, file_value)
                    if expanded:
                        targets.extend(expanded)
                    else:
                        candidate = file_value.strip()
                        if candidate:
                            targets.append(candidate)
    return targets


def _iter_task_include_edges(data: object) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for task in _iter_task_mappings(data):
        for key in tlp.TASK_INCLUDE_KEYS:
            if key not in task:
                continue
            value = task[key]
            module_name = "import_tasks" if "import_tasks" in key else "include_tasks"
            if isinstance(value, str):
                expanded = _expand_include_target_candidates(task, value)
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
                expanded = _expand_include_target_candidates(task, file_value)
                if expanded:
                    for candidate in expanded:
                        edges.append({"module": module_name, "target": candidate})
                else:
                    candidate = file_value.strip()
                    if candidate:
                        edges.append({"module": module_name, "target": candidate})
    return edges


def _expand_include_target_candidates(task: dict, include_target: str) -> list[str]:
    candidate = include_target.strip()
    if not candidate:
        return []
    if "{{" not in candidate and "{%" not in candidate:
        return [candidate]

    match = tlp.TEMPLATED_INCLUDE_RE.match(candidate)
    if not match:
        return []

    variable = (match.group("var") or "").strip()
    if not variable:
        return []
    allowed_values = tlp._extract_constrained_when_values(task, variable)
    if not allowed_values:
        return []

    prefix = (match.group("prefix") or "").strip()
    suffix = (match.group("suffix") or "").strip()
    return [f"{prefix}{value}{suffix}" for value in allowed_values]


def _iter_role_include_targets(task: dict) -> list[str]:
    role_targets: list[str] = []
    for key in tlp.ROLE_INCLUDE_KEYS:
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


def _iter_dynamic_role_include_targets(task: dict) -> list[str]:
    dynamic_targets: list[str] = []
    for key in tlp.ROLE_INCLUDE_KEYS:
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
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for task_file in task_files:
        data = load_yaml_file(task_file)
        relpath = str(task_file.relative_to(role_root))
        for task in _iter_task_mappings(data):
            task_name = str(task.get("name") or "(unnamed task)")
            for include_key in tlp.TASK_INCLUDE_KEYS:
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
                if _expand_include_target_candidates(task, include_path):
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
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for task_file in task_files:
        data = load_yaml_file(task_file)
        relpath = str(task_file.relative_to(role_root))
        for task in _iter_task_mappings(data):
            task_name = str(task.get("name") or "(unnamed task)")
            for include_key in tlp.ROLE_INCLUDE_KEYS:
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
                if _expand_include_target_candidates(task, role_ref):
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
    "_expand_include_target_candidates",
    "_iter_dynamic_role_include_targets",
    "_iter_role_include_targets",
    "_iter_task_include_edges",
    "_iter_task_include_targets",
    "_iter_task_mappings",
    "collect_unconstrained_dynamic_role_includes",
    "collect_unconstrained_dynamic_task_includes",
]
