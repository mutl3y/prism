"""Kubernetes base fixtures for pod scenarios.

Provides pod-related error scenarios including pod not found,
pod failed, and pod pending states.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def k8s_pod_not_found_context() -> dict[str, Any]:
    """Pod not found scenario."""
    return {
        "pod_name": "nginx-7d8b49c9bd-abcde",
        "namespace": "default",
        "cluster": "prod-us-west",
        "error_message": "Error from server (NotFound): pods not found",
    }


@pytest.fixture
def k8s_pod_failed_context() -> dict[str, Any]:
    """Pod failed with CrashLoopBackOff."""
    return {
        "pod_name": "api-server-abc123",
        "namespace": "production",
        "cluster": "prod-eu",
        "error_message": "Pod failed: CrashLoopBackOff",
    }


@pytest.fixture
def k8s_pod_pending_context() -> dict[str, Any]:
    """Pod pending with ImagePullBackOff."""
    return {
        "pod_name": "worker-xyz789",
        "namespace": "staging",
        "cluster": "staging-cluster",
        "error_message": "Pod is pending: ImagePullBackOff",
    }


@pytest.fixture
def k8s_pod_oom_killed_context() -> dict[str, Any]:
    """Pod OOMKilled scenario."""
    return {
        "pod_name": "memory-intensive-pod",
        "namespace": "default",
        "cluster": "test-cluster",
        "error_message": "Pod failed: OOMKilled - container exceeded memory limit",
    }


@pytest.fixture
def k8s_pod_evicted_context() -> dict[str, Any]:
    """Pod evicted due to node pressure."""
    return {
        "pod_name": "batch-job-123",
        "namespace": "batch",
        "cluster": "prod-us-east",
        "error_message": "Pod evicted: node pressure",
    }
