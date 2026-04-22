"""Ansible-backed default policy implementations.

These classes provide concrete default implementations that are currently
Ansible-specific. They delegate traversal, detection, and extraction logic
to prism.scanner_plugins.ansible.task_traversal_bare and sibling modules.
Platform-specific plugins (e.g. Kubernetes, Terraform) would provide their
own equivalents rather than extending these classes.

Implementation is decomposed across sibling modules:
- constants.py                        — key sets and regex patterns
- ansible/task_traversal_bare.py      — Ansible traversal primitives (this module's runtime)
- annotation_parsing.py               — annotation extraction
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from prism.scanner_plugins.policies.constants import (
    COMMENT_CONTINUATION_RE,
    COMMENTED_TASK_ENTRY_RE,
    INCLUDE_VARS_KEYS,
    ROLE_INCLUDE_KEYS,
    SET_FACT_KEYS,
    TASK_BLOCK_KEYS,
    TASK_ENTRY_RE,
    TASK_INCLUDE_KEYS,
    TASK_META_KEYS,
    YAML_LIKE_KEY_VALUE_RE,
    YAML_LIKE_LIST_ITEM_RE,
)
from prism.scanner_plugins.policies.constants import (
    DEFAULT_DOC_MARKER_PREFIX,
)
from prism.scanner_plugins.ansible.task_traversal_bare import (
    TEMPLATED_INCLUDE_RE,
    WHEN_IN_LIST_RE,
    collect_unconstrained_dynamic_role_includes,
    collect_unconstrained_dynamic_task_includes,
    detect_task_module,
    expand_include_target_candidates,
    extract_constrained_when_values,
    iter_dynamic_role_include_targets,
    iter_role_include_targets,
    iter_task_include_edges,
    iter_task_include_targets,
    iter_task_mappings,
)
from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
    get_marker_line_re,
    normalize_marker_prefix,
)
from prism.scanner_plugins.policies.annotation_parsing import (
    annotation_payload_looks_yaml,
    extract_task_annotations_for_file,
    split_task_annotation_label,
    split_task_target_payload,
    task_anchor,
)


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
        return extract_constrained_when_values(task, variable)

    @staticmethod
    def detect_task_module(task: dict) -> str | None:
        return detect_task_module(task)


class DefaultVariableExtractorPolicyPlugin:
    """Default variable-extractor policy implementation."""

    @staticmethod
    def collect_include_vars_files(
        *,
        role_path: str,
        exclude_paths: list[str] | None,
        collect_task_files: Callable[..., Iterable[Path]],
        load_yaml_file: Callable[[Path], object],
        include_vars_keys: set[str] | None = None,
    ) -> list[Path]:
        effective_keys = (
            include_vars_keys if include_vars_keys is not None else INCLUDE_VARS_KEYS
        )
        role_root = Path(role_path).resolve()
        include_files: set[Path] = set()
        for task_file in collect_task_files(role_root, exclude_paths=exclude_paths):
            data = load_yaml_file(task_file)
            if not isinstance(data, list):
                continue
            for task in data:
                if not isinstance(task, dict):
                    continue
                for key in effective_keys:
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
        return split_task_annotation_label(text)

    @staticmethod
    def normalize_marker_prefix(marker_prefix: str | None) -> str:
        return normalize_marker_prefix(marker_prefix)

    @staticmethod
    def get_marker_line_re(marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX):
        return get_marker_line_re(marker_prefix)

    @staticmethod
    def split_task_target_payload(text: str) -> tuple[str, str]:
        return split_task_target_payload(text)

    @staticmethod
    def annotation_payload_looks_yaml(payload: str) -> bool:
        return annotation_payload_looks_yaml(payload)

    @staticmethod
    def extract_task_annotations_for_file(
        lines: list[str],
        marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
        include_task_index: bool = False,
    ) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
        return extract_task_annotations_for_file(
            lines=lines,
            marker_prefix=marker_prefix,
            include_task_index=include_task_index,
        )

    @staticmethod
    def task_anchor(file_path: str, task_name: str, index: int) -> str:
        return task_anchor(file_path, task_name, index)


class DefaultTaskTraversalPolicyPlugin:
    """Ansible-backed default task-traversal policy delegating to task_traversal_bare."""

    @staticmethod
    def iter_task_mappings(data: object):
        yield from iter_task_mappings(data)

    @staticmethod
    def iter_task_include_targets(data: object) -> list[str]:
        return iter_task_include_targets(data)

    @staticmethod
    def iter_task_include_edges(data: object) -> list[dict[str, str]]:
        return iter_task_include_edges(data)

    @staticmethod
    def expand_include_target_candidates(task: dict, include_target: str) -> list[str]:
        return expand_include_target_candidates(task, include_target)

    @staticmethod
    def iter_role_include_targets(task: dict) -> list[str]:
        return iter_role_include_targets(task)

    @staticmethod
    def iter_dynamic_role_include_targets(task: dict) -> list[str]:
        return iter_dynamic_role_include_targets(task)

    @staticmethod
    def collect_unconstrained_dynamic_task_includes(
        *, role_root, task_files, load_yaml_file
    ):
        return collect_unconstrained_dynamic_task_includes(
            role_root=role_root,
            task_files=task_files,
            load_yaml_file=load_yaml_file,
        )

    @staticmethod
    def collect_unconstrained_dynamic_role_includes(
        *, role_root, task_files, load_yaml_file
    ):
        return collect_unconstrained_dynamic_role_includes(
            role_root=role_root,
            task_files=task_files,
            load_yaml_file=load_yaml_file,
        )


__all__ = [
    "COMMENT_CONTINUATION_RE",
    "COMMENTED_TASK_ENTRY_RE",
    "DEFAULT_DOC_MARKER_PREFIX",
    "DefaultTaskAnnotationPolicyPlugin",
    "DefaultTaskLineParsingPolicyPlugin",
    "DefaultTaskTraversalPolicyPlugin",
    "DefaultVariableExtractorPolicyPlugin",
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
    "collect_unconstrained_dynamic_role_includes",
    "collect_unconstrained_dynamic_task_includes",
    "detect_task_module",
    "expand_include_target_candidates",
    "extract_constrained_when_values",
    "annotation_payload_looks_yaml",
    "extract_task_annotations_for_file",
    "get_marker_line_re",
    "iter_dynamic_role_include_targets",
    "iter_role_include_targets",
    "iter_task_include_edges",
    "iter_task_include_targets",
    "iter_task_mappings",
    "normalize_marker_prefix",
    "split_task_annotation_label",
    "split_task_target_payload",
    "task_anchor",
]
