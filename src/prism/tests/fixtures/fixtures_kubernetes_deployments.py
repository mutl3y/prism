"""Kubernetes deployment fixtures.

Provides deployment-related error scenarios including rollout failures
and replica readiness issues.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def k8s_deployment_failed_context() -> dict[str, Any]:
    """Deployment rollout failed."""
    return {
        "deployment_name": "api-server",
        "namespace": "production",
        "cluster": "prod-eu",
        "error_message": "Deployment rollout failed",
    }


@pytest.fixture
def k8s_replicas_not_ready_context() -> dict[str, Any]:
    """Deployment has replicas not ready."""
    return {
        "deployment_name": "frontend",
        "namespace": "production",
        "cluster": "prod-us-west",
        "error_message": "Deployment has 0/3 replicas ready",
    }


@pytest.fixture
def k8s_deployment_timeout_context() -> dict[str, Any]:
    """Deployment rollout timeout."""
    return {
        "deployment_name": "backend-api",
        "namespace": "staging",
        "cluster": "staging-cluster",
        "error_message": "Deployment rollout timeout: replicas not ready",
    }


@pytest.fixture
def k8s_deployment_progress_deadline_context() -> dict[str, Any]:
    """Deployment progress deadline exceeded."""
    return {
        "deployment_name": "worker-service",
        "namespace": "production",
        "cluster": "prod-eu",
        "error_message": "Deployment progress deadline exceeded: 1/5 replicas ready",
    }
