"""Generic base default policy implementations.

Defaults are concrete policy classes that expose stable, platform-agnostic
contracts.  Platform plugins (e.g. Ansible) extend these base sets with
their own collection-qualified module names.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml

from prism.scanner_plugins.parsers.jinja import JinjaAnalysisPolicyPlugin
from prism.scanner_plugins.parsers.yaml import YAMLParsingPolicyPlugin

TASK_INCLUDE_KEYS = {
    "include_tasks",
    "import_tasks",
}
ROLE_INCLUDE_KEYS = {
    "include_role",
    "import_role",
}
INCLUDE_VARS_KEYS = {"include_vars"}
SET_FACT_KEYS = {"set_fact"}
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


def _detect_task_module(task: dict) -> str | None:
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


def _iter_task_mappings(data: object):
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            yield item
            for key in TASK_BLOCK_KEYS:
                nested = item.get(key)
                if nested is not None:
                    yield from _iter_task_mappings(nested)


def _expand_include_target_candidates(task: dict, include_target: str) -> list[str]:
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
    allowed_values = _extract_constrained_when_values(task, variable)
    if not allowed_values:
        return []

    prefix = (match.group("prefix") or "").strip()
    suffix = (match.group("suffix") or "").strip()
    return [f"{prefix}{value}{suffix}" for value in allowed_values]


def _iter_task_include_targets(data: object) -> list[str]:
    targets: list[str] = []
    for task in _iter_task_mappings(data):
        for key in TASK_INCLUDE_KEYS:
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
        for key in TASK_INCLUDE_KEYS:
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


def _iter_role_include_targets(task: dict) -> list[str]:
    role_targets: list[str] = []
    for key in ROLE_INCLUDE_KEYS:
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
    for key in ROLE_INCLUDE_KEYS:
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


def _collect_unconstrained_dynamic_task_includes(
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
            for include_key in TASK_INCLUDE_KEYS:
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


def _collect_unconstrained_dynamic_role_includes(
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
            for include_key in ROLE_INCLUDE_KEYS:
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


def _normalize_marker_prefix(marker_prefix: str | None) -> str:
    if not isinstance(marker_prefix, str):
        return DEFAULT_DOC_MARKER_PREFIX
    prefix = marker_prefix.strip()
    if not prefix:
        return DEFAULT_DOC_MARKER_PREFIX
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
        return DEFAULT_DOC_MARKER_PREFIX
    return prefix


def _get_marker_line_re(marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX):
    escaped_prefix = re.escape(_normalize_marker_prefix(marker_prefix))
    return re.compile(
        rf"^\s*#\s*{escaped_prefix}\s*~\s*(?P<label>[a-z0-9_-]+)\s*:?\s*(?P<body>.*)$",
        flags=re.IGNORECASE,
    )


def _split_task_annotation_label(text: str) -> tuple[str, str]:
    raw = text.strip()
    if not raw:
        return "note", ""
    if ":" not in raw:
        return "note", raw

    prefix, remainder = raw.split(":", 1)
    label = prefix.strip().lower()
    body = remainder.strip()
    if label in {
        "runbook",
        "warning",
        "deprecated",
        "note",
        "notes",
        "additional",
        "additionals",
    }:
        if label == "notes":
            label = "note"
        if label == "additionals":
            label = "additional"
        return label, body
    return "note", raw


def _split_task_target_payload(text: str) -> tuple[str, str]:
    if "|" not in text:
        return "", text.strip()
    target, payload = text.split("|", 1)
    return target.strip(), payload.strip()


def _annotation_payload_looks_yaml(payload: str) -> bool:
    return any(
        YAML_LIKE_KEY_VALUE_RE.match(line) or YAML_LIKE_LIST_ITEM_RE.match(line)
        for line in payload.splitlines()
    )


def _extract_task_annotations_for_file(
    lines: list[str],
    marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
    include_task_index: bool = False,
) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
    from bisect import bisect_right
    from collections import defaultdict

    marker_line_re = _get_marker_line_re(marker_prefix)
    implicit: list[dict[str, object]] = []
    explicit: dict[str, list[dict[str, object]]] = defaultdict(list)
    task_line_indices = [
        idx
        for idx, source_line in enumerate(lines)
        if TASK_ENTRY_RE.match(source_line) and not source_line.lstrip().startswith("#")
    ]

    i = 0
    while i < len(lines):
        line = lines[i]
        marker_match = marker_line_re.match(line)
        if not marker_match:
            i += 1
            continue

        target_name = ""
        label = (marker_match.group("label") or "").strip().lower()
        text = (marker_match.group("body") or "").strip()

        if label == "task":
            target_name, text = _split_task_target_payload(text)
            if not target_name:
                label = "note"
        elif label not in {
            "runbook",
            "warning",
            "deprecated",
            "note",
            "notes",
            "additional",
            "additionals",
        }:
            i += 1
            continue

        if label == "notes":
            label = "note"
        if label == "additionals":
            label = "additional"

        continuation: list[str] = []
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            if marker_line_re.match(next_line):
                break
            cont_match = COMMENT_CONTINUATION_RE.match(next_line)
            if not cont_match:
                break
            continuation.append((cont_match.group(1) or "").strip())
            j += 1

        if continuation:
            text = "\n".join(part for part in [text, *continuation] if part)

        disabled = any(COMMENTED_TASK_ENTRY_RE.match(c) for c in continuation)
        if label == "task" and target_name:
            kind, body = _split_task_annotation_label(text)
        else:
            kind, body = _split_task_annotation_label(f"{label}: {text}")

        if body:
            yaml_like = _annotation_payload_looks_yaml(body)
            item: dict[str, object] = {"kind": kind, "text": body}
            if disabled:
                item["disabled"] = True
            if yaml_like:
                item["format_warning"] = "yaml-like-payload-use-key-equals-value"
            if target_name:
                explicit[target_name].append(item)
            else:
                next_task_pos = bisect_right(task_line_indices, i)
                if include_task_index and next_task_pos < len(task_line_indices):
                    item["task_index"] = next_task_pos
                implicit.append(item)

        i = j if j > i + 1 else i + 1

    return implicit, explicit


def _task_anchor(file_path: str, task_name: str, index: int) -> str:
    raw = f"task-{file_path}-{task_name}-{index}"
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return slug or f"task-{index}"


class DefaultTaskLineParsingPolicyPlugin:
    """Default task-line parsing policy implementation."""

    TASK_INCLUDE_KEYS = TASK_INCLUDE_KEYS
    ROLE_INCLUDE_KEYS = ROLE_INCLUDE_KEYS
    INCLUDE_VARS_KEYS = INCLUDE_VARS_KEYS
    SET_FACT_KEYS = SET_FACT_KEYS
    TASK_BLOCK_KEYS = TASK_BLOCK_KEYS
    TASK_META_KEYS = TASK_META_KEYS
    TEMPLATED_INCLUDE_RE = TEMPLATED_INCLUDE_RE

    @staticmethod
    def extract_constrained_when_values(task: dict, variable: str) -> list[str]:
        return _extract_constrained_when_values(task, variable)

    @staticmethod
    def detect_task_module(task: dict) -> str | None:
        return _detect_task_module(task)


class DefaultTaskTraversalPolicyPlugin:
    """Default task-traversal policy implementation."""

    @staticmethod
    def iter_task_mappings(data: object):
        yield from _iter_task_mappings(data)

    @staticmethod
    def iter_task_include_targets(data: object) -> list[str]:
        return _iter_task_include_targets(data)

    @staticmethod
    def iter_task_include_edges(data: object) -> list[dict[str, str]]:
        return _iter_task_include_edges(data)

    @staticmethod
    def expand_include_target_candidates(task: dict, include_target: str) -> list[str]:
        return _expand_include_target_candidates(task, include_target)

    @staticmethod
    def iter_role_include_targets(task: dict) -> list[str]:
        return _iter_role_include_targets(task)

    @staticmethod
    def iter_dynamic_role_include_targets(task: dict) -> list[str]:
        return _iter_dynamic_role_include_targets(task)

    @staticmethod
    def collect_unconstrained_dynamic_task_includes(
        *, role_root, task_files, load_yaml_file
    ):
        return _collect_unconstrained_dynamic_task_includes(
            role_root=role_root,
            task_files=task_files,
            load_yaml_file=load_yaml_file,
        )

    @staticmethod
    def collect_unconstrained_dynamic_role_includes(
        *, role_root, task_files, load_yaml_file
    ):
        return _collect_unconstrained_dynamic_role_includes(
            role_root=role_root,
            task_files=task_files,
            load_yaml_file=load_yaml_file,
        )


class DefaultVariableExtractorPolicyPlugin:
    """Default variable-extractor policy implementation."""

    @staticmethod
    def collect_include_vars_files(
        *,
        role_path: str,
        exclude_paths: list[str] | None,
        collect_task_files,
        load_yaml_file,
    ):
        role_root = Path(role_path).resolve()
        include_files: set[Path] = set()
        for task_file in collect_task_files(role_root, exclude_paths=exclude_paths):
            data = load_yaml_file(task_file)
            if not isinstance(data, list):
                continue
            for task in data:
                if not isinstance(task, dict):
                    continue
                for key in INCLUDE_VARS_KEYS:
                    if key not in task:
                        continue
                    value = task.get(key)
                    if isinstance(value, str):
                        include_path = (task_file.parent / value).resolve()
                        if include_path.is_file():
                            include_files.add(include_path)
                    elif isinstance(value, dict):
                        file_value = value.get("file") or value.get("_raw_params")
                        if isinstance(file_value, str):
                            include_path = (task_file.parent / file_value).resolve()
                            if include_path.is_file():
                                include_files.add(include_path)
        return sorted(include_files)


class DefaultTaskAnnotationPolicyPlugin:
    """Default task-annotation parsing policy implementation."""

    COMMENT_CONTINUATION_RE = COMMENT_CONTINUATION_RE
    COMMENTED_TASK_ENTRY_RE = COMMENTED_TASK_ENTRY_RE
    TASK_ENTRY_RE = TASK_ENTRY_RE
    YAML_LIKE_KEY_VALUE_RE = YAML_LIKE_KEY_VALUE_RE
    YAML_LIKE_LIST_ITEM_RE = YAML_LIKE_LIST_ITEM_RE

    @staticmethod
    def split_task_annotation_label(text: str) -> tuple[str, str]:
        return _split_task_annotation_label(text)

    @staticmethod
    def normalize_marker_prefix(marker_prefix: str | None) -> str:
        return _normalize_marker_prefix(marker_prefix)

    @staticmethod
    def get_marker_line_re(marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX):
        return _get_marker_line_re(marker_prefix)

    @staticmethod
    def split_task_target_payload(text: str) -> tuple[str, str]:
        return _split_task_target_payload(text)

    @staticmethod
    def annotation_payload_looks_yaml(payload: str) -> bool:
        return _annotation_payload_looks_yaml(payload)

    @staticmethod
    def extract_task_annotations_for_file(
        lines: list[str],
        marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
        include_task_index: bool = False,
    ) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
        return _extract_task_annotations_for_file(
            lines=lines,
            marker_prefix=marker_prefix,
            include_task_index=include_task_index,
        )

    @staticmethod
    def task_anchor(file_path: str, task_name: str, index: int) -> str:
        return _task_anchor(file_path, task_name, index)


class DefaultYAMLParsingPolicyPlugin(YAMLParsingPolicyPlugin):
    """Default YAML parsing policy compatibility alias."""


class DefaultJinjaAnalysisPolicyPlugin(JinjaAnalysisPolicyPlugin):
    """Default Jinja analysis policy compatibility alias."""


__all__ = [
    "DefaultJinjaAnalysisPolicyPlugin",
    "DefaultTaskAnnotationPolicyPlugin",
    "DefaultTaskLineParsingPolicyPlugin",
    "DefaultTaskTraversalPolicyPlugin",
    "DefaultVariableExtractorPolicyPlugin",
    "DefaultYAMLParsingPolicyPlugin",
]
