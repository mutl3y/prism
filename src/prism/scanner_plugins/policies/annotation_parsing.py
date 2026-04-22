"""Annotation parsing algorithms for default policy implementations."""

from __future__ import annotations

import re

from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
    DEFAULT_DOC_MARKER_PREFIX,
    normalize_marker_prefix,
    get_marker_line_re,
)
from prism.scanner_plugins.policies.constants import (
    COMMENT_CONTINUATION_RE,
    COMMENTED_TASK_ENTRY_RE,
    TASK_ENTRY_RE,
    YAML_LIKE_KEY_VALUE_RE,
    YAML_LIKE_LIST_ITEM_RE,
)


def _normalize_marker_prefix(marker_prefix: str | None) -> str:
    return normalize_marker_prefix(marker_prefix)


def _get_marker_line_re(marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX):
    return get_marker_line_re(marker_prefix)


def split_task_annotation_label(text: str) -> tuple[str, str]:
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


def split_task_target_payload(text: str) -> tuple[str, str]:
    if "|" not in text:
        return "", text.strip()
    target, payload = text.split("|", 1)
    return target.strip(), payload.strip()


def annotation_payload_looks_yaml(payload: str) -> bool:
    return any(
        YAML_LIKE_KEY_VALUE_RE.match(line) or YAML_LIKE_LIST_ITEM_RE.match(line)
        for line in payload.splitlines()
    )


def extract_task_annotations_for_file(
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
            target_name, text = split_task_target_payload(text)
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
            kind, body = split_task_annotation_label(text)
        else:
            kind, body = split_task_annotation_label(f"{label}: {text}")

        if body:
            yaml_like = annotation_payload_looks_yaml(body)
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


def task_anchor(file_path: str, task_name: str, index: int) -> str:
    raw = f"task-{file_path}-{task_name}-{index}"
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return slug or f"task-{index}"


__all__ = [
    "annotation_payload_looks_yaml",
    "extract_task_annotations_for_file",
    "split_task_annotation_label",
    "split_task_target_payload",
    "task_anchor",
]
