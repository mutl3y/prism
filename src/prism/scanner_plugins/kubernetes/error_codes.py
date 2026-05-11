"""Kubernetes-specific error codes and taxonomy.

Defines error code constants used throughout the Kubernetes plugin layer
for structured error envelope construction and categorization.

Error code range: 300-310 (reserved for Kubernetes platform).
"""

from __future__ import annotations

# Kubernetes error code constants
# Format: K8S_[DOMAIN]_[CONDITION]
# Range: 300-310

# Pod lifecycle errors (300-302)
K8S_POD_NOT_FOUND = "K8S_POD_NOT_FOUND"
K8S_POD_FAILED = "K8S_POD_FAILED"
K8S_POD_PENDING = "K8S_POD_PENDING"

# Deployment errors (303-304)
K8S_DEPLOYMENT_FAILED = "K8S_DEPLOYMENT_FAILED"
K8S_REPLICAS_NOT_READY = "K8S_REPLICAS_NOT_READY"

# Service errors (305-306)
K8S_SERVICE_NOT_FOUND = "K8S_SERVICE_NOT_FOUND"
K8S_SERVICE_ENDPOINT_EMPTY = "K8S_SERVICE_ENDPOINT_EMPTY"

# Configuration errors (307-308)
K8S_CONFIG_MISSING = "K8S_CONFIG_MISSING"
K8S_SECRET_NOT_FOUND = "K8S_SECRET_NOT_FOUND"

# Resource and RBAC errors (309-310)
K8S_QUOTA_EXCEEDED = "K8S_QUOTA_EXCEEDED"
K8S_RBAC_DENIED = "K8S_RBAC_DENIED"

# Dictionary of all Kubernetes error codes for reference
K8S_ERROR_CODES = {
    # Pod lifecycle
    K8S_POD_NOT_FOUND,
    K8S_POD_FAILED,
    K8S_POD_PENDING,
    # Deployments
    K8S_DEPLOYMENT_FAILED,
    K8S_REPLICAS_NOT_READY,
    # Services
    K8S_SERVICE_NOT_FOUND,
    K8S_SERVICE_ENDPOINT_EMPTY,
    # Config
    K8S_CONFIG_MISSING,
    K8S_SECRET_NOT_FOUND,
    # Resources
    K8S_QUOTA_EXCEEDED,
    K8S_RBAC_DENIED,
}

# Error code to category mapping (aligns with error_taxonomy.py)
K8S_ERROR_CATEGORY_MAP: dict[str, str] = {
    # Pod errors -> runtime
    K8S_POD_NOT_FOUND: "runtime",
    K8S_POD_FAILED: "runtime",
    K8S_POD_PENDING: "runtime",
    # Deployment errors -> runtime
    K8S_DEPLOYMENT_FAILED: "runtime",
    K8S_REPLICAS_NOT_READY: "runtime",
    # Service errors -> runtime
    K8S_SERVICE_NOT_FOUND: "runtime",
    K8S_SERVICE_ENDPOINT_EMPTY: "runtime",
    # Config errors -> io
    K8S_CONFIG_MISSING: "io",
    K8S_SECRET_NOT_FOUND: "io",
    # Resource/RBAC errors -> auth
    K8S_QUOTA_EXCEEDED: "api",
    K8S_RBAC_DENIED: "auth",
}

# Transient (recoverable) error codes
K8S_TRANSIENT_ERRORS = frozenset({
    K8S_POD_PENDING,
    K8S_REPLICAS_NOT_READY,
    K8S_SERVICE_ENDPOINT_EMPTY,
})
