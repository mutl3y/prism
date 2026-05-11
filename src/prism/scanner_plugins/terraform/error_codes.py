"""Terraform-specific error codes and taxonomy.

Defines error code constants used throughout the Terraform plugin layer
for structured error envelope construction and categorization.

Error code range: 400-410 (reserved for Terraform platform).
"""

from __future__ import annotations

# Terraform error code constants
# Format: TF_[DOMAIN]_[CONDITION]
# Range: 400-410

# Plan and validation errors (400-402)
TF_PLAN_FAILED = "TF_PLAN_FAILED"
TF_VALIDATION_FAILED = "TF_VALIDATION_FAILED"
TF_VERSION_FAILED = "TF_VERSION_FAILED"

# Apply and resource errors (403-405)
TF_APPLY_FAILED = "TF_APPLY_FAILED"
TF_RESOURCE_FAILED = "TF_RESOURCE_FAILED"
TF_MODULE_NOT_FOUND = "TF_MODULE_NOT_FOUND"

# State and backend errors (406-408)
TF_STATE_CORRUPTED = "TF_STATE_CORRUPTED"
TF_BACKEND_FAILED = "TF_BACKEND_FAILED"
TF_LOCK_FAILED = "TF_LOCK_FAILED"

# Credential and authentication errors (409-410)
TF_CREDENTIAL_FAILED = "TF_CREDENTIAL_FAILED"

# Dictionary of all Terraform error codes for reference
TF_ERROR_CODES = {
    # Plan/validation
    TF_PLAN_FAILED,
    TF_VALIDATION_FAILED,
    TF_VERSION_FAILED,
    # Apply/resources
    TF_APPLY_FAILED,
    TF_RESOURCE_FAILED,
    TF_MODULE_NOT_FOUND,
    # State/backend
    TF_STATE_CORRUPTED,
    TF_BACKEND_FAILED,
    TF_LOCK_FAILED,
    # Credentials
    TF_CREDENTIAL_FAILED,
}

# Error code to category mapping (aligns with error_taxonomy.py)
TF_ERROR_CATEGORY_MAP: dict[str, str] = {
    # Plan/validation errors -> parser
    TF_PLAN_FAILED: "parser",
    TF_VALIDATION_FAILED: "parser",
    TF_VERSION_FAILED: "runtime",
    # Apply/resource errors -> runtime
    TF_APPLY_FAILED: "runtime",
    TF_RESOURCE_FAILED: "runtime",
    TF_MODULE_NOT_FOUND: "io",
    # State/backend errors -> io
    TF_STATE_CORRUPTED: "io",
    TF_BACKEND_FAILED: "io",
    TF_LOCK_FAILED: "io",
    # Credential errors -> auth
    TF_CREDENTIAL_FAILED: "auth",
}

# Transient (recoverable) error codes
TF_TRANSIENT_ERRORS = frozenset(
    {
        TF_LOCK_FAILED,
        TF_BACKEND_FAILED,
    }
)
