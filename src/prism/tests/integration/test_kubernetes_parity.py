"""Parity tests for Kubernetes adapter against Ansible reference.

Verifies K8s adapter follows same patterns and conventions as Ansible
adapter for consistency across platforms.
"""

from __future__ import annotations

import pytest
from typing import Any

from prism.scanner_plugins.kubernetes.error_adapter import (
    build_k8s_error_detail,
    classify_k8s_error,
)
from prism.scanner_plugins.kubernetes.error_codes import (
    K8S_ERROR_CODES,
    K8S_ERROR_CATEGORY_MAP,
    K8S_TRANSIENT_ERRORS,
)


class TestK8sAdapterParity:
    """Test K8s adapter follows Ansible adapter patterns."""

    def test_error_detail_returns_dict(self) -> None:
        """Error detail builder returns dict like Ansible adapter."""
        context: dict[str, Any] = {"pod_name": "test"}
        exception = RuntimeError("test")
        
        detail = build_k8s_error_detail(context, exception)
        
        assert isinstance(detail, dict)

    def test_error_detail_preserves_context_fields(self) -> None:
        """Error detail preserves all context fields like Ansible."""
        context = {
            "pod_name": "test-pod",
            "namespace": "test-ns",
            "cluster": "test-cluster",
        }
        exception = RuntimeError("test")
        
        detail = build_k8s_error_detail(context, exception)
        
        for key, value in context.items():
            assert detail[key] == value

    def test_classify_error_returns_three_tuple(self) -> None:
        """Classifier returns (code, category, recoverable) like Ansible."""
        exception = RuntimeError("test error")
        
        result = classify_k8s_error(exception)
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        code, category, recoverable = result
        assert isinstance(code, str)
        assert isinstance(category, str)
        assert isinstance(recoverable, bool)

    def test_all_error_codes_have_category_mapping(self) -> None:
        """All K8s codes mapped to categories like Ansible."""
        for error_code in K8S_ERROR_CODES:
            assert error_code in K8S_ERROR_CATEGORY_MAP
            category = K8S_ERROR_CATEGORY_MAP[error_code]
            assert category in {"runtime", "io", "parser", "api", "auth"}

    def test_transient_errors_subset_of_all_codes(self) -> None:
        """Transient codes subset of all codes like Ansible."""
        assert K8S_TRANSIENT_ERRORS.issubset(K8S_ERROR_CODES)

    def test_error_codes_follow_naming_convention(self) -> None:
        """K8s codes follow K8S_ prefix convention."""
        for error_code in K8S_ERROR_CODES:
            assert error_code.startswith("K8S_")
            assert error_code.isupper()
            assert all(c.isalnum() or c == "_" for c in error_code)

    def test_classifier_handles_runtime_error(self) -> None:
        """Classifier handles RuntimeError like Ansible."""
        exception = RuntimeError("Generic error")
        
        code, category, recoverable = classify_k8s_error(exception)
        
        assert code in K8S_ERROR_CODES
        assert category in K8S_ERROR_CATEGORY_MAP.values()

    def test_classifier_handles_permission_error(self) -> None:
        """Classifier handles PermissionError like Ansible."""
        exception = PermissionError("Access denied")
        
        code, category, recoverable = classify_k8s_error(exception)
        
        assert code in K8S_ERROR_CODES
        assert category in {"auth", "api"}
        assert recoverable is False

    def test_classifier_handles_file_not_found_error(self) -> None:
        """Classifier handles FileNotFoundError like Ansible."""
        exception = FileNotFoundError("Config not found")
        
        code, category, recoverable = classify_k8s_error(exception)
        
        assert code in K8S_ERROR_CODES
        assert category == "io"
        assert recoverable is False

    def test_error_detail_empty_context_safe(self) -> None:
        """Empty context handled safely like Ansible."""
        context: dict[str, Any] = {}
        exception = RuntimeError("test")
        
        detail = build_k8s_error_detail(context, exception)
        
        assert isinstance(detail, dict)
        assert len(detail) == 0
