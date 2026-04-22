"""Core-facing adapters for task extraction seams.

Pure import re-exports for symbols that need no transformation, plus
marker-prefix injection adapters for annotation/catalog extraction.
"""

from __future__ import annotations

from prism.scanner_data.di_helpers import scan_options_from_di
from prism.scanner_extract.task_annotation_parsing import (
    extract_task_annotations_for_file as _extract_task_annotations_for_file,
)
from prism.scanner_extract.task_catalog_assembly import (
    collect_task_handler_catalog as _collect_task_handler_catalog,
)

# --- pure re-exports (no transformation) ---
from prism.scanner_extract.task_catalog_assembly import (  # noqa: F401
    detect_task_module,
    extract_collection_from_module_name,
)
from prism.scanner_extract.task_file_traversal import (  # noqa: F401
    collect_task_files,
    collect_unconstrained_dynamic_role_includes,
    collect_unconstrained_dynamic_task_includes,
    is_path_excluded,
    iter_dynamic_role_include_targets,
    iter_role_include_targets,
    iter_task_include_targets,
    iter_task_mappings,
    load_yaml_file as load_task_yaml_file,
)


def _resolve_marker_prefix(di: object | None) -> str:
    scan_options = scan_options_from_di(di)
    if not isinstance(scan_options, dict):
        raise ValueError(
            "prepared_policy_bundle must be available via DI scan_options "
            "before marker-prefix resolution"
        )
    bundle = scan_options.get("prepared_policy_bundle")
    if not isinstance(bundle, dict):
        raise ValueError(
            "prepared_policy_bundle must be available in scan_options "
            "before marker-prefix resolution"
        )
    bundle_prefix = bundle.get("comment_doc_marker_prefix")
    if not isinstance(bundle_prefix, str):
        raise ValueError(
            "prepared_policy_bundle.comment_doc_marker_prefix must be set "
            "before marker-prefix resolution"
        )
    return bundle_prefix


def extract_task_annotations_for_file(
    raw_lines: list[str],
    *,
    include_task_index: bool = False,
    di: object | None = None,
) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
    return _extract_task_annotations_for_file(
        raw_lines,
        marker_prefix=_resolve_marker_prefix(di),
        include_task_index=include_task_index,
        di=di,
    )


def collect_task_handler_catalog(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    return _collect_task_handler_catalog(
        role_path,
        exclude_paths=exclude_paths,
        marker_prefix=_resolve_marker_prefix(di),
        di=di,
    )
