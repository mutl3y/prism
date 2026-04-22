"""Scanner extraction package - consolidates variable, task, and data extraction logic."""

from __future__ import annotations

from prism.scanner_extract.task_line_parsing import (
    TASK_INCLUDE_KEYS,
    ROLE_INCLUDE_KEYS,
    INCLUDE_VARS_KEYS,
    SET_FACT_KEYS,
    TASK_BLOCK_KEYS,
    TASK_META_KEYS,
    ROLE_NOTES_RE,
    TASK_NOTES_LONG_RE,
    COMMENT_CONTINUATION_RE,
)
from prism.scanner_extract.task_file_traversal import (
    is_path_excluded,
    is_relpath_excluded,
    load_yaml_file,
    collect_task_files,
)
from prism.scanner_extract.task_catalog_assembly import (
    collect_task_handler_catalog,
)
from prism.scanner_extract.variable_extractor import (
    DEFAULT_TARGET_RE,
    JINJA_VAR_RE,
    JINJA_IDENTIFIER_RE,
    VAULT_KEY_RE,
    collect_include_vars_files,
    looks_secret_name,
    resembles_password_like,
    extract_default_target_var,
    load_seed_variables,
)
from prism.scanner_extract.discovery import (
    iter_role_variable_map_candidates,
    load_meta,
    load_requirements,
    load_variables,
    resolve_scan_identity,
)
from prism.scanner_extract.dataload import (
    iter_role_yaml_candidates,
    parse_yaml_candidate,
    collect_yaml_parse_failures,
    load_role_variable_maps,
    iter_role_argument_spec_entries,
    map_argument_spec_type,
)
from prism.scanner_extract.requirements import (
    format_requirement_line,
    normalize_requirements,
    normalize_meta_role_dependencies,
    normalize_included_role_dependencies,
    extract_declared_collections_from_meta,
    extract_declared_collections_from_requirements,
    build_collection_compliance_notes,
    build_requirements_display,
)


__all__ = [
    "TASK_INCLUDE_KEYS",
    "ROLE_INCLUDE_KEYS",
    "INCLUDE_VARS_KEYS",
    "SET_FACT_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_META_KEYS",
    "ROLE_NOTES_RE",
    "TASK_NOTES_LONG_RE",
    "COMMENT_CONTINUATION_RE",
    "is_path_excluded",
    "load_yaml_file",
    "collect_task_files",
    "is_relpath_excluded",
    "collect_task_handler_catalog",
    "DEFAULT_TARGET_RE",
    "JINJA_VAR_RE",
    "JINJA_IDENTIFIER_RE",
    "VAULT_KEY_RE",
    "looks_secret_name",
    "resembles_password_like",
    "extract_default_target_var",
    "load_seed_variables",
    "collect_include_vars_files",
    "iter_role_variable_map_candidates",
    "load_meta",
    "load_requirements",
    "load_variables",
    "resolve_scan_identity",
    "iter_role_yaml_candidates",
    "parse_yaml_candidate",
    "collect_yaml_parse_failures",
    "load_role_variable_maps",
    "iter_role_argument_spec_entries",
    "map_argument_spec_type",
    "format_requirement_line",
    "normalize_requirements",
    "normalize_meta_role_dependencies",
    "normalize_included_role_dependencies",
    "extract_declared_collections_from_meta",
    "extract_declared_collections_from_requirements",
    "build_collection_compliance_notes",
    "build_requirements_display",
]


def __getattr__(name: str) -> object:
    """Enforce module public API at runtime."""
    if name.startswith("_"):
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}' "
            f"(private member; only __all__ symbols are public)"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    """Expose only public API in dir() and introspection."""
    return sorted(__all__)
