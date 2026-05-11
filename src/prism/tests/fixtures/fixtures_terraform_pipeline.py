"""Fixtures for Terraform plugin tests."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def terraform_scan_options() -> dict[str, Any]:
    """Basic Terraform scan options for testing."""
    return {
        "role_path": "/tmp/terraform-module",
        "platform": "terraform",
    }


@pytest.fixture
def terraform_scan_context() -> dict[str, Any]:
    """Basic Terraform scan context for testing."""
    return {
        "plugin_platform": "terraform",
        "plugin_name": "terraform",
        "plugin_enabled": True,
    }


def build_terraform_scan_options(
    *,
    role_path: str = "/tmp/terraform-module",
    platform: str = "terraform",
    **extra: Any,
) -> dict[str, Any]:
    """Build Terraform scan options for testing."""
    options = {
        "role_path": role_path,
        "platform": platform,
    }
    options.update(extra)
    return options


def build_terraform_scan_context(
    *,
    plugin_platform: str = "terraform",
    plugin_name: str = "terraform",
    plugin_enabled: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """Build Terraform scan context for testing."""
    context = {
        "plugin_platform": plugin_platform,
        "plugin_name": plugin_name,
        "plugin_enabled": plugin_enabled,
    }
    context.update(extra)
    return context
