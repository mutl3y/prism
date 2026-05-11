"""Terraform module and dependency fixtures.

Provides module-related error scenarios including module not found,
version conflicts, and dependency cycles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


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


def build_nested_terraform_module_fixture(tmp_path: Path) -> Path:
    """Build a deterministic nested Terraform fixture tree for integration tests."""
    fixture_root = tmp_path / "terraform-nested"
    modules_root = fixture_root / "modules"
    compute_root = modules_root / "compute"
    networking_root = modules_root / "networking"

    compute_root.mkdir(parents=True)
    networking_root.mkdir(parents=True)

    (fixture_root / "README.md").write_text(
        "# Nested Terraform Fixture\n\nDeterministic nested Terraform tree for scanner tests.\n",
        encoding="utf-8",
    )
    (fixture_root / "main.tf").write_text(
        """
terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 5.0"
        }
    }
}

module "compute" {
    source = "./modules/compute"
}

module "networking" {
    source = "./modules/networking"
}

resource "aws_s3_bucket" "logs" {
    bucket = "example-logs"
}
""".strip() + "\n",
        encoding="utf-8",
    )
    (fixture_root / "variables.tf").write_text(
        """
variable "root_region" {
    description = "Root region"
    type        = string
    default     = "us-east-1"
}
""".strip() + "\n",
        encoding="utf-8",
    )
    (compute_root / "main.tf").write_text(
        """
resource "aws_instance" "app" {
    ami           = "ami-123456"
    instance_type = var.instance_type
}
""".strip() + "\n",
        encoding="utf-8",
    )
    (compute_root / "variables.tf").write_text(
        """
variable "instance_type" {
    description = "Compute instance type"
    type        = string
    default     = "t3.micro"
}
""".strip() + "\n",
        encoding="utf-8",
    )
    (networking_root / "main.tf").write_text(
        """
data "aws_vpc" "selected" {
    tags = {
        Name = "shared"
    }
}
""".strip() + "\n",
        encoding="utf-8",
    )
    (networking_root / "variables.tf").write_text(
        """
variable "vpc_cidr" {
    description = "VPC CIDR"
    type        = string
    default     = "10.0.0.0/16"
}
""".strip() + "\n",
        encoding="utf-8",
    )

    return fixture_root
