"""Shared helpers for the public API facade."""

from __future__ import annotations

import json
import traceback
from typing import Any

from prism.errors import (
    ERROR_CATEGORY_RUNTIME,
    PrismRuntimeError,
    ROLE_SCAN_FAILED,
    SCAN_ROLE_PAYLOAD_JSON_INVALID,
    SCAN_ROLE_PAYLOAD_SHAPE_INVALID,
    SCAN_ROLE_PAYLOAD_TYPE_INVALID,
)


def collection_role_failure_details(
    exc: Exception,
    *,
    collection_role_failure_codes: tuple[tuple[type[Exception], str, str], ...],
) -> tuple[str, str, str | None]:
    if isinstance(exc, PrismRuntimeError):
        return exc.code, exc.category, exc.code

    for error_type, code, category in collection_role_failure_codes:
        if isinstance(exc, error_type):
            return code, category, None
    return ROLE_SCAN_FAILED, ERROR_CATEGORY_RUNTIME, None


def parse_scan_role_payload(payload: str | dict[str, Any]) -> dict[str, Any]:
    """Parse run_scan JSON payload with explicit classification at the API boundary."""
    if isinstance(payload, dict):
        parsed = payload
    else:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{SCAN_ROLE_PAYLOAD_JSON_INVALID}: scan_role received invalid JSON payload"
            ) from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(
            f"{SCAN_ROLE_PAYLOAD_TYPE_INVALID}: scan_role payload must be a JSON object"
        )

    if "role_name" in parsed and not isinstance(parsed.get("role_name"), str):
        raise RuntimeError(
            f"{SCAN_ROLE_PAYLOAD_SHAPE_INVALID}: expected role_name=str when present"
        )

    if "metadata" in parsed and not isinstance(parsed.get("metadata"), dict):
        raise RuntimeError(
            f"{SCAN_ROLE_PAYLOAD_SHAPE_INVALID}: expected metadata=object when present"
        )

    return parsed


def normalize_scan_role_payload_shape(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach stable public field names to the structured scan payload."""
    normalized = dict(payload)
    if "variables" not in normalized and "display_variables" in normalized:
        normalized["variables"] = normalized["display_variables"]
    if "requirements" not in normalized and "requirements_display" in normalized:
        normalized["requirements"] = normalized["requirements_display"]
    if (
        "default_filters" not in normalized
        and "undocumented_default_filters" in normalized
    ):
        normalized["default_filters"] = normalized["undocumented_default_filters"]
    return normalized


def build_failure_record(
    *,
    role_name: str,
    role_path: str,
    exc: Exception,
    include_traceback: bool,
    collection_role_failure_details_fn,
    to_failure_detail_fn,
) -> dict[str, Any]:
    error_code, error_category, error_detail_code = collection_role_failure_details_fn(
        exc
    )
    traceback_text = (
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if include_traceback
        else None
    )
    detail = to_failure_detail_fn(
        code=error_code,
        message=str(exc),
        detail_code=error_detail_code,
        source=role_path,
        cause=exc,
        traceback_text=traceback_text,
    )
    failure = {
        "role": role_name,
        "path": role_path,
        "error_code": detail["code"],
        "error_category": detail["category"],
        "error_type": detail.get("cause_type", type(exc).__name__),
        "error": detail["message"],
    }
    if error_detail_code is not None:
        failure["error_detail_code"] = error_detail_code
        failure["detail_code"] = error_detail_code
    if traceback_text:
        failure["traceback"] = traceback_text
    return failure
