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

# These imports remain as they delegate to scanner_extract which will
# eventually delegate back to plugin policies. This is a transitional
# state to break the direct circular dependency while maintaining behavior.
from prism.scanner_extract.task_annotation_parsing import (
    extract_task_annotations_for_file,
)
from prism.scanner_extract.task_catalog_assembly import detect_task_module
from prism.scanner_extract.task_catalog_assembly import (
    extract_collection_from_module_name,
)
from prism.scanner_extract.task_file_traversal import collect_task_files
from prism.scanner_extract.task_file_traversal import (
    iter_dynamic_role_include_targets,
)
from prism.scanner_extract.task_file_traversal import iter_role_include_targets
from prism.scanner_extract.task_file_traversal import iter_task_include_targets
from prism.scanner_extract.task_file_traversal import iter_task_mappings
from prism.scanner_extract.task_file_traversal import is_path_excluded
from prism.scanner_extract.task_file_traversal import (
    load_yaml_file as load_task_yaml_file,
)
from prism.scanner_extract.task_file_traversal import (
    collect_unconstrained_dynamic_role_includes as _collect_unconstrained_dynamic_role_includes,
)
from prism.scanner_extract.task_file_traversal import (
    collect_unconstrained_dynamic_task_includes as _collect_unconstrained_dynamic_task_includes,
)
from prism.scanner_extract.task_catalog_assembly import (
    collect_molecule_scenarios as _collect_molecule_scenarios,
)
from prism.scanner_extract.variable_helpers import format_inline_yaml
from prism.scanner_extract.variable_helpers import find_variable_line_in_yaml
from prism.scanner_extract.variable_helpers import infer_variable_type
from prism.scanner_extract.variable_helpers import is_sensitive_variable
from prism.scanner_extract.variable_helpers import JINJA_IDENTIFIER_RE
from prism.scanner_extract.requirements import normalize_requirements
from prism.scanner_extract.discovery import (
    iter_role_variable_map_candidates,
)

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


def collect_unconstrained_dynamic_role_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[dict[str, str]]:
    """Collect dynamic role includes that cannot be resolved statically.

    Ansible-specific: handles include_role with templated role names.
    """
    return _collect_unconstrained_dynamic_role_includes(
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
    return _collect_unconstrained_dynamic_task_includes(
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
    return _collect_molecule_scenarios(
        role_path,
        exclude_paths=exclude_paths,
        di=di,
    )
