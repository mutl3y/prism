"""Terraform credential and sanitization fixtures.

Provides credential-related error scenarios and sensitive data
sanitization scenarios including tfstate scrubbing, credential removal,
and private key removal.
"""

from __future__ import annotations

import pytest
from typing import Any


@pytest.fixture
def tf_credential_failed_context() -> dict[str, Any]:
    """Credential authentication failed scenario."""
    return {
        "module": "production",
        "provider": "aws",
        "error_message": "Error: invalid credentials - AWS authentication failed",
    }


@pytest.fixture
def tf_tfstate_with_secrets_context() -> dict[str, Any]:
    """State file containing secrets to scrub."""
    return {
        "module": "database",
        "state_file": "/path/to/terraform.tfstate",
        "error_message": "State contains sensitive data: aws_access_key=AKIAIOSFODNN7EXAMPLE",
    }


@pytest.fixture
def tf_credential_in_plan_context() -> dict[str, Any]:
    """Credentials exposed in plan file."""
    return {
        "module": "infrastructure",
        "plan_file": "/path/to/main.tf",
        "line_number": 8,
        "error_message": "Credential found in plan: password='SuperSecret123'",
    }


@pytest.fixture
def tf_private_key_exposed_context() -> dict[str, Any]:
    """Private key exposed in configuration."""
    return {
        "module": "compute",
        "resource": "aws_instance.web",
        "plan_file": "/path/to/compute.tf",
        "error_message": "Private key exposed: -----BEGIN RSA PRIVATE KEY-----",
    }
