"""Kubernetes configuration fixtures.

Provides config and secret error scenarios including missing configmaps
and secret not found errors.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def k8s_config_missing_context() -> dict[str, Any]:
    """ConfigMap not found scenario."""
    return {
        "config_name": "app-config",
        "namespace": "default",
        "cluster": "prod-us-west",
        "error_message": "ConfigMap not found",
    }


@pytest.fixture
def k8s_secret_not_found_context() -> dict[str, Any]:
    """Secret not found scenario."""
    return {
        "secret_name": "db-credentials",
        "namespace": "production",
        "cluster": "prod-eu",
        "error_message": "Secret not found",
    }


@pytest.fixture
def k8s_config_mount_failed_context() -> dict[str, Any]:
    """ConfigMap mount failed."""
    return {
        "pod_name": "app-pod",
        "config_name": "app-settings",
        "namespace": "staging",
        "cluster": "staging-cluster",
        "error_message": "ConfigMap mount failed: config not found",
    }


@pytest.fixture
def k8s_secret_mount_failed_context() -> dict[str, Any]:
    """Secret mount failed."""
    return {
        "pod_name": "secure-app",
        "secret_name": "tls-cert",
        "namespace": "production",
        "cluster": "prod-us-east",
        "error_message": "Secret mount failed: secret not found",
    }
