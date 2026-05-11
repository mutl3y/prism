"""Tests for Terraform adapter parity and boundaries.

Tests consistency with Kubernetes and Ansible adapters, and validates
boundary behavior for edge cases.
"""

from __future__ import annotations

import pytest

from prism.scanner_plugins.terraform.error_adapter import (
    build_terraform_error_detail,
    classify_terraform_error,
)
from prism.scanner_plugins.terraform.error_codes import (
    TF_ERROR_CATEGORY_MAP,
    TF_ERROR_CODES,
)

pytestmark = pytest.mark.terraform


class TestCategoryParity:
    """Test error category mapping consistency."""

    def test_all_error_codes_have_category_mapping(self) -> None:
        """Verify all error codes have category mappings (parity with K8s/Ansible)."""
        for error_code in TF_ERROR_CODES:
            assert (
                error_code in TF_ERROR_CATEGORY_MAP
            ), f"Error code {error_code} missing category mapping"

    def test_categories_are_valid(self) -> None:
        """Verify categories match allowed taxonomy."""
        allowed_categories = {"runtime", "io", "parser", "api", "auth"}
        for category in TF_ERROR_CATEGORY_MAP.values():
            assert category in allowed_categories, f"Invalid category: {category}"


class TestRecoverabilityParity:
    """Test recoverability classification consistency."""

    def test_transient_errors_return_recoverable_true(self) -> None:
        """Verify transient errors are classified as recoverable."""
        # Lock failed
        exception = RuntimeError("state lock acquisition failed")
        _, _, recoverable = classify_terraform_error(exception)
        assert recoverable is True

        # Backend failed
        exception = RuntimeError("backend initialization failed")
        _, _, recoverable = classify_terraform_error(exception)
        assert recoverable is True

    def test_non_transient_errors_return_recoverable_false(self) -> None:
        """Verify non-transient errors are not recoverable."""
        # Plan failed
        exception = RuntimeError("terraform plan failed")
        _, _, recoverable = classify_terraform_error(exception)
        assert recoverable is False

        # Module not found
        exception = FileNotFoundError("module not found")
        _, _, recoverable = classify_terraform_error(exception)
        assert recoverable is False


class TestBoundaryConditions:
    """Test boundary and edge case behavior."""

    def test_empty_context_returns_empty_dict(self) -> None:
        context: dict[str, str] = {}
        exception = RuntimeError("Error")

        detail = build_terraform_error_detail(context, exception)

        assert isinstance(detail, dict)
        assert len(detail) == 0

    def test_unknown_exception_type_defaults_to_apply_failed(self) -> None:
        exception = ValueError("Unknown error type")

        error_code, category, recoverable = classify_terraform_error(exception)

        assert error_code == "TF_APPLY_FAILED"
        assert category == "runtime"
        assert recoverable is False

    def test_classify_returns_tuple_of_three(self) -> None:
        exception = RuntimeError("any error")

        result = classify_terraform_error(exception)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], str)  # error_code
        assert isinstance(result[1], str)  # category
        assert isinstance(result[2], bool)  # recoverable
