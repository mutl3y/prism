"""Task annotation extraction compatibility helpers for fsrc task catalogs."""

from __future__ import annotations

from prism.scanner_core.di_helpers import _scan_options_from_di
from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
    DEFAULT_DOC_MARKER_PREFIX,
)


def _get_prepared_policy(di: object | None, policy_name: str) -> object | None:
    scan_options = _scan_options_from_di(di)
    if not isinstance(scan_options, dict):
        return None
    prepared_policy_bundle = scan_options.get("prepared_policy_bundle")
    if not isinstance(prepared_policy_bundle, dict):
        return None
    return prepared_policy_bundle.get(policy_name)


def _get_task_annotation_policy(di: object | None = None):
    prepared_policy = _get_prepared_policy(di, "task_annotation_parsing")
    if prepared_policy is not None:
        return prepared_policy
    raise ValueError(
        "prepared_policy_bundle.task_annotation_parsing must be provided before "
        "task_annotation_parsing canonical execution"
    )


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
