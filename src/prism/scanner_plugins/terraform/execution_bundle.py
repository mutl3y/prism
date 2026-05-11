"""Fail-closed Terraform execution-bundle participants for the first slice."""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable
from pathlib import Path
from typing import Any

from prism.scanner_data.contracts_request import TaskAnnotation, TaskMapping
from prism.scanner_data.contracts_request import YamlParseFailure


class _TerraformTaskLineParsingPolicy:
    TASK_INCLUDE_KEYS: Collection[str] = frozenset()
    ROLE_INCLUDE_KEYS: Collection[str] = frozenset()
    INCLUDE_VARS_KEYS: Collection[str] = frozenset()
    SET_FACT_KEYS: Collection[str] = frozenset()
    TASK_BLOCK_KEYS: Collection[str] = frozenset()
    TASK_META_KEYS: Collection[str] = frozenset()

    @staticmethod
    def detect_task_module(task: TaskMapping) -> str | None:
        del task
        return None


class _TerraformJinjaAnalysisPolicy:
    @staticmethod
    def collect_undeclared_jinja_variables(text: str) -> set[str]:
        del text
        return set()


class _TerraformTaskTraversalPolicy:
    @staticmethod
    def iter_task_mappings(data: object) -> Iterable[TaskMapping]:
        del data
        return ()

    @staticmethod
    def iter_task_include_targets(data: object) -> list[str]:
        del data
        return []

    @staticmethod
    def iter_task_include_edges(data: object) -> list[dict[str, str]]:
        del data
        return []

    @staticmethod
    def expand_include_target_candidates(
        task: TaskMapping, include_target: str
    ) -> list[str]:
        del task, include_target
        return []

    @staticmethod
    def iter_role_include_targets(task: TaskMapping) -> list[str]:
        del task
        return []

    @staticmethod
    def iter_dynamic_role_include_targets(task: TaskMapping) -> list[str]:
        del task
        return []

    @staticmethod
    def collect_unconstrained_dynamic_task_includes(
        *, role_root: object, task_files: list[object], load_yaml_file: object
    ) -> list[dict[str, str]]:
        del role_root, task_files, load_yaml_file
        return []

    @staticmethod
    def collect_unconstrained_dynamic_role_includes(
        *, role_root: object, task_files: list[object], load_yaml_file: object
    ) -> list[dict[str, str]]:
        del role_root, task_files, load_yaml_file
        return []


class _TerraformYAMLParsingPolicy:
    @staticmethod
    def load_yaml_file(path: str | Path) -> object:
        del path
        return {}

    @staticmethod
    def parse_yaml_candidate(
        candidate: str | Path, role_root: str | Path
    ) -> YamlParseFailure | None:
        del role_root
        return {
            "file": str(candidate),
            "line": None,
            "column": None,
            "error": "Terraform execution bundle does not provide YAML parsing.",
        }


class _TerraformVariableExtractorPolicy:
    @staticmethod
    def collect_include_vars_files(
        *,
        role_path: str,
        exclude_paths: list[str] | None,
        collect_task_files: object,
        load_yaml_file: object,
    ) -> list[object]:
        del role_path, exclude_paths, collect_task_files, load_yaml_file
        return []


class _TerraformTaskAnnotationPolicy:
    @staticmethod
    def split_task_annotation_label(text: str) -> tuple[str, str]:
        return text, ""

    @staticmethod
    def split_task_target_payload(text: str) -> tuple[str, str]:
        return text, ""

    @staticmethod
    def annotation_payload_looks_yaml(payload: str) -> bool:
        del payload
        return False

    @staticmethod
    def normalize_marker_prefix(marker_prefix: str | None) -> str:
        return marker_prefix or "prism"

    @staticmethod
    def get_marker_line_re(marker_prefix: str = "prism") -> object:
        return re.compile(rf"^\s*#\s*{re.escape(marker_prefix)}:")

    @staticmethod
    def extract_task_annotations_for_file(
        lines: list[str],
        marker_prefix: str = "prism",
        include_task_index: bool = False,
    ) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
        del lines, marker_prefix, include_task_index
        return [], {}

    @staticmethod
    def task_anchor(file_path: str, task_name: str, index: int) -> str:
        del task_name
        return f"{file_path}#task-{index}"


def build_fail_closed_participants() -> dict[str, Any]:
    task_line_parsing = _TerraformTaskLineParsingPolicy()
    jinja_analysis = _TerraformJinjaAnalysisPolicy()
    return {
        "task_line_parsing": task_line_parsing,
        "jinja_analysis": jinja_analysis,
        "task_traversal": _TerraformTaskTraversalPolicy(),
        "yaml_parsing": _TerraformYAMLParsingPolicy(),
        "variable_extractor": _TerraformVariableExtractorPolicy(),
        "task_annotation_parsing": _TerraformTaskAnnotationPolicy(),
    }


def build_terraform_execution_bundle(
    scan_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the Terraform execution bundle for scan pipeline execution.

    Returns a dict containing:
    - prepared_policy: Fail-closed policy participant instances
    - platform_participants: References to key policy participants
    """
    del scan_options
    prepared_policy = build_fail_closed_participants()
    participants = {
        "task_line_parsing": prepared_policy["task_line_parsing"],
        "jinja_analysis": prepared_policy["jinja_analysis"],
    }
    return {
        "prepared_policy": prepared_policy,
        "platform_participants": participants,
    }


__all__ = ["build_fail_closed_participants", "build_terraform_execution_bundle"]