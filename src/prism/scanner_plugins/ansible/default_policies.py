from __future__ import annotations

from collections.abc import Collection, Iterable
from pathlib import Path
from typing import ClassVar, Protocol

from prism.scanner_data.contracts_request import TaskAnnotation, TaskMapping
from prism.scanner_plugins.ansible.task_vocabulary import (
    INCLUDE_VARS_KEYS,
    ROLE_INCLUDE_KEYS,
    SET_FACT_KEYS,
    TASK_BLOCK_KEYS,
    TASK_INCLUDE_KEYS,
    TASK_META_KEYS,
)
from prism.scanner_plugins.ansible.task_traversal_bare import (
    TEMPLATED_INCLUDE_RE,
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
    COMMENT_CONTINUATION_RE,
    DEFAULT_DOC_MARKER_PREFIX,
    NormalizesMarkerPrefix,
    get_marker_line_re,
)
from prism.scanner_plugins.parsers.comment_doc.annotation_parsing import (
    annotation_payload_looks_yaml,
    extract_task_annotations_for_file,
    split_task_annotation_label,
    split_task_target_payload,
    task_anchor,
)
from prism.scanner_plugins.parsers.yaml.line_shape import (
    TASK_ENTRY_RE,
    YAML_LIKE_KEY_VALUE_RE,
    YAML_LIKE_LIST_ITEM_RE,
)


class CollectsTaskFiles(Protocol):
    """Callable that enumerates task files under a role root with optional excludes."""

    def __call__(
        self, role_root: Path, *, exclude_paths: list[str] | None = ...
    ) -> Iterable[Path]: ...


class LoadsYamlFile(Protocol):
    """Callable that loads a YAML file path and returns its parsed object."""

    def __call__(self, path: Path) -> object: ...


class AnsibleDefaultTaskLineParsingPolicyPlugin:
    """Ansible-specific default task-line parsing policy; registered as the 'ansible' platform default."""

    PLUGIN_IS_STATELESS: ClassVar[bool] = True
    TASK_INCLUDE_KEYS = TASK_INCLUDE_KEYS
    ROLE_INCLUDE_KEYS = ROLE_INCLUDE_KEYS
    INCLUDE_VARS_KEYS = INCLUDE_VARS_KEYS
    SET_FACT_KEYS = SET_FACT_KEYS
    TASK_BLOCK_KEYS = TASK_BLOCK_KEYS
    TASK_META_KEYS = TASK_META_KEYS
    TEMPLATED_INCLUDE_RE = TEMPLATED_INCLUDE_RE

    @staticmethod
    def extract_constrained_when_values(task: TaskMapping, variable: str) -> list[str]:
        return extract_constrained_when_values(task, variable)

    @staticmethod
    def detect_task_module(task: TaskMapping) -> str | None:
        return detect_task_module(task)


class AnsibleDefaultVariableExtractorPolicyPlugin:
    """Ansible-specific default variable-extractor policy; registered as the 'ansible' platform default."""

    PLUGIN_IS_STATELESS: ClassVar[bool] = True

    @staticmethod
    def collect_include_vars_files(
        *,
        role_path: str,
        exclude_paths: list[str] | None,
        collect_task_files: CollectsTaskFiles,
        load_yaml_file: LoadsYamlFile,
        include_vars_keys: Collection[str] | None = None,
    ) -> list[Path]:
        effective_keys: Collection[str] = (
            include_vars_keys if include_vars_keys is not None else INCLUDE_VARS_KEYS
        )
        role_root = Path(role_path).resolve()
        include_files: set[Path] = set()

        def add_include_file(ref: str, task_file: Path) -> None:
            include_path = (task_file.parent / ref).resolve()
            if not include_path.is_file():
                return
            try:
                include_path.relative_to(role_root)
            except ValueError:
                return
            include_files.add(include_path)

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
                        add_include_file(value, task_file)
                    elif isinstance(value, dict):
                        file_value = value.get("file") or value.get("_raw_params")
                        if isinstance(file_value, str):
                            add_include_file(file_value, task_file)
        return sorted(include_files)


class AnsibleDefaultTaskAnnotationPolicyPlugin(NormalizesMarkerPrefix):
    """Ansible-specific default task-annotation parsing policy; registered as the 'ansible' platform default."""

    PLUGIN_IS_STATELESS: ClassVar[bool] = True
    COMMENT_CONTINUATION_RE = COMMENT_CONTINUATION_RE
    TASK_ENTRY_RE = TASK_ENTRY_RE
    YAML_LIKE_KEY_VALUE_RE = YAML_LIKE_KEY_VALUE_RE
    YAML_LIKE_LIST_ITEM_RE = YAML_LIKE_LIST_ITEM_RE

    @staticmethod
    def split_task_annotation_label(text: str) -> tuple[str, str]:
        return split_task_annotation_label(text)

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
    ) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
        return extract_task_annotations_for_file(
            lines=lines,
            marker_prefix=marker_prefix,
            include_task_index=include_task_index,
        )

    @staticmethod
    def task_anchor(file_path: str, task_name: str, index: int) -> str:
        return task_anchor(file_path, task_name, index)


class AnsibleDefaultTaskTraversalPolicyPlugin:
    """Ansible-specific default task-traversal policy delegating to task_traversal_bare; registered as the 'ansible' platform default."""

    PLUGIN_IS_STATELESS: ClassVar[bool] = True

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
    def expand_include_target_candidates(
        task: TaskMapping, include_target: str
    ) -> list[str]:
        return expand_include_target_candidates(task, include_target)

    @staticmethod
    def iter_role_include_targets(task: TaskMapping) -> list[str]:
        return iter_role_include_targets(task)

    @staticmethod
    def iter_dynamic_role_include_targets(task: TaskMapping) -> list[str]:
        return iter_dynamic_role_include_targets(task)

    @staticmethod
    def collect_unconstrained_dynamic_task_includes(
        *,
        role_root: Path,
        task_files: list[Path],
        load_yaml_file: LoadsYamlFile,
    ) -> list[dict[str, str]]:
        return collect_unconstrained_dynamic_task_includes(
            role_root=role_root,
            task_files=task_files,
            load_yaml_file=load_yaml_file,
        )

    @staticmethod
    def collect_unconstrained_dynamic_role_includes(
        *,
        role_root: Path,
        task_files: list[Path],
        load_yaml_file: LoadsYamlFile,
    ) -> list[dict[str, str]]:
        return collect_unconstrained_dynamic_role_includes(
            role_root=role_root,
            task_files=task_files,
            load_yaml_file=load_yaml_file,
        )


__all__ = [
    "AnsibleDefaultTaskAnnotationPolicyPlugin",
    "AnsibleDefaultTaskLineParsingPolicyPlugin",
    "AnsibleDefaultTaskTraversalPolicyPlugin",
    "AnsibleDefaultVariableExtractorPolicyPlugin",
]
