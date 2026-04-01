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
ROLE_POLICY_CONFIG_YAML_INVALID = "role_policy_config_yaml_invalid"
ROLE_README_MARKER_CONFIG_YAML_INVALID = "role_readme_marker_config_yaml_invalid"
ROLE_README_SECTION_CONFIG_YAML_INVALID = "role_readme_section_config_yaml_invalid"
ROLE_METADATA_YAML_INVALID = "role_metadata_yaml_invalid"

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
    ROLE_POLICY_CONFIG_YAML_INVALID: ERROR_CATEGORY_CONFIG,
    ROLE_README_MARKER_CONFIG_YAML_INVALID: ERROR_CATEGORY_CONFIG,
    ROLE_README_SECTION_CONFIG_YAML_INVALID: ERROR_CATEGORY_CONFIG,
    ROLE_METADATA_YAML_INVALID: ERROR_CATEGORY_CONFIG,
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
    return CATEGORY_BY_CODE.get(code, default)


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
