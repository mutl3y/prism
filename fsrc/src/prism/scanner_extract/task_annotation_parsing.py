"""Task annotation extraction compatibility helpers for fsrc task catalogs."""

from __future__ import annotations

from prism.scanner_plugins.defaults import resolve_task_annotation_policy_plugin
from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
    DEFAULT_DOC_MARKER_PREFIX,
)


def _resolve_plugin_registry(di: object | None = None):
    if di is None:
        return None
    registry = getattr(di, "plugin_registry", None)
    if registry is not None:
        return registry
    scan_options = getattr(di, "_scan_options", None)
    if isinstance(scan_options, dict):
        return scan_options.get("plugin_registry")
    return None


def _resolve_policy_with_registry(resolver, di: object | None = None):
    registry = _resolve_plugin_registry(di)
    if registry is None:
        return resolver(di)
    try:
        return resolver(di, registry=registry)
    except TypeError:
        return resolver(di)


def _get_task_annotation_policy(di: object | None = None):
    return _resolve_policy_with_registry(resolve_task_annotation_policy_plugin, di)


def _split_task_annotation_label(
    text: str,
    *,
    di: object | None = None,
) -> tuple[str, str]:
    return _get_task_annotation_policy(di).split_task_annotation_label(text)


def _split_task_target_payload(
    text: str,
    *,
    di: object | None = None,
) -> tuple[str, str]:
    return _get_task_annotation_policy(di).split_task_target_payload(text)


def _annotation_payload_looks_yaml(
    payload: str,
    *,
    di: object | None = None,
) -> bool:
    return _get_task_annotation_policy(di).annotation_payload_looks_yaml(payload)


def _extract_task_annotations_for_file(
    lines: list[str],
    marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
    include_task_index: bool = False,
    *,
    di: object | None = None,
) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
    return _get_task_annotation_policy(di).extract_task_annotations_for_file(
        lines=lines,
        marker_prefix=marker_prefix,
        include_task_index=include_task_index,
    )


def _task_anchor(
    file_path: str,
    task_name: str,
    index: int,
    *,
    di: object | None = None,
) -> str:
    return _get_task_annotation_policy(di).task_anchor(
        file_path=file_path,
        task_name=task_name,
        index=index,
    )


def extract_task_annotations_for_file(
    lines: list[str],
    marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
    include_task_index: bool = False,
    *,
    di: object | None = None,
) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
    return _extract_task_annotations_for_file(
        lines,
        marker_prefix=marker_prefix,
        include_task_index=include_task_index,
        di=di,
    )
