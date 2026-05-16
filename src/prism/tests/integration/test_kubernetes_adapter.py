"""Tests for Kubernetes error adapter core functionality.

Tests error detection, provenance extraction, and secret sanitization
for Kubernetes platform errors.
"""

from __future__ import annotations

import pytest

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


class TestBuildK8sErrorDetail:
    """Test error detail construction with K8s provenance."""

    def test_build_error_detail_pod_context(self) -> None:
        resource_context = {
            "pod_name": "nginx-7d8b49c9bd-abcde",
            "namespace": "default",
            "cluster": "prod-us-west",
            "error_message": "Pod failed: ImagePullBackOff",
        }
        exception = RuntimeError("Pod failed")

        detail = build_k8s_error_detail(resource_context, exception)

        assert detail["pod_name"] == "nginx-7d8b49c9bd-abcde"
        assert detail["namespace"] == "default"
        assert detail["cluster"] == "prod-us-west"
        assert detail["error_message"] == "Pod failed: ImagePullBackOff"

    def test_build_error_detail_deployment_context(self) -> None:
        resource_context = {
            "deployment_name": "api-server",
            "namespace": "production",
            "cluster": "prod-eu",
            "error_message": "Deployment rollout failed",
        }
        exception = RuntimeError("Deployment failed")

        detail = build_k8s_error_detail(resource_context, exception)

        assert detail["deployment_name"] == "api-server"
        assert detail["namespace"] == "production"
        assert detail["cluster"] == "prod-eu"
        assert detail["error_message"] == "Deployment rollout failed"

    def test_build_error_detail_minimal_context(self) -> None:
        resource_context: dict[str, str] = {}
        exception = RuntimeError("Generic error")

        detail = build_k8s_error_detail(resource_context, exception)

        assert isinstance(detail, dict)

    def test_build_error_detail_preserves_all_fields(self) -> None:
        resource_context = {
            "pod_name": "test-pod",
            "namespace": "test-ns",
            "cluster": "test-cluster",
            "service_name": "test-svc",
            "config_name": "test-config",
            "secret_name": "test-secret",
            "error_message": "Test error",
        }
        exception = RuntimeError("Error")

        detail = build_k8s_error_detail(resource_context, exception)

        assert len(detail) == 7
        for key in resource_context:
            assert detail[key] == resource_context[key]


class TestClassifyK8sError:
    """Test K8s error classification into error codes and categories."""

    def test_classify_pod_not_found(self) -> None:
        exception = RuntimeError("Error from server (NotFound): pods not found")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_POD_NOT_FOUND
        assert category == "runtime"
        assert recoverable is False

    def test_classify_pod_failed(self) -> None:
        exception = RuntimeError("Pod failed: CrashLoopBackOff")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_POD_FAILED
        assert category == "runtime"
        assert recoverable is False

    def test_classify_pod_pending(self) -> None:
        exception = RuntimeError("Pod is pending: ImagePullBackOff")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_POD_PENDING
        assert category == "runtime"
        assert recoverable is True

    def test_classify_deployment_failed(self) -> None:
        exception = RuntimeError("Deployment rollout failed")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_DEPLOYMENT_FAILED
        assert category == "runtime"
        assert recoverable is False

    def test_classify_replicas_not_ready(self) -> None:
        exception = RuntimeError("Deployment has 0/3 replicas ready")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_REPLICAS_NOT_READY
        assert category == "runtime"
        assert recoverable is True

    def test_classify_service_not_found(self) -> None:
        exception = RuntimeError("Service not found")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_SERVICE_NOT_FOUND
        assert category == "runtime"
        assert recoverable is False

    def test_classify_service_endpoint_empty(self) -> None:
        exception = RuntimeError("Service has no endpoints")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_SERVICE_ENDPOINT_EMPTY
        assert category == "runtime"
        assert recoverable is True

    def test_classify_config_missing(self) -> None:
        exception = FileNotFoundError("ConfigMap not found")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_CONFIG_MISSING
        assert category == "io"
        assert recoverable is False

    def test_classify_secret_not_found(self) -> None:
        exception = RuntimeError("Secret not found")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_SECRET_NOT_FOUND
        assert category == "io"
        assert recoverable is False

    def test_classify_quota_exceeded(self) -> None:
        exception = RuntimeError("Resource quota exceeded")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_QUOTA_EXCEEDED
        assert category == "api"
        assert recoverable is False

    def test_classify_rbac_denied(self) -> None:
        exception = PermissionError("RBAC: access denied")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_RBAC_DENIED
        assert category == "auth"
        assert recoverable is False

    def test_classify_generic_runtime_error(self) -> None:
        exception = RuntimeError("Unknown K8s error")

        error_code, category, recoverable = classify_k8s_error(exception)

        assert error_code == K8S_POD_FAILED
        assert category == "runtime"
        assert recoverable is True
