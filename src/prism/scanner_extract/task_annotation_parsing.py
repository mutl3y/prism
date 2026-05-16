"""Task annotation extraction compatibility helpers for fsrc task catalogs."""

from __future__ import annotations

from typing import cast

from prism.scanner_core.di_helpers import require_prepared_policy
from prism.scanner_data.contracts_request import (
    DIContainer,
    PreparedTaskAnnotationPolicy,
    TaskAnnotation,
)
from prism.scanner_data.policy_constants import PolicyConstants


def _annotation_policy(
    di: DIContainer | None,
    policy_constants: PolicyConstants | None,
) -> PreparedTaskAnnotationPolicy:
    if policy_constants is not None:
        policy = getattr(policy_constants, "task_annotation_parsing", None)
        if policy is not None:
            return policy
    return cast(
        PreparedTaskAnnotationPolicy,
        require_prepared_policy(
            di, "task_annotation_parsing", "task_annotation_parsing"
        ),
    )


def _split_task_annotation_label(
    text: str,
    *,
    di: DIContainer | None = None,
    policy_constants: PolicyConstants | None = None,
) -> tuple[str, str]:
    return _annotation_policy(di, policy_constants).split_task_annotation_label(text)


def _split_task_target_payload(
    text: str,
    *,
    di: DIContainer | None = None,
    policy_constants: PolicyConstants | None = None,
) -> tuple[str, str]:
    return _annotation_policy(di, policy_constants).split_task_target_payload(text)


def _annotation_payload_looks_yaml(
    payload: str,
    *,
    di: DIContainer | None = None,
    policy_constants: PolicyConstants | None = None,
) -> bool:
    return _annotation_policy(di, policy_constants).annotation_payload_looks_yaml(
        payload
    )


def _extract_task_annotations_for_file(
    lines: list[str],
    marker_prefix: str,
    include_task_index: bool = False,
    *,
    di: DIContainer | None = None,
    policy_constants: PolicyConstants | None = None,
) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
    return _annotation_policy(di, policy_constants).extract_task_annotations_for_file(
        lines=lines,
        marker_prefix=marker_prefix,
        include_task_index=include_task_index,
    )


def _task_anchor(
    file_path: str,
    task_name: str,
    index: int,
    *,
    di: DIContainer | None = None,
    policy_constants: PolicyConstants | None = None,
) -> str:
    return _annotation_policy(di, policy_constants).task_anchor(
        file_path=file_path,
        task_name=task_name,
        index=index,
    )


def extract_task_annotations_for_file(
    lines: list[str],
    marker_prefix: str,
    include_task_index: bool = False,
    *,
    di: DIContainer | None = None,
    policy_constants: PolicyConstants | None = None,
) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
    return _extract_task_annotations_for_file(
        lines,
        marker_prefix=marker_prefix,
        include_task_index=include_task_index,
        di=di,
        policy_constants=policy_constants,
    )


def task_anchor(
    file_path: str,
    task_name: str,
    index: int,
    *,
    di: DIContainer | None = None,
    policy_constants: PolicyConstants | None = None,
) -> str:
    return _task_anchor(
        file_path, task_name, index, di=di, policy_constants=policy_constants
    )
