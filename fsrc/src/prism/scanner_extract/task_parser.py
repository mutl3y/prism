"""Task-parser compatibility surface for fsrc feature extraction paths."""

from __future__ import annotations

from prism.scanner_extract.task_annotation_parsing import (
    _extract_task_annotations_for_file,
    _task_anchor,
)
from prism.scanner_extract.task_catalog_assembly import (
    _collect_task_handler_catalog,
    _compact_task_parameters,
    _detect_task_module,
    _extract_collection_from_module_name,
    extract_role_features,
)
from prism.scanner_extract.task_file_traversal import (
    _collect_task_files,
    _collect_task_files_with_unresolved_includes,
    _collect_unconstrained_dynamic_role_includes,
    _collect_unconstrained_dynamic_task_includes,
    _expand_include_target_candidates,
    _format_inline_yaml,
    _is_path_excluded,
    _is_relpath_excluded,
    _iter_dynamic_role_include_targets,
    _iter_role_include_targets,
    _iter_task_include_targets,
    _iter_task_mappings,
    _load_yaml_file,
    _normalize_exclude_patterns,
    _resolve_task_include,
)
from prism.scanner_extract.task_line_parsing import (
    COMMENT_CONTINUATION_RE,
    ROLE_INCLUDE_KEYS,
    TASK_BLOCK_KEYS,
    TASK_ENTRY_RE,
    TASK_INCLUDE_KEYS,
    TASK_META_KEYS,
)
from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
    DEFAULT_DOC_MARKER_PREFIX,
)

__all__ = [
    "COMMENT_CONTINUATION_RE",
    "DEFAULT_DOC_MARKER_PREFIX",
    "ROLE_INCLUDE_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_ENTRY_RE",
    "TASK_INCLUDE_KEYS",
    "TASK_META_KEYS",
    "_collect_task_files",
    "_collect_task_files_with_unresolved_includes",
    "_collect_unconstrained_dynamic_role_includes",
    "_collect_unconstrained_dynamic_task_includes",
    "_collect_task_handler_catalog",
    "_compact_task_parameters",
    "_detect_task_module",
    "_expand_include_target_candidates",
    "_extract_collection_from_module_name",
    "_extract_task_annotations_for_file",
    "_format_inline_yaml",
    "_is_path_excluded",
    "_is_relpath_excluded",
    "_iter_dynamic_role_include_targets",
    "_iter_role_include_targets",
    "_iter_task_include_targets",
    "_iter_task_mappings",
    "_load_yaml_file",
    "_normalize_exclude_patterns",
    "_resolve_task_include",
    "_task_anchor",
    "extract_role_features",
]
