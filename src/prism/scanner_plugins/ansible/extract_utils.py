"""Ansible-specific extraction utilities.

This module contains Ansible-specific traversal and parsing functions
that were previously in scanner_extract. These are NOT generic utilities
that other platform plugins (Kubernetes, Terraform) can reuse - each
platform should implement its own extraction logic appropriate to its
file structure and concepts.

Functions moved from scanner_extract to establish clean plugin-extract boundary:
- Task file collection and traversal (Ansible tasks/ directory structure)
- Task include/role include detection (Ansible include_* directives)
- Module and collection name extraction (Ansible module system)
- Molecule scenario collection (Ansible testing framework)
- Variable helpers (Ansible variable formatting and detection)
- Requirements normalization (Ansible Galaxy requirements)
- Discovery helpers (Ansible role variable discovery)
"""

from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable
from typing import Any

from prism.scanner_data.contracts_request import (
    DIContainer,
    TaskAnnotation,
    TaskMapping,
)
from prism.scanner_data.policy_constants import PolicyConstants
from prism.scanner_extract.task_file_traversal import YamlParseFailure
from prism.scanner_plugins.ansible.constants import JINJA_IDENTIFIER_RE

# Re-export with Ansible-specific naming to make ownership clear
__all__ = [
    "extract_task_annotations_for_file",
    "detect_task_module",
    "extract_collection_from_module_name",
    "collect_task_files",
    "iter_dynamic_role_include_targets",
    "iter_role_include_targets",
    "iter_task_include_targets",
    "iter_task_mappings",
    "is_path_excluded",
    "load_task_yaml_file",
    "collect_unconstrained_dynamic_role_includes",
    "collect_unconstrained_dynamic_task_includes",
    "collect_molecule_scenarios",
    "format_inline_yaml",
    "find_variable_line_in_yaml",
    "infer_variable_type",
    "is_sensitive_variable",
    "JINJA_IDENTIFIER_RE",
    "normalize_requirements",
    "iter_role_variable_map_candidates",
]


def extract_task_annotations_for_file(
    lines: list[str],
    marker_prefix: str,
    include_task_index: bool = False,
    *,
    di: DIContainer | None = None,
    policy_constants: PolicyConstants | None = None,
) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
    """Extract task annotations from file (Ansible-specific)."""
    from prism.scanner_extract.task_annotation_parsing import (
        extract_task_annotations_for_file as _extract,
    )

    return _extract(
        lines,
        marker_prefix,
        include_task_index,
        di=di,
        policy_constants=policy_constants,
    )


def detect_task_module(
    task: TaskMapping,
    *,
    di: object | None = None,
    policy_constants: PolicyConstants | None = None,
) -> str | None:
    """Detect task module name (Ansible-specific).

    Args:
        task: Task dict to analyze
        di: DI container for runtime context (optional)
        policy_constants: Policy configuration (optional)

    Returns:
        Detected module name or None if not found.
    """
    from prism.scanner_extract.task_catalog_assembly import (
        detect_task_module as _detect,
    )

    return _detect(task, di=di, policy_constants=policy_constants)


def extract_collection_from_module_name(
    module_name: str,
    builtin_collection_prefixes: frozenset[str] = frozenset(),
) -> str | None:
    """Extract collection name from module name (Ansible-specific)."""
    from prism.scanner_extract.task_catalog_assembly import (
        extract_collection_from_module_name as _extract,
    )

    return _extract(
        module_name, builtin_collection_prefixes=builtin_collection_prefixes
    )


