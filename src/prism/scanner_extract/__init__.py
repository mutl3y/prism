"""Scanner extraction package - consolidates variable, task, and data extraction logic.

Exports public API for variable discovery orchestation and task feature extraction.
"""

from __future__ import annotations

# Task parsing constants and functions
from .task_parser import (
    TASK_INCLUDE_KEYS,
    ROLE_INCLUDE_KEYS,
    INCLUDE_VARS_KEYS,
    SET_FACT_KEYS,
    TASK_BLOCK_KEYS,
    TASK_META_KEYS,
    ROLE_NOTES_RE,
    ROLE_NOTES_SHORT_RE,
    TASK_NOTES_LONG_RE,
    TASK_NOTES_SHORT_RE,
    COMMENT_CONTINUATION_RE,
    is_path_excluded,
    load_yaml_file,
    collect_task_files,
    is_relpath_excluded,
    extract_role_notes_from_comments,
    collect_unconstrained_dynamic_role_includes,
    collect_unconstrained_dynamic_task_includes,
    collect_task_handler_catalog,
    collect_molecule_scenarios,
    extract_role_features,
)

# Variable extraction functions
from .variable_extractor import (
    DEFAULT_TARGET_RE,
    JINJA_VAR_RE,
    JINJA_IDENTIFIER_RE,
    VAULT_KEY_RE,
    IGNORED_IDENTIFIERS,
    collect_include_vars_files,
    looks_secret_name,
    resembles_password_like,
    extract_default_target_var,
    load_seed_variables,
    refresh_policy_derived_state,
)

# Discovery helpers
from .discovery import (
    iter_role_variable_map_candidates,
    load_meta,
    load_requirements,
    load_variables,
    resolve_scan_identity,
)

# Data loading functions
from .dataload import (
    iter_role_yaml_candidates,
    parse_yaml_candidate,
    collect_yaml_parse_failures,
    load_role_variable_maps,
    iter_role_argument_spec_entries,
    map_argument_spec_type,
)

# Requirements functions
from .requirements import (
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
    # Task parsing
    "TASK_INCLUDE_KEYS",
    "ROLE_INCLUDE_KEYS",
    "INCLUDE_VARS_KEYS",
    "SET_FACT_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_META_KEYS",
    "ROLE_NOTES_RE",
    "ROLE_NOTES_SHORT_RE",
    "TASK_NOTES_LONG_RE",
    "TASK_NOTES_SHORT_RE",
    "COMMENT_CONTINUATION_RE",
    "is_path_excluded",
    "load_yaml_file",
    "collect_task_files",
    "is_relpath_excluded",
    "extract_role_notes_from_comments",
    "collect_unconstrained_dynamic_role_includes",
    "collect_unconstrained_dynamic_task_includes",
    "collect_task_handler_catalog",
    "collect_molecule_scenarios",
    "extract_role_features",
    # Variables
    "DEFAULT_TARGET_RE",
    "JINJA_VAR_RE",
    "JINJA_IDENTIFIER_RE",
    "VAULT_KEY_RE",
    "IGNORED_IDENTIFIERS",
    "looks_secret_name",
    "resembles_password_like",
    "extract_default_target_var",
    "load_seed_variables",
    "collect_include_vars_files",
    "refresh_policy_derived_state",
    # Discovery
    "iter_role_variable_map_candidates",
    "load_meta",
    "load_requirements",
    "load_variables",
    "resolve_scan_identity",
    # Data loading
    "iter_role_yaml_candidates",
    "parse_yaml_candidate",
    "collect_yaml_parse_failures",
    "load_role_variable_maps",
    "iter_role_argument_spec_entries",
    "map_argument_spec_type",
    # Requirements
    "format_requirement_line",
    "normalize_requirements",
    "normalize_meta_role_dependencies",
    "normalize_included_role_dependencies",
    "extract_declared_collections_from_meta",
    "extract_declared_collections_from_requirements",
    "build_collection_compliance_notes",
    "build_requirements_display",
]
