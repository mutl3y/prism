"""Kubernetes resource and RBAC fixtures.

Provides resource quota and RBAC error scenarios.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def k8s_quota_exceeded_context() -> dict[str, Any]:
    """Resource quota exceeded scenario."""
    return {
        "namespace": "production",
        "cluster": "prod-us-west",
        "error_message": "Resource quota exceeded: cannot create more pods",
    }


@pytest.fixture
def k8s_rbac_denied_context() -> dict[str, Any]:
    """RBAC access denied scenario."""
    return {
        "namespace": "secure-namespace",
        "cluster": "prod-eu",
        "error_message": "RBAC: access denied - insufficient permissions",
    }


@pytest.fixture
def k8s_cpu_quota_exceeded_context() -> dict[str, Any]:
    """CPU quota exceeded."""
    return {
        "namespace": "compute-intensive",
        "cluster": "prod-us-east",
        "error_message": "Resource quota exceeded: CPU limit reached",
    }


@pytest.fixture
def k8s_memory_quota_exceeded_context() -> dict[str, Any]:
    """Memory quota exceeded."""
    return {
        "namespace": "data-processing",
        "cluster": "prod-us-west",
        "error_message": "Resource quota exceeded: memory limit reached",
    }


@pytest.fixture
def k8s_pvc_quota_exceeded_context() -> dict[str, Any]:
    """PVC quota exceeded."""
    return {
        "namespace": "storage-heavy",
        "cluster": "prod-eu",
        "error_message": "Resource quota exceeded: PVC count limit reached",
    }
