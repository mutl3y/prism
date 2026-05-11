"""Terraform module and dependency fixtures.

Provides module-related error scenarios including module not found,
version conflicts, and dependency cycles.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def tf_module_not_found_context() -> dict[str, Any]:
    """Module not found scenario."""
    return {
        "module": "networking",
        "plan_file": "/path/to/main.tf",
        "error_message": "Error: module not found - ./modules/vpc does not exist",
    }


@pytest.fixture
def tf_module_version_conflict_context() -> dict[str, Any]:
    """Module version conflict scenario."""
    return {
        "module": "compute",
        "plan_file": "/path/to/compute.tf",
        "error_message": "Error: module version conflict - required 2.0, found 1.5",
    }


@pytest.fixture
def tf_dependency_cycle_context() -> dict[str, Any]:
    """Dependency cycle detected."""
    return {
        "module": "infrastructure",
        "plan_file": "/path/to/main.tf",
        "error_message": "Error: dependency cycle detected - module A depends on B, B depends on A",
    }
