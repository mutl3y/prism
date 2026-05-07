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


def extract_task_annotations_for_file(*args: object, **kwargs: object) -> object:
    """Extract task annotations from file (Ansible-specific)."""
    from prism.scanner_extract.task_annotation_parsing import (
        extract_task_annotations_for_file as _extract,
    )

    return _extract(*args, **kwargs)


def detect_task_module(*args: object, **kwargs: object) -> object:
    """Detect task module name (Ansible-specific)."""
    from prism.scanner_extract.task_catalog_assembly import detect_task_module as _detect

    return _detect(*args, **kwargs)


def extract_collection_from_module_name(*args: object, **kwargs: object) -> object:
    """Extract collection name from module name (Ansible-specific)."""
    from prism.scanner_extract.task_catalog_assembly import (
        extract_collection_from_module_name as _extract,
    )

    return _extract(*args, **kwargs)


def collect_task_files(*args: object, **kwargs: object) -> object:
    """Collect task files from role (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import collect_task_files as _collect

    return _collect(*args, **kwargs)


def iter_dynamic_role_include_targets(*args: object, **kwargs: object) -> object:
    """Iterate dynamic role include targets (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import (
        iter_dynamic_role_include_targets as _iter,
    )

    return _iter(*args, **kwargs)


def iter_role_include_targets(*args: object, **kwargs: object) -> object:
    """Iterate role include targets (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import (
        iter_role_include_targets as _iter,
    )

    return _iter(*args, **kwargs)


def iter_task_include_targets(*args: object, **kwargs: object) -> object:
    """Iterate task include targets (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import (
        iter_task_include_targets as _iter,
    )

    return _iter(*args, **kwargs)


def iter_task_mappings(*args: object, **kwargs: object) -> object:
    """Iterate task mappings (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import iter_task_mappings as _iter

    return _iter(*args, **kwargs)


def is_path_excluded(*args: object, **kwargs: object) -> object:
    """Check if path is excluded (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import is_path_excluded as _check

    return _check(*args, **kwargs)


def load_task_yaml_file(*args: object, **kwargs: object) -> object:
    """Load task YAML file (Ansible-specific)."""
    from prism.scanner_extract.task_file_traversal import (
        load_yaml_file as _load_yaml,
    )

    return _load_yaml(*args, **kwargs)


def format_inline_yaml(*args: object, **kwargs: object) -> object:
    """Format inline YAML value (Ansible-specific)."""
    from prism.scanner_extract.variable_helpers import format_inline_yaml as _format

    return _format(*args, **kwargs)


def find_variable_line_in_yaml(*args: object, **kwargs: object) -> object:
    """Find variable line in YAML file (Ansible-specific)."""
    from prism.scanner_extract.variable_helpers import (
        find_variable_line_in_yaml as _find,
    )

    return _find(*args, **kwargs)


def infer_variable_type(*args: object, **kwargs: object) -> object:
    """Infer variable type from value (Ansible-specific)."""
    from prism.scanner_extract.variable_helpers import infer_variable_type as _infer

    return _infer(*args, **kwargs)


def is_sensitive_variable(*args: object, **kwargs: object) -> object:
    """Check if variable is sensitive (Ansible-specific)."""
    from prism.scanner_extract.variable_helpers import is_sensitive_variable as _check

    return _check(*args, **kwargs)


def normalize_requirements(*args: object, **kwargs: object) -> object:
    """Normalize requirements (Ansible-specific)."""
    from prism.scanner_extract.requirements import normalize_requirements as _normalize

    return _normalize(*args, **kwargs)


def iter_role_variable_map_candidates(*args: object, **kwargs: object) -> object:
    """Iterate role variable map candidates (Ansible-specific)."""
    from prism.scanner_extract.discovery import (
        iter_role_variable_map_candidates as _iter,
    )

    return _iter(*args, **kwargs)


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
