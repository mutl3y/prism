"""Kubernetes service fixtures.

Provides service-related error scenarios including service not found
and endpoint errors.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def k8s_service_not_found_context() -> dict[str, Any]:
    """Service not found scenario."""
    return {
        "service_name": "api-service",
        "namespace": "default",
        "cluster": "prod-us-west",
        "error_message": "Service not found",
    }


@pytest.fixture
def k8s_service_endpoint_empty_context() -> dict[str, Any]:
    """Service has no endpoints."""
    return {
        "service_name": "backend-service",
        "namespace": "production",
        "cluster": "prod-eu",
        "error_message": "Service has no endpoints",
    }


@pytest.fixture
def k8s_service_selector_mismatch_context() -> dict[str, Any]:
    """Service selector doesn't match any pods."""
    return {
        "service_name": "worker-service",
        "namespace": "staging",
        "cluster": "staging-cluster",
        "error_message": "Service has no endpoints: selector mismatch",
    }


@pytest.fixture
def k8s_service_port_conflict_context() -> dict[str, Any]:
    """Service port conflict."""
    return {
        "service_name": "metrics-service",
        "namespace": "monitoring",
        "cluster": "prod-us-east",
        "error_message": "Service port conflict: port 8080 already in use",
    }
