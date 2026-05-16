"""Pytest fixtures for platform scanner testing.

Provides access to mock Terraform and Kubernetes projects for plugin testing.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def terraform_fixtures_dir() -> Path:
    """Return path to mock Terraform project fixtures."""
    return Path(__file__).parent / "fixtures" / "terraform"


@pytest.fixture
def kubernetes_fixtures_dir() -> Path:
    """Return path to mock Kubernetes project fixtures."""
    return Path(__file__).parent / "fixtures" / "kubernetes"


@pytest.fixture
def terraform_main_config(terraform_fixtures_dir: Path) -> Path:
    """Return path to mock Terraform main.tf file."""
    return terraform_fixtures_dir / "main.tf"


@pytest.fixture
def terraform_vars_config(terraform_fixtures_dir: Path) -> Path:
    """Return path to mock Terraform variables.tf file."""
    return terraform_fixtures_dir / "variables.tf"


@pytest.fixture
def kubernetes_deployment(kubernetes_fixtures_dir: Path) -> Path:
    """Return path to mock Kubernetes deployment manifest."""
    return kubernetes_fixtures_dir / "deployment.yaml"


@pytest.fixture
def kubernetes_service(kubernetes_fixtures_dir: Path) -> Path:
    """Return path to mock Kubernetes service manifest."""
    return kubernetes_fixtures_dir / "service.yaml"


@pytest.fixture
def kubernetes_secret(kubernetes_fixtures_dir: Path) -> Path:
    """Return path to mock Kubernetes secret manifest."""
    return kubernetes_fixtures_dir / "secret.yaml"


# Terraform scenario fixtures
@pytest.fixture
def terraform_complex_dir(terraform_fixtures_dir: Path) -> Path:
    """Return path to Terraform complex scenario directory."""
    return terraform_fixtures_dir / "complex"


@pytest.fixture
def terraform_complex_main(terraform_complex_dir: Path) -> Path:
    """Return path to Terraform complex main.tf."""
    return terraform_complex_dir / "main.tf"


@pytest.fixture
def terraform_errors_dir(terraform_fixtures_dir: Path) -> Path:
    """Return path to Terraform with-errors scenario directory."""
    return terraform_fixtures_dir / "with-errors"


@pytest.fixture
def terraform_security_dir(terraform_fixtures_dir: Path) -> Path:
    """Return path to Terraform security-issues scenario directory."""
    return terraform_fixtures_dir / "security-issues"


# Kubernetes scenario fixtures
@pytest.fixture
def kubernetes_complex_dir(kubernetes_fixtures_dir: Path) -> Path:
    """Return path to Kubernetes complex scenario directory."""
    return kubernetes_fixtures_dir / "complex"


@pytest.fixture
def kubernetes_complex_manifests(kubernetes_complex_dir: Path) -> Path:
    """Return path to Kubernetes complex manifests.yaml."""
    return kubernetes_complex_dir / "manifests.yaml"


@pytest.fixture
def kubernetes_errors_dir(kubernetes_fixtures_dir: Path) -> Path:
    """Return path to Kubernetes with-errors scenario directory."""
    return kubernetes_fixtures_dir / "with-errors"


@pytest.fixture
def kubernetes_errors_manifests(kubernetes_errors_dir: Path) -> Path:
    """Return path to Kubernetes error manifests."""
    return kubernetes_errors_dir / "error-manifests.yaml"


@pytest.fixture
def kubernetes_security_dir(kubernetes_fixtures_dir: Path) -> Path:
    """Return path to Kubernetes security-issues scenario directory."""
    return kubernetes_fixtures_dir / "security-issues"


@pytest.fixture
def kubernetes_security_manifests(kubernetes_security_dir: Path) -> Path:
    """Return path to Kubernetes security issue manifests."""
    return kubernetes_security_dir / "security-issues.yaml"
