"""Terraform plan and validation fixtures.

Provides plan-related error scenarios including plan failures,
validation errors, and version mismatches.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def tf_plan_failed_context() -> dict[str, Any]:
    """Plan failed scenario."""
    return {
        "module": "networking",
        "plan_file": "/path/to/main.tf",
        "line_number": 42,
        "error_message": "Error: terraform plan failed - invalid configuration",
    }


@pytest.fixture
def tf_validation_failed_context() -> dict[str, Any]:
    """Validation failed scenario."""
    return {
        "module": "compute",
        "plan_file": "/path/to/compute.tf",
        "line_number": 15,
        "provider": "aws",
        "error_message": "Error: validation failed - required argument missing",
    }


@pytest.fixture
def tf_version_mismatch_context() -> dict[str, Any]:
    """Version mismatch scenario."""
    return {
        "module": "database",
        "plan_file": "/path/to/versions.tf",
        "error_message": "Error: version mismatch - Terraform 1.5 required, found 1.3",
    }
