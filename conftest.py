"""Pytest bootstrap configuration for local source imports."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# Ensure tests import the in-repo package without requiring PYTHONPATH exports.
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Load K8s fixture modules
pytest_plugins = [
    "prism.tests.fixtures.fixtures_kubernetes_pods",
    "prism.tests.fixtures.fixtures_kubernetes_deployments",
    "prism.tests.fixtures.fixtures_kubernetes_services",
    "prism.tests.fixtures.fixtures_kubernetes_config",
    "prism.tests.fixtures.fixtures_kubernetes_resources",
    "prism.tests.fixtures.fixtures_kubernetes_sanitization",
    # Terraform fixture modules
    "prism.tests.fixtures.fixtures_terraform_plan",
    "prism.tests.fixtures.fixtures_terraform_apply",
    "prism.tests.fixtures.fixtures_terraform_state",
    "prism.tests.fixtures.fixtures_terraform_modules",
    "prism.tests.fixtures.fixtures_terraform_resources",
    "prism.tests.fixtures.fixtures_terraform_sanitization",
]


CORE_TEST_PREFIXES = (
    "test_blocker_fact_evaluator.py",
    "test_cache_",
    "test_dataload.py",
    "test_defaults.py",
    "test_di_",
    "test_error",
    "test_execution_request_builder.py",
    "test_feature_",
    "test_filter_scanner.py",
    "test_kernel.py",
    "test_kernel_plugin_runner.py",
    "test_policy_",
    "test_scanner_config",
    "test_scanner_context",
    "test_scanner_core_di.py",
    "test_scanner_core_small_surfaces.py",
    "test_task_",
    "test_underscore_policy_filter.py",
    "test_variable_discovery_pipeline.py",
)

PLUGIN_TEST_PREFIXES = (
    "test_ansible_task_traversal_bare.py",
    "test_comment_doc_plugin_resolution.py",
    "test_extract_defaults_ansible_ownership.py",
    "test_plugin_",
    "test_readme_renderer_plugin_",
    "test_readme_renderer_registry_wiring.py",
    "test_registry_reserved_platforms.py",
    "test_w2_hardwiring_audit.py",
)

INTEGRATION_TEST_PREFIXES = (
    "test_api_",
    "test_cli_",
    "test_gf2_collection_namespace_filtering.py",
    "test_gilfoyle_blockers_runtime.py",
    "test_import_style_guardrails.py",
    "test_legacy_retirement.py",
    "test_mp1_compatibility.py",
    "test_mp1_enforcement.py",
    "test_mp1_plugin_hardening.py",
    "test_package_",
    "test_platform_",
    "test_real_world_scans.py",
    "test_readme_parity.py",
    "test_scanner_parity.py",
    "test_t1_",
    "test_t2_",
    "test_t3_",
    "test_t4_",
    "test_test_output_safety_guard.py",
)

BOUNDARY_TEST_NAMES = {
    "test_cli_api_guardrails.py",
    "test_plugin_extract_boundary.py",
    "test_scanner_guardrails.py",
}


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for item in items:
        try:
            rel_path = item.path.relative_to(ROOT / "src" / "prism" / "tests")
            top_dir = rel_path.parts[0] if len(rel_path.parts) > 1 else ""
        except ValueError:
            top_dir = ""
        module_name = item.path.name
        if module_name in BOUNDARY_TEST_NAMES:
            item.add_marker(pytest.mark.boundary)

        if top_dir == "core" or module_name.startswith(CORE_TEST_PREFIXES):
            item.add_marker(pytest.mark.core)

        if top_dir == "plugins" or module_name.startswith(PLUGIN_TEST_PREFIXES):
            item.add_marker(pytest.mark.plugins)
            if (
                top_dir == "plugins"
                and len(item.path.parts) >= 2
                and item.path.parts[-2] == "ansible"
            ) or module_name.startswith("test_ansible_") or "ansible" in module_name:
                item.add_marker(pytest.mark.ansible)

        if (
            top_dir == "integration"
            or module_name.startswith(INTEGRATION_TEST_PREFIXES)
        ):
            item.add_marker(pytest.mark.integration)

        if "kubernetes" in module_name:
            item.add_marker(pytest.mark.kubernetes)
        if "terraform" in module_name:
            item.add_marker(pytest.mark.terraform)


# ============================================================================
# Phase 2: PolicyManager Module Test Fixtures
# ============================================================================


@pytest.fixture
def scan_options_fixture() -> dict[str, object]:
    """Create minimal scan_options for policy manager testing.

    Provides a complete ScanOptionsDict structure for policy resolution tests.
    """
    from prism.scanner_data.contracts_request import ScanOptionsDict

    opts: ScanOptionsDict = {
        "role_path": "/tmp/test-role",
        "role_name_override": None,
        "readme_config_path": None,
        "policy_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": None,
        "detailed_catalog": False,
        "include_task_parameters": False,
        "include_task_runbooks": False,
        "inline_task_runbooks": False,
        "include_collection_checks": False,
        "keep_unknown_style_sections": False,
        "adopt_heading_mode": None,
        "vars_seed_paths": None,
        "style_readme_path": None,
        "style_source_path": None,
        "style_guide_skeleton": False,
        "compare_role_path": None,
        "fail_on_unconstrained_dynamic_includes": None,
        "fail_on_yaml_like_task_annotations": None,
        "ignore_unresolved_internal_underscore_references": None,
    }
    return opts


@pytest.fixture
def di_container_fixture(scan_options_fixture: dict[str, object]) -> Any:
    """Create a DIContainer for policy manager integration tests.

    Returns a fully initialized container with policy manager and registry
    factories available for testing.
    """
    from prism.scanner_core.di import DIContainer

    return DIContainer(
        role_path="/tmp/test-role",
        scan_options=scan_options_fixture,  # type: ignore[arg-type]
    )


@pytest.fixture
def policy_registry_fixture() -> Any:
    """Create a FallbackPolicyRegistry mock for testing (Wave 0 stubs).

    Returns a mock registry since Wave 0 implementations raise NotImplementedError.
    Tests can inject real implementations in Wave 1+.
    """

    class MockPolicyRegistry:
        """Mock registry for Wave 0 tests (before stub implementation)."""

        def __init__(self) -> None:
            self.policies: dict[str, dict[str, Any]] = {}
            self.default_platform_key: str | None = None

        def get_default_policy(self, policy_type: str) -> dict[str, Any]:
            return self.policies.get(policy_type, {})

        def get_registry_dict(self) -> dict[str, dict[str, Any]]:
            return self.policies

    return MockPolicyRegistry()


@pytest.fixture
def policy_manager_fixture() -> Any:
    """Create a PolicyManager mock for testing (Wave 0 stubs).

    Returns a mock manager since Wave 0 implementations raise NotImplementedError.
    Tests can inject real implementations in Wave 1+.
    """

    class MockPolicyManager:
        """Mock manager for Wave 0 tests (before stub implementation)."""

        def __init__(self, registry: Any = None) -> None:
            self.registry = registry
            self.overrides: dict[str, Any] = {}

        def resolve_prepared_bundle(self, *, scan_options: dict[str, object]) -> Any:
            return {}

        def override_task_line_policy(self, policy: Any) -> None:
            self.overrides["task_line"] = policy

    return MockPolicyManager()


@pytest.fixture
def mock_task_line_policy() -> dict[str, Any]:
    """Create a mock task line parsing policy for override testing."""
    return {
        "type": "task_line_parsing",
        "description": "Mock task line policy",
        "version": "1.0.0",
    }


@pytest.fixture
def mock_annotation_policy() -> dict[str, Any]:
    """Create a mock task annotation policy for override testing."""
    return {
        "type": "task_annotation",
        "description": "Mock annotation policy",
        "version": "1.0.0",
    }


@pytest.fixture
def mock_traversal_policy() -> dict[str, Any]:
    """Create a mock task traversal policy for override testing."""
    return {
        "type": "task_traversal",
        "description": "Mock traversal policy",
        "version": "1.0.0",
    }


@pytest.fixture
def mock_variable_extractor_policy() -> dict[str, Any]:
    """Create a mock variable extractor policy for override testing."""
    return {
        "type": "variable_extractor",
        "description": "Mock variable extractor policy",
        "version": "1.0.0",
    }


@pytest.fixture
def mock_yaml_parsing_policy() -> dict[str, Any]:
    """Create a mock YAML parsing policy for override testing."""
    return {
        "type": "yaml_parsing",
        "description": "Mock YAML parsing policy",
        "version": "1.0.0",
    }


@pytest.fixture
def mock_jinja_analysis_policy() -> dict[str, Any]:
    """Create a mock Jinja analysis policy for override testing."""
    return {
        "type": "jinja_analysis",
        "description": "Mock Jinja analysis policy",
        "version": "1.0.0",
    }


@pytest.fixture
def mock_variable_extractor_policy() -> dict[str, Any]:
    """Create a mock variable extractor policy for testing."""
    return {
        "type": "variable_extractor",
        "description": "Mock variable extractor policy",
        "version": "1.0.0",
    }


@pytest.fixture
def mock_yaml_parsing_policy() -> dict[str, Any]:
    """Create a mock YAML parsing policy for testing."""
    return {
        "type": "yaml_parsing",
        "description": "Mock YAML parsing policy",
        "version": "1.0.0",
    }


@pytest.fixture
def policy_overrides_fixture() -> dict[str, dict[str, Any]]:
    """Create a policy overrides dict for testing override injection."""
    return {
        "task_line_parsing": {
            "type": "task_line_parsing",
            "override": True,
        },
        "task_annotation": {
            "type": "task_annotation",
            "override": True,
        },
        "task_traversal": {
            "type": "task_traversal",
            "override": True,
        },
    }


@pytest.fixture
def mock_prepared_bundle_fixture() -> dict[str, object]:
    """Create a mock prepared policy bundle for testing."""
    return {
        "task_line_parsing": {"type": "task_line_parsing"},
        "jinja_analysis": {"type": "jinja_analysis"},
        "task_traversal": {"type": "task_traversal"},
        "yaml_parsing": {"type": "yaml_parsing"},
        "variable_extractor": {"type": "variable_extractor"},
        "task_annotation_parsing": {"type": "task_annotation_parsing"},
        "comment_doc_marker_prefix": "#",
        "ignore_unresolved_internal_underscore_references": False,
    }


@pytest.fixture
def policy_overrides_fixture(
    mock_task_line_policy: dict[str, Any],
    mock_annotation_policy: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Create a complete policy overrides dict for testing.

    Returns a dict of policy type to policy implementation for injection testing.
    """
    return {
        "task_line_parsing": mock_task_line_policy,
        "task_annotation": mock_annotation_policy,
    }
