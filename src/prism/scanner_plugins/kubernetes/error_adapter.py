"""Kubernetes-specific error adapter for structured error envelope construction.

Provides functions to build Kubernetes error details with unified provenance
information (pod name, namespace, cluster, etc.) and classify Kubernetes
exceptions into platform-specific error codes.
"""

from __future__ import annotations

from typing import Any

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


def build_k8s_error_detail(
    resource_context: dict[str, Any],
    exception: Exception,
) -> dict[str, Any]:
    """Build Kubernetes error detail with unified provenance information.

    Constructs a detail dictionary with Kubernetes-specific provenance fields
    that can be used in error envelopes for structured error handling and
    diagnostics.

    Args:
        resource_context: Dictionary with resource context information. Expected keys:
            - pod_name: Pod name (e.g., 'nginx-7d8b49c9bd-abcde')
            - namespace: Kubernetes namespace (e.g., 'default')
            - cluster: Cluster name (e.g., 'prod-us-west')
            - deployment_name: Deployment name
            - service_name: Service name
            - config_name: ConfigMap name
            - secret_name: Secret name
            - error_message: Human-readable error message
        exception: The exception that occurred during resource operation

    Returns:
        Dictionary with unified Kubernetes provenance structure:
        {
            "pod_name": str,
            "namespace": str,
            "cluster": str,
            "deployment_name": str,
            "service_name": str,
            "config_name": str,
            "secret_name": str,
            "error_message": str
        }
    """
    detail: dict[str, Any] = {}

    # Add provenance fields from resource context
    if "pod_name" in resource_context:
        detail["pod_name"] = resource_context["pod_name"]
    if "namespace" in resource_context:
        detail["namespace"] = resource_context["namespace"]
    if "cluster" in resource_context:
        detail["cluster"] = resource_context["cluster"]
    if "deployment_name" in resource_context:
        detail["deployment_name"] = resource_context["deployment_name"]
    if "service_name" in resource_context:
        detail["service_name"] = resource_context["service_name"]
    if "config_name" in resource_context:
        detail["config_name"] = resource_context["config_name"]
    if "secret_name" in resource_context:
        detail["secret_name"] = resource_context["secret_name"]
    if "error_message" in resource_context:
        detail["error_message"] = resource_context["error_message"]

    return detail


def classify_k8s_error(
    exception: Exception,
) -> tuple[str, str, bool]:
    """Classify a Kubernetes exception into error code, category, and recoverability.

    Maps common Kubernetes exception types to structured error metadata for
    use in error envelope construction.

    Args:
        exception: The exception to classify

    Returns:
        Tuple of (error_code, category, recoverable):
        - error_code: K8s-specific error code (e.g., K8S_POD_NOT_FOUND)
        - category: Error category (runtime, io, parser, api, auth)
        - recoverable: True if scan can continue despite this error
    """
    exception_type = type(exception).__name__
    exception_msg = str(exception).lower()

    # RBAC and permission errors
    if exception_type in ("PermissionError", "OSError") and (
        "rbac" in exception_msg or "access denied" in exception_msg
    ):
        return K8S_RBAC_DENIED, "auth", False

    # File not found (config/secret missing)
    if exception_type == "FileNotFoundError":
        if "configmap" in exception_msg or "config" in exception_msg:
            return K8S_CONFIG_MISSING, "io", False
        elif "secret" in exception_msg:
            return K8S_SECRET_NOT_FOUND, "io", False
        else:
            return K8S_CONFIG_MISSING, "io", False

    # Pod errors
    if "pod" in exception_msg:
        if "not found" in exception_msg or "notfound" in exception_msg:
            return K8S_POD_NOT_FOUND, "runtime", False
        elif "pending" in exception_msg or "imagepullbackoff" in exception_msg:
            return K8S_POD_PENDING, "runtime", True
        elif "failed" in exception_msg or "crashloopbackoff" in exception_msg:
            return K8S_POD_FAILED, "runtime", False

    # Replica errors (check before deployment to catch replica-specific issues)
    if "replicas" in exception_msg or (
        "replica" in exception_msg and "ready" in exception_msg
    ):
        return K8S_REPLICAS_NOT_READY, "runtime", True

    # Deployment errors
    if "deployment" in exception_msg:
        if "rollout" in exception_msg or "failed" in exception_msg:
            return K8S_DEPLOYMENT_FAILED, "runtime", False

    # Service errors
    if "service" in exception_msg:
        if "not found" in exception_msg:
            return K8S_SERVICE_NOT_FOUND, "runtime", False
        elif "endpoint" in exception_msg or "no endpoints" in exception_msg:
            return K8S_SERVICE_ENDPOINT_EMPTY, "runtime", True

    # Secret errors (without FileNotFoundError)
    if "secret" in exception_msg and "not found" in exception_msg:
        return K8S_SECRET_NOT_FOUND, "io", False

    # Resource quota errors
    if exception_type in ("RuntimeError", "ValueError") and (
        "quota" in exception_msg or "resource quota exceeded" in exception_msg
    ):
        return K8S_QUOTA_EXCEEDED, "api", False

    # Default: generic pod failure (recoverable)
    return K8S_POD_FAILED, "runtime", True