def collect_task_files(
    role_root: Path,
    *,
    exclude_paths: list[str] | None = None,
    di: object | None = None,
    policy_constants: PolicyConstants | None = None,
) -> list[Path]:
    """Collect task files from role (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import collect_task_files as _collect

    return _collect(
        role_root, exclude_paths=exclude_paths, di=di, policy_constants=policy_constants
    )


def iter_dynamic_role_include_targets(
    task: TaskMapping,
    *,
    di: object | None = None,
) -> list[str]:
    """Iterate dynamic role include targets (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import (
        iter_dynamic_role_include_targets as _iter,
    )

    return _iter(task, di=di)


def iter_role_include_targets(
    task: TaskMapping,
    *,
    di: object | None = None,
) -> list[str]:
    """Iterate role include targets (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import (
        iter_role_include_targets as _iter,
    )

    return _iter(task, di=di)


def iter_task_include_targets(
    data: object,
    *,
    di: object | None = None,
) -> list[str]:
    """Iterate task include targets (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import (
        iter_task_include_targets as _iter,
    )

    return _iter(data, di=di)


def iter_task_mappings(
    task: object,
    *,
    di: object | None = None,
) -> Iterable[TaskMapping]:
    """Iterate task mappings (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import iter_task_mappings as _iter

    return _iter(task, di=di)


def is_path_excluded(
    path: Path,
    role_root: Path,
    exclude_paths: list[str] | None,
) -> bool:
    """Check if path is excluded (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import is_path_excluded as _check

    return _check(path, role_root, exclude_paths)


def load_task_yaml_file(
    path: Path,
    *,
    yaml_failure_collector: list[YamlParseFailure] | None = None,
    role_root: Path | None = None,
    di: object | None = None,
) -> object:
    """Load task YAML file (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import (
        load_yaml_file as _load_yaml,
    )

    return _load_yaml(
        path,
        yaml_failure_collector=yaml_failure_collector,
        role_root=role_root,
        di=di,
    )


def format_inline_yaml(value: object) -> str:
    """Format inline YAML value (Ansible-specific)."""
    from prism.scanner_extract.variable_helpers import format_inline_yaml as _format

    return _format(value)


def find_variable_line_in_yaml(
    path: Path | None,
    name: str,
) -> int | None:
    """Find variable line in YAML file (Ansible-specific)."""
    from prism.scanner_extract.variable_helpers import (
        find_variable_line_in_yaml as _find,
    )

    return _find(path, name)


def infer_variable_type(value: object) -> str:
    """Infer variable type from value (Ansible-specific)."""
    from prism.scanner_extract.variable_helpers import infer_variable_type as _infer

    return _infer(value)


def is_sensitive_variable(name: str, value: Any) -> bool:
    """Check if variable is sensitive (Ansible-specific)."""
    from prism.scanner_extract.variable_helpers import is_sensitive_variable as _check

    return _check(name, value)


def normalize_requirements(requirements: list[Any]) -> list[str]:
    """Normalize requirements (Ansible-specific)."""
    from prism.scanner_extract.requirements import normalize_requirements as _normalize

    return _normalize(requirements)


def iter_role_variable_map_candidates(
    role_root: Path,
    subdir: str,
) -> list[Path]:
    """Iterate role variable map candidates (Ansible-specific)."""
    from prism.scanner_extract.discovery import (
        iter_role_variable_map_candidates as _iter,
    )

    return _iter(role_root, subdir)


def collect_unconstrained_dynamic_role_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[dict[str, str]]:
    """Collect dynamic role includes that cannot be resolved statically.

    Ansible-specific: handles include_role with templated role names.
    """
    from prism.scanner_extract.task_file_traversal import (
        collect_unconstrained_dynamic_role_includes as _collect_dyn_role,
    )

    return _collect_dyn_role(
        role_path,
        exclude_paths=exclude_paths,
        di=di,
    )


def collect_unconstrained_dynamic_task_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[dict[str, str]]:
    """Collect dynamic task includes that cannot be resolved statically.

    Ansible-specific: handles include_tasks with templated file names.
    """
    from prism.scanner_extract.task_file_traversal import (
        collect_unconstrained_dynamic_task_includes as _collect_dyn_task,
    )

    return _collect_dyn_task(
        role_path,
        exclude_paths=exclude_paths,
        di=di,
    )


def collect_molecule_scenarios(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[dict[str, object]]:
    """Collect Molecule test scenarios from role.

    Ansible-specific: handles Molecule testing framework structure.
    """
    from prism.scanner_extract.task_catalog_assembly import (
        collect_molecule_scenarios as _collect_scenarios,
    )

    return _collect_scenarios(
        role_path,
        exclude_paths=exclude_paths,
        di=di,
    )
