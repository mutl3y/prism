"""Focused tests for the centralized Prism error taxonomy helpers."""

from __future__ import annotations

from prism import errors as prism_errors


def test_to_failure_detail_imports_and_shapes_optional_fields() -> None:
    cause = ValueError("bad payload")

    detail = prism_errors.to_failure_detail(
        code=prism_errors.REPO_CONTENT_INVALID,
        message="repo payload invalid",
        source="scan_repo",
        detail_code="repo_scan_payload_shape_invalid",
        cause=cause,
        traceback_text="traceback text",
    )

    assert detail == {
        "code": prism_errors.REPO_CONTENT_INVALID,
        "category": prism_errors.ERROR_CATEGORY_REPO,
        "message": "repo payload invalid",
        "source": "scan_repo",
        "detail_code": "repo_scan_payload_shape_invalid",
        "cause_type": "ValueError",
        "traceback": "traceback text",
    }


def test_category_for_code_falls_back_for_unknown_codes() -> None:
    assert prism_errors.category_for_code("unknown-code") == (
        prism_errors.ERROR_CATEGORY_RUNTIME
    )
