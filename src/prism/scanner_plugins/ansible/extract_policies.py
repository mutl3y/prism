"""Ansible extract-policy plugin adapters for fsrc."""

from __future__ import annotations

from collections.abc import Collection

from prism.scanner_plugins.ansible import task_line_parsing as task_line_parsing_module
from prism.scanner_plugins.ansible import task_annotation_strategy
from prism.scanner_plugins.ansible import task_traversal_bare
from prism.scanner_plugins.ansible import (
    variable_extractor as variable_extractor_module,
)
from prism.scanner_plugins.parsers.jinja import (
    collect_undeclared_jinja_variables as _collect_undeclared_jinja_variables,
)


DEFAULT_DOC_MARKER_PREFIX = task_annotation_strategy.DEFAULT_DOC_MARKER_PREFIX

_ANSIBLE_TASK_INCLUDE_KEYS = task_line_parsing_module.TASK_INCLUDE_KEYS
_ANSIBLE_ROLE_INCLUDE_KEYS = task_line_parsing_module.ROLE_INCLUDE_KEYS


class AnsibleTaskLineParsingPolicyPlugin:
    """Expose ansible task-line parsing contracts via a policy plugin object."""

    TASK_INCLUDE_KEYS: Collection[str] = frozenset(
        task_line_parsing_module.TASK_INCLUDE_KEYS
    )
    ROLE_INCLUDE_KEYS: Collection[str] = frozenset(
        task_line_parsing_module.ROLE_INCLUDE_KEYS
    )
    INCLUDE_VARS_KEYS: Collection[str] = frozenset(
        task_line_parsing_module.INCLUDE_VARS_KEYS
    )
    SET_FACT_KEYS: Collection[str] = frozenset(task_line_parsing_module.SET_FACT_KEYS)
    TASK_BLOCK_KEYS: Collection[str] = frozenset(
        task_line_parsing_module.TASK_BLOCK_KEYS
    )
    TASK_META_KEYS: Collection[str] = frozenset(task_line_parsing_module.TASK_META_KEYS)
    TEMPLATED_INCLUDE_RE = task_line_parsing_module.TEMPLATED_INCLUDE_RE

    @staticmethod
    def extract_constrained_when_values(task: dict, variable: str) -> list[str]:
        return task_traversal_bare.extract_constrained_when_values(task, variable)

    @staticmethod
    def detect_task_module(task: dict) -> str | None:
        return task_line_parsing_module.detect_task_module(task)


class AnsibleTaskTraversalPolicyPlugin:
    """Expose ansible task traversal helpers via a policy plugin object."""

    @staticmethod
    def iter_task_mappings(data: object):
        yield from task_traversal_bare.iter_task_mappings(data)

    @staticmethod
    def iter_task_include_targets(data: object) -> list[str]:
        return task_traversal_bare.iter_task_include_targets(
            data, task_include_keys=_ANSIBLE_TASK_INCLUDE_KEYS
        )

    @staticmethod
    def iter_task_include_edges(data: object) -> list[dict[str, str]]:
        return task_traversal_bare.iter_task_include_edges(
            data, task_include_keys=_ANSIBLE_TASK_INCLUDE_KEYS
        )

    @staticmethod
    def expand_include_target_candidates(task: dict, include_target: str) -> list[str]:
        return task_traversal_bare.expand_include_target_candidates(
            task, include_target
        )

    @staticmethod
    def iter_role_include_targets(task: dict) -> list[str]:
        return task_traversal_bare.iter_role_include_targets(
            task, role_include_keys=_ANSIBLE_ROLE_INCLUDE_KEYS
        )

    @staticmethod
    def iter_dynamic_role_include_targets(task: dict) -> list[str]:
        return task_traversal_bare.iter_dynamic_role_include_targets(
            task, role_include_keys=_ANSIBLE_ROLE_INCLUDE_KEYS
        )

    @staticmethod
    def collect_unconstrained_dynamic_task_includes(
        *, role_root, task_files, load_yaml_file
    ):
        return task_traversal_bare.collect_unconstrained_dynamic_task_includes(
            role_root=role_root,
            task_files=task_files,
            load_yaml_file=load_yaml_file,
            task_include_keys=_ANSIBLE_TASK_INCLUDE_KEYS,
        )

    @staticmethod
    def collect_unconstrained_dynamic_role_includes(
        *, role_root, task_files, load_yaml_file
    ):
        return task_traversal_bare.collect_unconstrained_dynamic_role_includes(
            role_root=role_root,
            task_files=task_files,
            load_yaml_file=load_yaml_file,
            role_include_keys=_ANSIBLE_ROLE_INCLUDE_KEYS,
        )


class AnsibleVariableExtractorPolicyPlugin:
    """Expose ansible include_vars extraction helpers via a policy plugin object."""

    @staticmethod
    def collect_include_vars_files(
        *,
        role_path: str,
        exclude_paths: list[str] | None,
        collect_task_files,
        load_yaml_file,
    ):
        return variable_extractor_module.collect_include_vars_files(
            role_path=role_path,
            exclude_paths=exclude_paths,
            collect_task_files=collect_task_files,
            load_yaml_file=load_yaml_file,
        )

    @staticmethod
    def collect_undeclared_jinja_variables(text: str) -> set[str]:
        return _collect_undeclared_jinja_variables(text)


class AnsibleTaskAnnotationPolicyPlugin:
    """Expose ansible task-annotation parsing via a policy plugin object."""

    COMMENT_CONTINUATION_RE = task_annotation_strategy.COMMENT_CONTINUATION_RE
    COMMENTED_TASK_ENTRY_RE = task_annotation_strategy.COMMENTED_TASK_ENTRY_RE
    TASK_ENTRY_RE = task_annotation_strategy.TASK_ENTRY_RE
    YAML_LIKE_KEY_VALUE_RE = task_annotation_strategy.YAML_LIKE_KEY_VALUE_RE
    YAML_LIKE_LIST_ITEM_RE = task_annotation_strategy.YAML_LIKE_LIST_ITEM_RE

    @staticmethod
    def split_task_annotation_label(text: str) -> tuple[str, str]:
        return task_annotation_strategy.split_task_annotation_label(text)

    @staticmethod
    def normalize_marker_prefix(marker_prefix: str | None) -> str:
        return task_annotation_strategy.normalize_marker_prefix(marker_prefix)

    @staticmethod
    def get_marker_line_re(marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX):
        return task_annotation_strategy.get_marker_line_re(marker_prefix)

    @staticmethod
    def split_task_target_payload(text: str) -> tuple[str, str]:
        return task_annotation_strategy.split_task_target_payload(text)

    @staticmethod
    def annotation_payload_looks_yaml(payload: str) -> bool:
        return task_annotation_strategy.annotation_payload_looks_yaml(payload)

    @staticmethod
    def extract_task_annotations_for_file(
        lines: list[str],
        marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
        include_task_index: bool = False,
    ) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
        return task_annotation_strategy.extract_task_annotations_for_file(
            lines=lines,
            marker_prefix=marker_prefix,
            include_task_index=include_task_index,
        )

    @staticmethod
    def task_anchor(file_path: str, task_name: str, index: int) -> str:
        return task_annotation_strategy.task_anchor(file_path, task_name, index)


__all__ = [
    "AnsibleTaskAnnotationPolicyPlugin",
    "AnsibleTaskLineParsingPolicyPlugin",
    "AnsibleTaskTraversalPolicyPlugin",
    "AnsibleVariableExtractorPolicyPlugin",
]
