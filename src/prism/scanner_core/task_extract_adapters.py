"""Core-facing adapters for task extraction seams.

Pure import re-exports for symbols that need no transformation, plus
marker-prefix injection adapters for annotation/catalog extraction.
"""

from __future__ import annotations

from pathlib import Path

from prism.scanner_core.di_helpers import scan_options_from_di
from prism.scanner_data.contracts_request import TaskAnnotation, YamlParseFailure


def _extract_task_annotations_for_file(
    raw_lines: list[str],
    *,
    marker_prefix: str = "prism",
    include_task_index: bool = False,
    di: object | None = None,
) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
    """Resolve the annotation parser lazily to avoid bootstrap import coupling."""
    from prism.scanner_extract.task_annotation_parsing import (
        extract_task_annotations_for_file,
    )

    return extract_task_annotations_for_file(
        raw_lines,
        marker_prefix=marker_prefix,
        include_task_index=include_task_index,
        di=di,
    )


def _collect_task_handler_catalog(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    marker_prefix: str = "prism",
    di: object | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Resolve the catalog assembler lazily to avoid bootstrap import coupling."""
    from prism.scanner_extract.task_catalog_assembly import collect_task_handler_catalog

    return collect_task_handler_catalog(
        role_path,
        exclude_paths=exclude_paths,
        marker_prefix=marker_prefix,
        di=di,
    )


def detect_task_module(
    task: dict[str, object], *, di: object | None = None
) -> str | None:
    from prism.scanner_extract.task_catalog_assembly import detect_task_module

    return detect_task_module(task, di=di)


def extract_collection_from_module_name(
    module_name: str,
    builtin_collection_prefixes: frozenset[str] = frozenset(),
) -> str | None:
    from prism.scanner_extract.task_catalog_assembly import (
        extract_collection_from_module_name,
    )

    return extract_collection_from_module_name(
        module_name,
        builtin_collection_prefixes=builtin_collection_prefixes,
    )


def collect_task_files(
    role_root: Path,
    *,
    exclude_paths: list[str] | None = None,
    di: object | None = None,
) -> list[Path]:
    from prism.scanner_extract.task_file_traversal import collect_task_files

    return collect_task_files(role_root, exclude_paths=exclude_paths, di=di)


def collect_unconstrained_dynamic_role_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[dict[str, str]]:
    from prism.scanner_extract.task_file_traversal import (
        collect_unconstrained_dynamic_role_includes,
    )

    return collect_unconstrained_dynamic_role_includes(
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
    from prism.scanner_extract.task_file_traversal import (
        collect_unconstrained_dynamic_task_includes,
    )

    return collect_unconstrained_dynamic_task_includes(
        role_path,
        exclude_paths=exclude_paths,
        di=di,
    )


def is_path_excluded(
    path: Path,
    role_root: Path,
    exclude_paths: list[str] | None,
) -> bool:
    from prism.scanner_extract.task_file_traversal import is_path_excluded

    return is_path_excluded(path, role_root, exclude_paths)


def iter_dynamic_role_include_targets(
    task_data: dict,
    *,
    di: object | None = None,
):
    from prism.scanner_extract.task_file_traversal import (
        iter_dynamic_role_include_targets,
    )

    return iter_dynamic_role_include_targets(task_data, di=di)


def iter_role_include_targets(
    task_data: dict,
    *,
    di: object | None = None,
):
    from prism.scanner_extract.task_file_traversal import iter_role_include_targets

    return iter_role_include_targets(task_data, di=di)


def iter_task_include_targets(
    task_data: object,
    *,
    di: object | None = None,
):
    from prism.scanner_extract.task_file_traversal import iter_task_include_targets

    return iter_task_include_targets(task_data, di=di)


def iter_task_mappings(
    task_data: object,
    *,
    di: object | None = None,
):
    from prism.scanner_extract.task_file_traversal import iter_task_mappings

    return iter_task_mappings(task_data, di=di)


def load_task_yaml_file(
    file_path: Path,
    *,
    yaml_failure_collector: list[YamlParseFailure] | None = None,
    role_root: Path | None = None,
    di: object | None = None,
):
    from prism.scanner_extract.task_file_traversal import load_yaml_file

    return load_yaml_file(
        file_path,
        yaml_failure_collector=yaml_failure_collector,
        role_root=role_root,
        di=di,
    )


def _resolve_marker_prefix(di: object | None) -> str:
    scan_options = scan_options_from_di(di)
    if not isinstance(scan_options, dict):
        raise ValueError(
            "prepared_policy_bundle must be available in scan_options to resolve marker prefix"
        )
    bundle = scan_options.get("prepared_policy_bundle")
    if not isinstance(bundle, dict):
        raise ValueError(
            "prepared_policy_bundle must be available in scan_options to resolve marker prefix"
        )
    bundle_prefix = bundle.get("comment_doc_marker_prefix")
    if not isinstance(bundle_prefix, str):
        raise ValueError(
            "prepared_policy_bundle must provide comment_doc_marker_prefix to resolve marker prefix"
        )
    return bundle_prefix


def extract_task_annotations_for_file(
    raw_lines: list[str],
    *,
    include_task_index: bool = False,
    di: object | None = None,
) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
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
