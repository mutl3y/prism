"""Task annotation extraction compatibility helpers for fsrc task catalogs."""

from __future__ import annotations

from prism.scanner_core.di_helpers import require_prepared_policy
from prism.scanner_data.contracts_request import TaskAnnotation


def _split_task_annotation_label(
    text: str,
    *,
    di: object | None = None,
) -> tuple[str, str]:
    return require_prepared_policy(
        di, "task_annotation_parsing", "task_annotation_parsing"
    ).split_task_annotation_label(text)


def _split_task_target_payload(
    text: str,
    *,
    di: object | None = None,
) -> tuple[str, str]:
    return require_prepared_policy(
        di, "task_annotation_parsing", "task_annotation_parsing"
    ).split_task_target_payload(text)


def _annotation_payload_looks_yaml(
    payload: str,
    *,
    di: object | None = None,
) -> bool:
    return require_prepared_policy(
        di, "task_annotation_parsing", "task_annotation_parsing"
    ).annotation_payload_looks_yaml(payload)


def _extract_task_annotations_for_file(
    lines: list[str],
    marker_prefix: str,
    include_task_index: bool = False,
    *,
    di: object | None = None,
) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
    return require_prepared_policy(
        di, "task_annotation_parsing", "task_annotation_parsing"
    ).extract_task_annotations_for_file(
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
    return require_prepared_policy(
        di, "task_annotation_parsing", "task_annotation_parsing"
    ).task_anchor(
        file_path=file_path,
        task_name=task_name,
        index=index,
    )


def extract_task_annotations_for_file(
    lines: list[str],
    marker_prefix: str,
    include_task_index: bool = False,
    *,
    di: object | None = None,
) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
    return _extract_task_annotations_for_file(
        lines,
        marker_prefix=marker_prefix,
        include_task_index=include_task_index,
        di=di,
    )


def task_anchor(
    file_path: str,
    task_name: str,
    index: int,
    *,
    di: object | None = None,
) -> str:
    return _task_anchor(file_path, task_name, index, di=di)
