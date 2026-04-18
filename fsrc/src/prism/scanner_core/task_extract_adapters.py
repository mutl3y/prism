"""Core-facing adapters for task extraction seams.

This module keeps scanner_core isolated from extractor private symbol names.
"""

from __future__ import annotations

from prism.scanner_extract.task_annotation_parsing import (
    extract_task_annotations_for_file as _extract_task_annotations_for_file,
)
from prism.scanner_extract.task_catalog_assembly import (
    collect_task_handler_catalog as _collect_task_handler_catalog,
)
from prism.scanner_extract.task_catalog_assembly import (
    detect_task_module as _detect_task_module,
)
from prism.scanner_extract.task_catalog_assembly import (
    extract_collection_from_module_name as _extract_collection_from_module_name,
)
from prism.scanner_extract.task_file_traversal import (
    collect_task_files as _collect_task_files,
)
from prism.scanner_extract.task_file_traversal import (
    collect_unconstrained_dynamic_role_includes as _collect_unconstrained_dynamic_role_includes,
)
from prism.scanner_extract.task_file_traversal import (
    collect_unconstrained_dynamic_task_includes as _collect_unconstrained_dynamic_task_includes,
)
from prism.scanner_extract.task_file_traversal import (
    is_path_excluded as _is_path_excluded,
)
from prism.scanner_extract.task_file_traversal import (
    iter_dynamic_role_include_targets as _iter_dynamic_role_include_targets,
)
from prism.scanner_extract.task_file_traversal import (
    iter_role_include_targets as _iter_role_include_targets,
)
from prism.scanner_extract.task_file_traversal import (
    iter_task_include_targets as _iter_task_include_targets,
)
from prism.scanner_extract.task_file_traversal import (
    iter_task_mappings as _iter_task_mappings,
)
from prism.scanner_extract.task_file_traversal import load_yaml_file as _load_yaml_file
from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
    DEFAULT_DOC_MARKER_PREFIX,
    normalize_marker_prefix,
)


def _scan_options_from_di(di: object | None) -> dict[str, object] | None:
    if di is None:
        return None
    scan_options = getattr(di, "scan_options", None)
    if isinstance(scan_options, dict):
        return scan_options
    scan_options = getattr(di, "_scan_options", None)
    if isinstance(scan_options, dict):
        return scan_options
    return None


def _resolve_marker_prefix_from_policy_context(di: object | None) -> str | None:
    scan_options = _scan_options_from_di(di)
    if not isinstance(scan_options, dict):
        return None
    policy_context = scan_options.get("policy_context")
    if not isinstance(policy_context, dict):
        return None

    comment_doc_context = policy_context.get("comment_doc")
    if isinstance(comment_doc_context, dict):
        marker_context = comment_doc_context.get("marker")
        if isinstance(marker_context, dict):
            canonical_prefix = marker_context.get("prefix")
            if isinstance(canonical_prefix, str):
                return canonical_prefix

    return None


def _resolve_marker_prefix(marker_prefix: str | None, di: object | None) -> str:
    if isinstance(marker_prefix, str):
        return normalize_marker_prefix(marker_prefix)

    configured_prefix = _resolve_marker_prefix_from_policy_context(di)
    if isinstance(configured_prefix, str):
        return normalize_marker_prefix(configured_prefix)

    return DEFAULT_DOC_MARKER_PREFIX


def collect_task_files(role_root, *, exclude_paths=None, di=None):
    return _collect_task_files(role_root, exclude_paths=exclude_paths, di=di)


def is_path_excluded(path, role_root, exclude_paths):
    return _is_path_excluded(path, role_root, exclude_paths)


def load_task_yaml_file(path, *, yaml_failure_collector=None, role_root=None, di=None):
    return _load_yaml_file(
        path,
        yaml_failure_collector=yaml_failure_collector,
        role_root=role_root,
        di=di,
    )


def iter_task_mappings(data, *, di=None):
    return _iter_task_mappings(data, di=di)


def iter_task_include_targets(data, *, di=None):
    return _iter_task_include_targets(data, di=di)


def iter_role_include_targets(task, *, di=None):
    return _iter_role_include_targets(task, di=di)


def iter_dynamic_role_include_targets(task, *, di=None):
    return _iter_dynamic_role_include_targets(task, di=di)


def detect_task_module(task, *, di=None):
    return _detect_task_module(task, di=di)


def extract_collection_from_module_name(module_name: str):
    return _extract_collection_from_module_name(module_name)


def extract_task_annotations_for_file(
    raw_lines,
    *,
    marker_prefix: str | None = None,
    include_task_index: bool = False,
    di=None,
):
    return _extract_task_annotations_for_file(
        raw_lines,
        marker_prefix=_resolve_marker_prefix(marker_prefix, di),
        include_task_index=include_task_index,
        di=di,
    )


def collect_task_handler_catalog(
    role_path,
    exclude_paths=None,
    marker_prefix: str | None = None,
    *,
    di=None,
):
    return _collect_task_handler_catalog(
        role_path,
        exclude_paths=exclude_paths,
        marker_prefix=_resolve_marker_prefix(marker_prefix, di),
        di=di,
    )


def collect_unconstrained_dynamic_task_includes(
    role_path: str,
    *,
    exclude_paths: list[str] | None = None,
    di: object | None = None,
):
    return _collect_unconstrained_dynamic_task_includes(
        role_path,
        exclude_paths=exclude_paths,
        di=di,
    )


def collect_unconstrained_dynamic_role_includes(
    role_path: str,
    *,
    exclude_paths: list[str] | None = None,
    di: object | None = None,
):
    return _collect_unconstrained_dynamic_role_includes(
        role_path,
        exclude_paths=exclude_paths,
        di=di,
    )
