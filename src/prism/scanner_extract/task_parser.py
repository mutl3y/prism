"""Task file traversal, catalog, and annotation helpers.

This module re-exports functions from focused phase modules to maintain
backward compatibility. Each phase module handles a specific extraction concern:

- task_line_parsing: Constants, regex patterns, marker detection
- task_file_traversal: Path handling, YAML loading, file collection
- task_annotation_parsing: Annotation extraction from lines
- task_catalog_assembly: Catalog building, feature extraction

Exported names consumed by scanner.py:
  Constants: TASK_INCLUDE_KEYS, INCLUDE_VARS_KEYS, SET_FACT_KEYS,
             TASK_BLOCK_KEYS, TASK_META_KEYS
    Regex:     ROLE_NOTES_RE, TASK_NOTES_LONG_RE, COMMENT_CONTINUATION_RE
  Functions: _normalize_exclude_patterns, _is_relpath_excluded,
             _is_path_excluded, _format_inline_yaml, _load_yaml_file,
             _iter_task_include_targets, _iter_task_mappings,
             _resolve_task_include, _collect_task_files,
             _extract_role_notes_from_comments, _split_task_annotation_label,
             _extract_task_annotations_for_file, _task_anchor,
             _detect_task_module, _extract_collection_from_module_name,
             _compact_task_parameters, _collect_task_handler_catalog,
             _collect_molecule_scenarios, extract_role_features
"""

from __future__ import annotations

# Re-export constants from task_line_parsing
from .task_line_parsing import (
    TASK_INCLUDE_KEYS,
    ROLE_INCLUDE_KEYS,
    INCLUDE_VARS_KEYS,
    SET_FACT_KEYS,
    TASK_BLOCK_KEYS,
    TASK_META_KEYS,
    ROLE_NOTES_RE,
    TASK_NOTES_LONG_RE,
    ROLE_NOTES_SHORT_RE,
    TASK_NOTES_SHORT_RE,
    COMMENT_CONTINUATION_RE,
    COMMENTED_TASK_ENTRY_RE,
    TASK_ENTRY_RE,
    YAML_LIKE_KEY_VALUE_RE,
    YAML_LIKE_LIST_ITEM_RE,
    WHEN_IN_LIST_RE,
    TEMPLATED_INCLUDE_RE,
    DEFAULT_DOC_MARKER_PREFIX,
)

# Re-export functions from task_file_traversal
from .task_file_traversal import (
    _normalize_exclude_patterns,
    _is_relpath_excluded,
    _is_path_excluded,
    _format_inline_yaml,
    _load_yaml_file,
    _iter_task_mappings,
    _iter_task_include_targets,
    _expand_include_target_candidates,
    _iter_role_include_targets,
    _iter_dynamic_role_include_targets,
    _resolve_task_include,
    _collect_task_files,
    _collect_unconstrained_dynamic_task_includes,
    _collect_unconstrained_dynamic_role_includes,
)

# Re-export functions from task_annotation_parsing
from .task_annotation_parsing import (
    _split_task_annotation_label,
    _split_task_target_payload,
    _annotation_payload_looks_yaml,
    _extract_task_annotations_for_file,
    _task_anchor,
)

# Re-export functions from task_catalog_assembly
from .task_catalog_assembly import (
    _detect_task_module,
    _extract_collection_from_module_name,
    _compact_task_parameters,
    _extract_role_notes_from_comments,
    _collect_task_handler_catalog,
    _collect_molecule_scenarios,
    extract_role_features,
)

__all__ = [
    # Constants from task_line_parsing
    "TASK_INCLUDE_KEYS",
    "ROLE_INCLUDE_KEYS",
    "INCLUDE_VARS_KEYS",
    "SET_FACT_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_META_KEYS",
    "ROLE_NOTES_RE",
    "TASK_NOTES_LONG_RE",
    "ROLE_NOTES_SHORT_RE",
    "TASK_NOTES_SHORT_RE",
    "COMMENT_CONTINUATION_RE",
    "COMMENTED_TASK_ENTRY_RE",
    "TASK_ENTRY_RE",
    "YAML_LIKE_KEY_VALUE_RE",
    "YAML_LIKE_LIST_ITEM_RE",
    "WHEN_IN_LIST_RE",
    "TEMPLATED_INCLUDE_RE",
    "DEFAULT_DOC_MARKER_PREFIX",
    # Functions from task_file_traversal
    "_normalize_exclude_patterns",
    "_is_relpath_excluded",
    "_is_path_excluded",
    "_format_inline_yaml",
    "_load_yaml_file",
    "_iter_task_mappings",
    "_iter_task_include_targets",
    "_expand_include_target_candidates",
    "_iter_role_include_targets",
    "_iter_dynamic_role_include_targets",
    "_resolve_task_include",
    "_collect_task_files",
    "_collect_unconstrained_dynamic_task_includes",
    "_collect_unconstrained_dynamic_role_includes",
    # Functions from task_annotation_parsing
    "_split_task_annotation_label",
    "_split_task_target_payload",
    "_annotation_payload_looks_yaml",
    "_extract_task_annotations_for_file",
    "_task_anchor",
    # Functions from task_catalog_assembly
    "_detect_task_module",
    "_extract_collection_from_module_name",
    "_compact_task_parameters",
    "_extract_role_notes_from_comments",
    "_collect_task_handler_catalog",
    "_collect_molecule_scenarios",
    "extract_role_features",
    # Public wrapper aliases
    "is_relpath_excluded",
    "is_path_excluded",
    "load_yaml_file",
    "collect_task_files",
    "extract_role_notes_from_comments",
    "collect_unconstrained_dynamic_role_includes",
    "collect_unconstrained_dynamic_task_includes",
    "collect_task_handler_catalog",
    "collect_molecule_scenarios",
]

# ---------------------------------------------------------------------------
# Public wrappers for package-root re-exports.
# ---------------------------------------------------------------------------

is_relpath_excluded = _is_relpath_excluded
is_path_excluded = _is_path_excluded
load_yaml_file = _load_yaml_file
collect_task_files = _collect_task_files
extract_role_notes_from_comments = _extract_role_notes_from_comments
collect_unconstrained_dynamic_role_includes = (
    _collect_unconstrained_dynamic_role_includes
)
collect_unconstrained_dynamic_task_includes = (
    _collect_unconstrained_dynamic_task_includes
)
collect_task_handler_catalog = _collect_task_handler_catalog
collect_molecule_scenarios = _collect_molecule_scenarios
