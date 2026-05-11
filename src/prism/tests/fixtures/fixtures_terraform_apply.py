"""Terraform apply and resource fixtures.

Provides apply-related error scenarios including apply failures,
resource errors, and state lock issues.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def tf_apply_failed_context() -> dict[str, Any]:
    """Apply failed scenario."""
    return {
        "module": "infrastructure",
        "resource": "aws_instance.web",
        "state_file": "/path/to/terraform.tfstate",
        "error_message": "Error: terraform apply failed - resource creation error",
    }


@pytest.fixture
def tf_state_lock_context() -> dict[str, Any]:
    """State lock acquisition failed."""
    return {
        "module": "storage",
        "state_file": "/path/to/terraform.tfstate",
        "error_message": "Error: state lock acquisition failed - locked by another operation",
    }


@pytest.fixture
def tf_resource_failed_context() -> dict[str, Any]:
    """Resource creation failed scenario."""
    return {
        "module": "networking",
        "resource": "azurerm_virtual_network.main",
        "provider": "azurerm",
        "error_message": "Error: resource creation failed - quota exceeded",
    }
