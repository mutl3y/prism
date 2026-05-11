"""Integration tests for Kubernetes error adapter with fixtures.

Tests error adapter with real fixture scenarios to verify end-to-end
error detection and provenance extraction.
"""

from __future__ import annotations
from typing import Any

from prism.scanner_plugins.kubernetes.error_adapter import (
    build_k8s_error_detail,
    classify_k8s_error,
)
from prism.scanner_plugins.kubernetes.error_codes import (
    K8S_CONFIG_MISSING,
    K8S_DEPLOYMENT_FAILED,
    K8S_POD_FAILED,
    K8S_POD_NOT_FOUND,
    K8S_POD_PENDING,
    K8S_QUOTA_EXCEEDED,
    K8S_RBAC_DENIED,
    K8S_REPLICAS_NOT_READY,
    K8S_SECRET_NOT_FOUND,
    K8S_SERVICE_ENDPOINT_EMPTY,
    K8S_SERVICE_NOT_FOUND,
)


class TestK8sPodFixtures:
    """Test K8s adapter with pod fixtures."""

    def test_pod_not_found_fixture(
        self, k8s_pod_not_found_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_pod_not_found_context["error_message"])

        detail = build_k8s_error_detail(k8s_pod_not_found_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["pod_name"] == "nginx-7d8b49c9bd-abcde"
        assert detail["namespace"] == "default"
        assert error_code == K8S_POD_NOT_FOUND
        assert category == "runtime"
        assert recoverable is False

    def test_pod_failed_fixture(self, k8s_pod_failed_context: dict[str, Any]) -> None:
        exception = RuntimeError(k8s_pod_failed_context["error_message"])

        detail = build_k8s_error_detail(k8s_pod_failed_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["pod_name"] == "api-server-abc123"
        assert error_code == K8S_POD_FAILED
        assert category == "runtime"
        assert recoverable is False

    def test_pod_pending_fixture(self, k8s_pod_pending_context: dict[str, Any]) -> None:
        exception = RuntimeError(k8s_pod_pending_context["error_message"])

        detail = build_k8s_error_detail(k8s_pod_pending_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["pod_name"] == "worker-xyz789"
        assert error_code == K8S_POD_PENDING
        assert category == "runtime"
        assert recoverable is True

    def test_pod_oom_killed_fixture(
        self, k8s_pod_oom_killed_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_pod_oom_killed_context["error_message"])

        detail = build_k8s_error_detail(k8s_pod_oom_killed_context, exception)
        error_code, category, _ = classify_k8s_error(exception)

        assert detail["pod_name"] == "memory-intensive-pod"
        assert error_code == K8S_POD_FAILED

    def test_pod_evicted_fixture(self, k8s_pod_evicted_context: dict[str, Any]) -> None:
        exception = RuntimeError(k8s_pod_evicted_context["error_message"])

        detail = build_k8s_error_detail(k8s_pod_evicted_context, exception)

        assert detail["pod_name"] == "batch-job-123"
        assert detail["cluster"] == "prod-us-east"


class TestK8sDeploymentFixtures:
    """Test K8s adapter with deployment fixtures."""

    def test_deployment_failed_fixture(
        self, k8s_deployment_failed_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_deployment_failed_context["error_message"])

        detail = build_k8s_error_detail(k8s_deployment_failed_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["deployment_name"] == "api-server"
        assert error_code == K8S_DEPLOYMENT_FAILED
        assert category == "runtime"
        assert recoverable is False

    def test_replicas_not_ready_fixture(
        self, k8s_replicas_not_ready_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_replicas_not_ready_context["error_message"])

        detail = build_k8s_error_detail(k8s_replicas_not_ready_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["deployment_name"] == "frontend"
        assert error_code == K8S_REPLICAS_NOT_READY
        assert category == "runtime"
        assert recoverable is True

    def test_deployment_timeout_fixture(
        self, k8s_deployment_timeout_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_deployment_timeout_context["error_message"])

        detail = build_k8s_error_detail(k8s_deployment_timeout_context, exception)
        error_code, _, _ = classify_k8s_error(exception)

        assert detail["deployment_name"] == "backend-api"
        assert error_code == K8S_REPLICAS_NOT_READY


class TestK8sServiceFixtures:
    """Test K8s adapter with service fixtures."""

    def test_service_not_found_fixture(
        self, k8s_service_not_found_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_service_not_found_context["error_message"])

        detail = build_k8s_error_detail(k8s_service_not_found_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["service_name"] == "api-service"
        assert error_code == K8S_SERVICE_NOT_FOUND
        assert category == "runtime"
        assert recoverable is False

    def test_service_endpoint_empty_fixture(
        self, k8s_service_endpoint_empty_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_service_endpoint_empty_context["error_message"])

        detail = build_k8s_error_detail(k8s_service_endpoint_empty_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["service_name"] == "backend-service"
        assert error_code == K8S_SERVICE_ENDPOINT_EMPTY
        assert category == "runtime"
        assert recoverable is True

    def test_service_selector_mismatch_fixture(
        self, k8s_service_selector_mismatch_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_service_selector_mismatch_context["error_message"])

        detail = build_k8s_error_detail(
            k8s_service_selector_mismatch_context, exception
        )
        error_code, _, _ = classify_k8s_error(exception)

        assert detail["service_name"] == "worker-service"
        assert error_code == K8S_SERVICE_ENDPOINT_EMPTY


class TestK8sConfigFixtures:
    """Test K8s adapter with config fixtures."""

    def test_config_missing_fixture(
        self, k8s_config_missing_context: dict[str, Any]
    ) -> None:
        exception = FileNotFoundError(k8s_config_missing_context["error_message"])

        detail = build_k8s_error_detail(k8s_config_missing_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["config_name"] == "app-config"
        assert error_code == K8S_CONFIG_MISSING
        assert category == "io"
        assert recoverable is False

    def test_secret_not_found_fixture(
        self, k8s_secret_not_found_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_secret_not_found_context["error_message"])

        detail = build_k8s_error_detail(k8s_secret_not_found_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["secret_name"] == "db-credentials"
        assert error_code == K8S_SECRET_NOT_FOUND
        assert category == "io"
        assert recoverable is False


class TestK8sResourceFixtures:
    """Test K8s adapter with resource fixtures."""

    def test_quota_exceeded_fixture(
        self, k8s_quota_exceeded_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_quota_exceeded_context["error_message"])

        detail = build_k8s_error_detail(k8s_quota_exceeded_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["namespace"] == "production"
        assert error_code == K8S_QUOTA_EXCEEDED
        assert category == "api"
        assert recoverable is False

    def test_rbac_denied_fixture(self, k8s_rbac_denied_context: dict[str, Any]) -> None:
        exception = PermissionError(k8s_rbac_denied_context["error_message"])

        detail = build_k8s_error_detail(k8s_rbac_denied_context, exception)
        error_code, category, recoverable = classify_k8s_error(exception)

        assert detail["namespace"] == "secure-namespace"
        assert error_code == K8S_RBAC_DENIED
        assert category == "auth"
        assert recoverable is False

    def test_cpu_quota_exceeded_fixture(
        self, k8s_cpu_quota_exceeded_context: dict[str, Any]
    ) -> None:
        exception = RuntimeError(k8s_cpu_quota_exceeded_context["error_message"])

        detail = build_k8s_error_detail(k8s_cpu_quota_exceeded_context, exception)
        error_code, _, _ = classify_k8s_error(exception)

        assert detail["namespace"] == "compute-intensive"
        assert error_code == K8S_QUOTA_EXCEEDED
