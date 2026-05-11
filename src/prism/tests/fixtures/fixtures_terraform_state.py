"""Terraform state and backend fixtures.

Provides state-related error scenarios including state corruption,
backend failures, and remote state errors.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def tf_state_corrupted_context() -> dict[str, Any]:
    """State file corrupted scenario."""
    return {
        "module": "production",
        "state_file": "/path/to/terraform.tfstate",
        "error_message": "Error: state file corrupted - invalid JSON format",
    }


@pytest.fixture
def tf_backend_failed_context() -> dict[str, Any]:
    """Backend initialization failed."""
    return {
        "module": "infrastructure",
        "state_file": "s3://bucket/terraform.tfstate",
        "provider": "aws",
        "error_message": "Error: backend initialization failed - S3 bucket not accessible",
    }


@pytest.fixture
def tf_remote_state_error_context() -> dict[str, Any]:
    """Remote state access error."""
    return {
        "module": "networking",
        "state_file": "azurerm://storage/terraform.tfstate",
        "provider": "azurerm",
        "error_message": "Error: remote state access failed - storage account not found",
    }
