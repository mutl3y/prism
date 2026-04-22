"""Centralized Prism error taxonomy and structured failure contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict


ERROR_CATEGORY_CONFIG = "config"
ERROR_CATEGORY_RUNTIME = "runtime"
ERROR_CATEGORY_IO = "io"
ERROR_CATEGORY_PARSER = "parser"
ERROR_CATEGORY_VALIDATION = "validation"
ERROR_CATEGORY_NETWORK = "network"
ERROR_CATEGORY_REPO = "repo"

ROLE_CONTENT_MISSING = "role_content_missing"
ROLE_CONTENT_ENCODING_INVALID = "role_content_encoding_invalid"
ROLE_CONTENT_JSON_INVALID = "role_content_json_invalid"
ROLE_CONTENT_YAML_INVALID = "role_content_yaml_invalid"
ROLE_CONTENT_IO_ERROR = "role_content_io_error"
ROLE_CONTENT_INVALID = "role_content_invalid"
ROLE_SCAN_RUNTIME_ERROR = "role_scan_runtime_error"
ROLE_SCAN_FAILED = "role_scan_failed"
ROLE_SCAN_PHASE_FAILED = "role_scan_phase_failed"
ROLE_SCAN_DEGRADED = "role_scan_degraded"
ROLE_POLICY_CONFIG_YAML_INVALID = "role_policy_config_yaml_invalid"
ROLE_README_MARKER_CONFIG_YAML_INVALID = "role_readme_marker_config_yaml_invalid"
ROLE_README_SECTION_CONFIG_YAML_INVALID = "role_readme_section_config_yaml_invalid"
ROLE_METADATA_YAML_INVALID = "role_metadata_yaml_invalid"
ROLE_METADATA_LOAD_FAILED = "role_metadata_load_failed"

SCAN_ROLE_PAYLOAD_JSON_INVALID = "SCAN_ROLE_PAYLOAD_JSON_INVALID"
SCAN_ROLE_PAYLOAD_TYPE_INVALID = "SCAN_ROLE_PAYLOAD_TYPE_INVALID"
SCAN_ROLE_PAYLOAD_SHAPE_INVALID = "SCAN_ROLE_PAYLOAD_SHAPE_INVALID"

REPO_SCAN_PAYLOAD_JSON_INVALID = "REPO_SCAN_PAYLOAD_JSON_INVALID"
REPO_SCAN_PAYLOAD_TYPE_INVALID = "REPO_SCAN_PAYLOAD_TYPE_INVALID"
REPO_SCAN_PAYLOAD_SHAPE_INVALID = "REPO_SCAN_PAYLOAD_SHAPE_INVALID"

REPO_TRANSPORT_FAILED = "repo_transport_failed"
REPO_CLONE_FAILED = "repo_clone_failed"
REPO_SPARSE_CHECKOUT_FAILED = "repo_sparse_checkout_failed"
REPO_CONTENT_INVALID = "repo_content_invalid"

CATEGORY_BY_CODE = {
    ROLE_CONTENT_MISSING: ERROR_CATEGORY_IO,
    ROLE_CONTENT_ENCODING_INVALID: ERROR_CATEGORY_IO,
    ROLE_CONTENT_JSON_INVALID: ERROR_CATEGORY_PARSER,
    ROLE_CONTENT_YAML_INVALID: ERROR_CATEGORY_PARSER,
    ROLE_CONTENT_IO_ERROR: ERROR_CATEGORY_IO,
    ROLE_CONTENT_INVALID: ERROR_CATEGORY_VALIDATION,
    ROLE_SCAN_RUNTIME_ERROR: ERROR_CATEGORY_RUNTIME,
    ROLE_SCAN_FAILED: ERROR_CATEGORY_RUNTIME,
    ROLE_SCAN_PHASE_FAILED: ERROR_CATEGORY_RUNTIME,
    ROLE_SCAN_DEGRADED: ERROR_CATEGORY_RUNTIME,
    ROLE_POLICY_CONFIG_YAML_INVALID: ERROR_CATEGORY_CONFIG,
    ROLE_README_MARKER_CONFIG_YAML_INVALID: ERROR_CATEGORY_CONFIG,
    ROLE_README_SECTION_CONFIG_YAML_INVALID: ERROR_CATEGORY_CONFIG,
    ROLE_METADATA_YAML_INVALID: ERROR_CATEGORY_CONFIG,
    ROLE_METADATA_LOAD_FAILED: ERROR_CATEGORY_CONFIG,
    REPO_TRANSPORT_FAILED: ERROR_CATEGORY_NETWORK,
    REPO_CLONE_FAILED: ERROR_CATEGORY_REPO,
    REPO_SPARSE_CHECKOUT_FAILED: ERROR_CATEGORY_REPO,
    REPO_CONTENT_INVALID: ERROR_CATEGORY_REPO,
}


class FailureDetail(TypedDict, total=False):
    """Structured warning/failure payload shared across API/CLI/repo boundaries."""

    code: str
    category: str
    message: str
    detail_code: str
    source: str
    cause_type: str
    traceback: str


@dataclass(frozen=True)
class FailurePolicy:
    """Request-scoped failure behavior contract used across runtime layers."""

    strict: bool = True


@dataclass
class PrismRuntimeError(RuntimeError):
    """Runtime exception with stable error code and category metadata."""

    code: str
    category: str
    message: str
    detail: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        super().__init__(f"{self.code}: {self.message}")


def category_for_code(code: str, default: str = ERROR_CATEGORY_RUNTIME) -> str:
    category = CATEGORY_BY_CODE.get(code)
    if category is not None:
        return category

    normalized = code.strip().lower()
    category = CATEGORY_BY_CODE.get(normalized)
    if category is not None:
        return category
    if normalized.startswith(
        (
            "readme_marker_config_",
            "readme_section_config_",
            "role_readme_marker_config_",
            "role_readme_section_config_",
            "role_metadata_",
        )
    ):
        return ERROR_CATEGORY_CONFIG
    if normalized.endswith("_json_invalid"):
        return ERROR_CATEGORY_PARSER
    if "yaml" in normalized:
        return (
            ERROR_CATEGORY_CONFIG
            if "readme" in normalized or "metadata" in normalized
            else ERROR_CATEGORY_PARSER
        )
    if normalized.endswith("_io_error") or normalized.endswith("_encoding_invalid"):
        return ERROR_CATEGORY_IO
    if normalized.endswith("_shape_invalid") or normalized.endswith("_type_invalid"):
        return ERROR_CATEGORY_VALIDATION
    if "scan_" in normalized:
        return ERROR_CATEGORY_RUNTIME
    return default


def normalize_warning_code(raw_code: str | None) -> str:
    """Return a canonical lower-case warning code for public payloads."""
    if not isinstance(raw_code, str):
        return ROLE_SCAN_DEGRADED
    normalized = raw_code.strip().lower()
    return normalized or ROLE_SCAN_DEGRADED


def to_failure_detail(
    *,
    code: str,
    message: str,
    source: str | None = None,
    detail_code: str | None = None,
    cause: Exception | None = None,
    traceback_text: str | None = None,
) -> FailureDetail:
    payload: FailureDetail = {
        "code": code,
        "category": category_for_code(code),
        "message": message,
    }
    if source:
        payload["source"] = source
    if detail_code:
        payload["detail_code"] = detail_code
    if cause is not None:
        payload["cause_type"] = cause.__class__.__name__
    if traceback_text:
        payload["traceback"] = traceback_text
    return payload


def normalize_metadata_warnings(metadata: dict[str, Any] | None) -> list[FailureDetail]:
    """Normalize degraded-scan metadata into stable warning records."""
    if not isinstance(metadata, dict):
        return []

    warnings: list[FailureDetail] = []
    seen: set[tuple[str, str, str]] = set()

    def _append(detail: FailureDetail) -> None:
        key = (
            detail.get("code", ""),
            detail.get("source", ""),
            detail.get("message", ""),
        )
        if key in seen:
            return
        seen.add(key)
        warnings.append(detail)

    for item in metadata.get("scan_errors") or []:
        if not isinstance(item, dict):
            continue
        phase = str(item.get("phase") or "").strip()
        message = str(item.get("message") or "").strip()
        if not message:
            continue
        detail = to_failure_detail(
            code=ROLE_SCAN_PHASE_FAILED,
            message=message,
            detail_code=phase or ROLE_SCAN_PHASE_FAILED,
            source=f"scan_phase:{phase}" if phase else None,
        )
        error_type = item.get("error_type")
        if isinstance(error_type, str) and error_type.strip():
            detail["cause_type"] = error_type.strip()
        _append(detail)

    for item in metadata.get("yaml_parse_failures") or []:
        if not isinstance(item, dict):
            continue
        source = str(item.get("file") or "").strip()
        line = item.get("line")
        column = item.get("column")
        if source and isinstance(line, int):
            source = f"{source}:{line}"
            if isinstance(column, int):
                source = f"{source}:{column}"
        message = str(item.get("error") or "").strip()
        if not message:
            continue
        _append(
            to_failure_detail(
                code=ROLE_CONTENT_YAML_INVALID,
                message=f"YAML parse failure: {message}",
                detail_code="yaml_parse_failure",
                source=source or None,
            )
        )

    for warning_items in (
        metadata.get("meta_load_warnings"),
        metadata.get("readme_marker_config_warnings"),
        metadata.get("readme_section_config_warnings"),
    ):
        for raw_warning in warning_items or []:
            if not isinstance(raw_warning, str):
                continue
            code_text, _, remainder = raw_warning.partition(":")
            message_text = remainder.strip() if remainder else raw_warning.strip()
            warning_source: str | None = None
            if remainder:
                source_text, second_sep, tail = remainder.strip().partition(":")
                if second_sep and source_text.strip():
                    warning_source = source_text.strip()
                    message_text = tail.strip() or warning_source
            detail_code = code_text.strip() if code_text.strip() else None
            _append(
                to_failure_detail(
                    code=normalize_warning_code(detail_code),
                    message=message_text or raw_warning.strip(),
                    detail_code=detail_code,
                    source=warning_source,
                )
            )

    if metadata.get("scan_degraded") and not warnings:
        _append(
            to_failure_detail(
                code=ROLE_SCAN_DEGRADED,
                message="Scan completed in degraded mode.",
            )
        )

    return warnings
