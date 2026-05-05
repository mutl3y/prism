"""Scan payload metadata and routing helpers for the kernel orchestration layer."""

from __future__ import annotations

import copy
from typing import Any

from prism.errors import PrismRuntimeError


_SCAN_PIPELINE_SELECTION_ORDER: tuple[str, ...] = (
    "request.option.scan_pipeline_plugin",
    "policy_context.selection.plugin",
    "platform",
    "registry_default",
)


def _merge_metadata_preserving_existing(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if key not in merged:
            merged[key] = value
            continue

        existing_value = merged[key]
        if isinstance(existing_value, dict) and isinstance(value, dict):
            merged[key] = _merge_metadata_preserving_existing(existing_value, value)
    return merged


def _build_routing_metadata(
    *,
    mode: str | None = None,
    selected_plugin: str | None = None,
    failure_mode: str | None = None,
    preflight_stage: str | None = None,
    exception_type: str | None = None,
    include_selection_order: bool = False,
) -> dict[str, Any]:
    routing: dict[str, Any] = {}
    if mode is not None:
        routing["mode"] = mode
    if include_selection_order:
        routing["selection_order"] = list(_SCAN_PIPELINE_SELECTION_ORDER)
    if selected_plugin is not None:
        routing["selected_plugin"] = selected_plugin
    if failure_mode is not None:
        routing["failure_mode"] = failure_mode
    if preflight_stage is not None:
        routing["preflight_stage"] = preflight_stage
    if exception_type is not None:
        routing["exception_type"] = exception_type
    return routing


def _merge_routing_metadata(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing) if isinstance(existing, dict) else {}
    merged.update(incoming)
    return merged


def _ensure_payload_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        payload["metadata"] = metadata
    return metadata


def _apply_routing_metadata(
    *,
    payload: dict[str, Any],
    routing: dict[str, Any],
) -> dict[str, Any]:
    metadata = _ensure_payload_metadata(payload)
    metadata["routing"] = _merge_routing_metadata(metadata.get("routing"), routing)
    return metadata["routing"]


def _append_scan_policy_warning(
    *,
    payload: dict[str, Any],
    code: str,
    message: str,
    detail: dict[str, Any],
) -> dict[str, Any]:
    warning_metadata = _ensure_payload_metadata(payload)
    existing_warnings = warning_metadata.get("scan_policy_warnings")
    warnings_list = (
        list(existing_warnings) if isinstance(existing_warnings, list) else []
    )
    warning = {
        "code": code,
        "message": message,
        "detail": copy.deepcopy(detail),
    }
    if warning not in warnings_list:
        warnings_list.append(warning)
    warning_metadata["scan_policy_warnings"] = warnings_list
    return payload


def apply_scan_policy_blocker_runtime_outcomes(
    *,
    payload: dict[str, Any],
    strict_mode: bool,
) -> dict[str, Any]:
    """Translate emitted blocker facts into preserved runtime outcomes."""
    metadata = _ensure_payload_metadata(payload)
    blocker_facts = metadata.get("scan_policy_blocker_facts")
    if not isinstance(blocker_facts, dict):
        return payload

    blocker_events: list[tuple[str, str, str, dict[str, Any]]] = []

    dynamic_facts = blocker_facts.get("dynamic_includes")
    if isinstance(dynamic_facts, dict):
        dynamic_total = int(dynamic_facts.get("total_count") or 0)
        if bool(dynamic_facts.get("enabled")) and dynamic_total > 0:
            blocker_events.append(
                (
                    "unconstrained_dynamic_includes_detected",
                    "Scan policy failure: unconstrained dynamic include targets were detected.",
                    "Scan policy warning: unconstrained dynamic include targets were detected.",
                    {
                        "dynamic_task_includes": int(
                            dynamic_facts.get("task_count") or 0
                        ),
                        "dynamic_role_includes": int(
                            dynamic_facts.get("role_count") or 0
                        ),
                    },
                )
            )

    yaml_like_facts = blocker_facts.get("yaml_like_annotations")
    if isinstance(yaml_like_facts, dict):
        yaml_like_count = int(yaml_like_facts.get("count") or 0)
        if bool(yaml_like_facts.get("enabled")) and yaml_like_count > 0:
            blocker_events.append(
                (
                    "yaml_like_task_annotations_detected",
                    "Scan policy failure: yaml-like task annotations were detected.",
                    "Scan policy warning: yaml-like task annotations were detected.",
                    {"yaml_like_task_annotations": yaml_like_count},
                )
            )

    if strict_mode and blocker_events:
        code, failure_message, _warning_message, detail = blocker_events[0]
        raise PrismRuntimeError(
            code=code,
            category="runtime",
            message=failure_message,
            detail=detail,
        )

    for code, _failure_message, warning_message, detail in blocker_events:
        _append_scan_policy_warning(
            payload=payload,
            code=code,
            message=warning_message,
            detail=detail,
        )

    return payload
