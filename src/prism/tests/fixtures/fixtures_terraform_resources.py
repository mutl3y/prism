"""Terraform resource and configuration fixtures.

Provides resource-specific error scenarios including syntax errors,
interpolation failures, and invalid arguments.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def tf_resource_syntax_error_context() -> dict[str, Any]:
    """Resource syntax error scenario."""
    return {
        "module": "compute",
        "resource": "aws_instance.web",
        "plan_file": "/path/to/compute.tf",
        "line_number": 25,
        "error_message": "Error: resource syntax error - unexpected token",
    }


@pytest.fixture
def tf_interpolation_error_context() -> dict[str, Any]:
    """Interpolation error scenario."""
    return {
        "module": "networking",
        "resource": "aws_security_group.web",
        "plan_file": "/path/to/network.tf",
        "line_number": 18,
        "error_message": "Error: interpolation error - variable not defined",
    }


@pytest.fixture
def tf_argument_invalid_context() -> dict[str, Any]:
    """Invalid argument scenario."""
    return {
        "module": "storage",
        "resource": "google_storage_bucket.data",
        "plan_file": "/path/to/storage.tf",
        "line_number": 12,
        "provider": "google",
        "error_message": "Error: invalid argument - location is required",
    }
