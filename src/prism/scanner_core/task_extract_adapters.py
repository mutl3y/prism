"""Core-facing adapters for task extraction seams.

Pure import re-exports for symbols that need no transformation, plus
marker-prefix injection adapters for annotation/catalog extraction.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from prism.scanner_core.di import DIContainer
from prism.scanner_core.marker_prefix_contract import MarkerPrefixContract
from prism.scanner_data.contracts_request import TaskAnnotation, YamlParseFailure


def _extract_task_annotations_for_file(
    raw_lines: list[str],
    *,
    marker_prefix: str = "prism",
    include_task_index: bool = False,
    di: object | None = None,
    policy_constants: object | None = None,
) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
    """Internal implementation that can be monkeypatched by tests.

    Validates marker_prefix at entry per MP1 contract.
    """
    from prism.scanner_extract.task_annotation_parsing import (
        extract_task_annotations_for_file as _impl,
    )

    # MP1 validation: marker_prefix must not be empty
    if not marker_prefix:
        raise ValueError("marker_prefix must not be empty")

    return _impl(
        raw_lines,
        marker_prefix=marker_prefix,
        include_task_index=include_task_index,
        di=cast(DIContainer | None, di),
    )


def extract_task_annotations_for_file(
    raw_lines: list[str],
    *,
    marker_prefix: str = "prism",
    include_task_index: bool = False,
    di: object | None = None,
) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
    """Resolve the annotation parser lazily to avoid bootstrap import coupling.

    CRITICAL: marker_prefix must be passed explicitly from scan ingress,
    not resolved at hot paths. This enforces the MP1 ownership contract.
    """
    # Resolve marker_prefix from bundle if di is present
    if di is not None:
        marker_prefix = _resolve_marker_prefix(di)

    # Validate marker_prefix using MarkerPrefixContract
    MarkerPrefixContract.enforce_marker_prefix_available(marker_prefix)

    return _extract_task_annotations_for_file(
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
    policy_constants: object | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Internal implementation that can be monkeypatched by tests."""
    from prism.scanner_extract.task_catalog_assembly import (
        collect_task_handler_catalog as _impl,
    )

    return _impl(
        role_path,
        exclude_paths=exclude_paths,
        marker_prefix=marker_prefix,
        di=cast(DIContainer | None, di),
    )


def collect_task_handler_catalog(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    marker_prefix: str = "prism",
    di: object | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Resolve the catalog assembler lazily to avoid bootstrap import coupling.

    CRITICAL: marker_prefix must be passed explicitly from scan ingress,
    not resolved at hot paths. This enforces the MP1 ownership contract.
    """
    # Resolve marker_prefix from bundle if di is present
    if di is not None:
        marker_prefix = _resolve_marker_prefix(di)

    # Validate marker_prefix using MarkerPrefixContract
    MarkerPrefixContract.enforce_marker_prefix_available(marker_prefix)

    return _collect_task_handler_catalog(
        role_path,
        exclude_paths=exclude_paths,
        marker_prefix=marker_prefix,
        di=di,
    )


def detect_task_module(
    task: dict[str, object], *, di: object | None = None
) -> str | None:
    from prism.scanner_extract.task_catalog_assembly import detect_task_module

    return detect_task_module(task, di=cast(DIContainer | None, di))


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
    """Resolve marker prefix from prepared_policy_bundle, fail-closed if missing.

    This is an internal helper used by tests and policy enforcement.
    Consumers should use MarkerPrefixContract.enforce_marker_prefix_available() instead.
    """
    if di is None:
        raise ValueError("prepared_policy_bundle must be available in DI context")

    if not hasattr(di, "scan_options"):
        raise ValueError("prepared_policy_bundle must be available in DI context")

    scan_options = getattr(di, "scan_options")
    if not isinstance(scan_options, dict):
        raise ValueError("prepared_policy_bundle must be available in DI context")

    bundle = scan_options.get("prepared_policy_bundle")
    if not isinstance(bundle, dict):
        raise ValueError("prepared_policy_bundle must be available in DI context")

    marker_prefix = bundle.get("comment_doc_marker_prefix")
    if not marker_prefix:
        raise ValueError(
            "comment_doc_marker_prefix must be available in prepared_policy_bundle"
        )

    return marker_prefix
