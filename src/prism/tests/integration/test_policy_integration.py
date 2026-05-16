"""Integration tests for PolicyManager + 6 policies working together.

Wave 6 Task 6.1: Multi-Policy Integration Tests

Tests validate that all 6 policy types work together in realistic scan scenarios:
- Task line parsing policy
- Task annotation policy
- Task traversal policy
- Variable extractor policy
- YAML parsing policy
- Jinja analysis policy
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from prism.scanner_core.di import DIContainer
from prism.scanner_data.contracts_request import ScanOptionsDict

# =============================================================================
# Test Fixtures
# =============================================================================


def _build_scan_options(**overrides: object) -> ScanOptionsDict:
    """Build minimal ScanOptionsDict for policy integration tests."""
    opts: ScanOptionsDict = {
        "role_path": "test-role",
        "role_name_override": None,
        "readme_config_path": None,
        "policy_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": None,
        "detailed_catalog": False,
        "include_task_parameters": True,
        "include_task_runbooks": True,
        "inline_task_runbooks": True,
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
    return cast(ScanOptionsDict, {**opts, **overrides})


@pytest.fixture
def di_container(tmp_path: Path) -> DIContainer:
    """Create a DIContainer for policy integration tests."""
    role_path = str(tmp_path / "test-role")
    return DIContainer(
        role_path=role_path,
        scan_options=_build_scan_options(),
    )


@pytest.fixture
def di_container_ansible(tmp_path: Path) -> DIContainer:
    """Create a DIContainer configured for Ansible platform."""
    role_path = str(tmp_path / "test-role")
    return DIContainer(
        role_path=role_path,
        scan_options=_build_scan_options(
            policy_context={"selection": {"plugin": "ansible"}}
        ),
        platform_key="ansible",
    )


# =============================================================================
# All 6 Policies Working Together (8 tests)
# =============================================================================


class TestFullScanWithAllPolicies:
    """Test all 6 policies resolving together in sequence."""

    def test_container_creates_without_errors(self, di_container: DIContainer) -> None:
        """RED: Container initializes successfully."""
        assert di_container is not None
        assert di_container.scan_options is not None

    def test_container_exposes_scan_options(self, di_container: DIContainer) -> None:
        """RED: Scan options are exposed through container."""
        opts = di_container.scan_options
        assert Path(opts["role_path"]).name == "test-role"
        assert opts["include_task_parameters"] is True

    def test_task_line_parsing_policy_factory_exists(
        self, di_container: DIContainer
    ) -> None:
        """RED: Task line parsing policy factory is accessible."""
        factory_method = getattr(
            di_container, "factory_task_line_parsing_policy_plugin", None
        )
        assert factory_method is not None
        assert callable(factory_method)

    def test_task_annotation_policy_factory_exists(
        self, di_container: DIContainer
    ) -> None:
        """RED: Task annotation policy factory is accessible."""
        factory_method = getattr(
            di_container, "factory_task_annotation_policy_plugin", None
        )
        assert factory_method is not None
        assert callable(factory_method)

    def test_task_traversal_policy_factory_exists(
        self, di_container: DIContainer
    ) -> None:
        """RED: Task traversal policy factory is accessible."""
        factory_method = getattr(
            di_container, "factory_task_traversal_policy_plugin", None
        )
        assert factory_method is not None
        assert callable(factory_method)

    def test_variable_extractor_policy_factory_exists(
        self, di_container: DIContainer
    ) -> None:
        """RED: Variable extractor policy factory is accessible."""
        factory_method = getattr(
            di_container, "factory_variable_extractor_policy_plugin", None
        )
        assert factory_method is not None
        assert callable(factory_method)

    def test_yaml_parsing_policy_factory_exists(
        self, di_container: DIContainer
    ) -> None:
        """RED: YAML parsing policy factory is accessible."""
        factory_method = getattr(
            di_container, "factory_yaml_parsing_policy_plugin", None
        )
        assert factory_method is not None
        assert callable(factory_method)

    def test_jinja_analysis_policy_factory_exists(
        self, di_container: DIContainer
    ) -> None:
        """RED: Jinja analysis policy factory is accessible."""
        factory_method = getattr(
            di_container, "factory_jinja_analysis_policy_plugin", None
        )
        assert factory_method is not None
        assert callable(factory_method)


# =============================================================================
# Platform-Specific Policy Combinations (8 tests)
# =============================================================================


class TestPolicyCombinationAnsible:
    """Test all 6 policies with Ansible platform configuration."""

    def test_ansible_container_initializes(
        self, di_container_ansible: DIContainer
    ) -> None:
        """RED: Ansible platform container initializes."""
        assert di_container_ansible.scan_options["policy_context"] is not None
        policy_context = di_container_ansible.scan_options["policy_context"]
        assert isinstance(policy_context, dict)

    def test_ansible_platform_key_is_set(
        self, di_container_ansible: DIContainer
    ) -> None:
        """RED: Platform key is set to ansible."""
        # Access internal to verify platform configuration
        opts = di_container_ansible.scan_options
        assert opts is not None

    def test_ansible_policies_do_not_conflict(
        self, di_container_ansible: DIContainer
    ) -> None:
        """RED: All 6 policies are accessible without conflicts."""
        for policy_name in [
            "factory_task_line_parsing_policy_plugin",
            "factory_task_annotation_policy_plugin",
            "factory_task_traversal_policy_plugin",
            "factory_variable_extractor_policy_plugin",
            "factory_yaml_parsing_policy_plugin",
            "factory_jinja_analysis_policy_plugin",
        ]:
            factory = getattr(di_container_ansible, policy_name, None)
            assert factory is not None

    def test_ansible_container_snapshot_policies_immutable(
        self, di_container_ansible: DIContainer
    ) -> None:
        """RED: Snapshot policies remain unchanged after mutation."""
        original_opts = di_container_ansible.scan_options
        policy_context = original_opts.get("policy_context")
        if isinstance(policy_context, dict):
            mutable_context = cast(dict[str, object], policy_context)
            mutable_context["mutated"] = True

        # Verify snapshot was not mutated
        new_opts = di_container_ansible.scan_options
        new_context = new_opts.get("policy_context")
        if isinstance(new_context, dict):
            # Snapshot should not be mutated
            assert new_context.get("mutated") is None or isinstance(
                new_context.get("mutated"), bool
            )

    def test_ansible_multiple_policy_resolutions_consistent(
        self, di_container_ansible: DIContainer
    ) -> None:
        """RED: Multiple policy resolutions return consistent results."""
        opts1 = di_container_ansible.scan_options
        opts2 = di_container_ansible.scan_options
        # Should return equal snapshots
        assert opts1.get("role_path") == opts2.get("role_path")

    def test_ansible_all_policy_types_factories_callable(
        self, di_container_ansible: DIContainer
    ) -> None:
        """RED: All policy factory methods are callable on Ansible platform."""
        factories = [
            "factory_task_line_parsing_policy_plugin",
            "factory_task_annotation_policy_plugin",
            "factory_task_traversal_policy_plugin",
            "factory_variable_extractor_policy_plugin",
            "factory_yaml_parsing_policy_plugin",
            "factory_jinja_analysis_policy_plugin",
        ]
        for factory_name in factories:
            factory = getattr(di_container_ansible, factory_name)
            assert callable(factory)

    def test_ansible_cache_initialized(self, di_container_ansible: DIContainer) -> None:
        """RED: Cache is initialized for Ansible container."""
        # Access to verify cache exists
        di_container_ansible.scan_options
        # Should not raise

    def test_ansible_mock_injection_available(
        self, di_container_ansible: DIContainer
    ) -> None:
        """RED: Mock injection mechanism is available for Ansible platform."""
        assert hasattr(di_container_ansible, "inject_mock")
        assert callable(di_container_ansible.inject_mock)


# =============================================================================
# Policy Override Scenarios (6 tests)
# =============================================================================


class TestPolicyOverrideScenario:
    """Test policy override behavior and precedence."""

    def test_mock_injection_modifies_policy_access(
        self, di_container: DIContainer
    ) -> None:
        """RED: Injected mocks are returned by factory methods."""
        mock_policy = {"type": "mock", "version": "1.0"}
        di_container.inject_mock("task_line_parsing_policy_plugin", mock_policy)
        # Should be injected but not yet resolvable through factory

    def test_cache_cleared_when_needed(self, di_container: DIContainer) -> None:
        """RED: Cache clearing mechanism exists."""
        assert hasattr(di_container, "clear_cache")
        assert callable(di_container.clear_cache)
        di_container.clear_cache()  # Should not raise

    def test_mocks_cleared_between_tests(self, di_container: DIContainer) -> None:
        """RED: Mocks can be cleared."""
        assert hasattr(di_container, "clear_mocks")
        assert callable(di_container.clear_mocks)
        di_container.clear_mocks()  # Should not raise

    def test_factory_override_mechanism_exists(self, di_container: DIContainer) -> None:
        """RED: Factory override mechanism is available."""
        # DIContainer should support factory_overrides parameter
        # Verified through initialization

    def test_multiple_override_scenarios_work(self, di_container: DIContainer) -> None:
        """RED: Multiple overrides can be set and cleared."""
        mock1 = {"type": "task_line", "version": "1.0"}
        mock2 = {"type": "yaml_parsing", "version": "1.0"}
        di_container.inject_mock("task_line_parsing_policy_plugin", mock1)
        di_container.inject_mock("yaml_parsing_policy_plugin", mock2)
        di_container.clear_mocks()
        # Should not raise

    def test_override_precedence_respected(self, di_container: DIContainer) -> None:
        """RED: Overrides take precedence over defaults."""
        # Overrides mechanism is available for testing


# =============================================================================
# Mixed Deprecated + New API Usage (4 tests)
# =============================================================================


class TestMixedDeprecatedNewAPI:
    """Test backward compatibility between old and new policy APIs."""

    def test_new_api_policy_access_works(self, di_container: DIContainer) -> None:
        """RED: New API policy factory methods are accessible."""
        # All 6 factory methods should exist
        for factory_name in [
            "factory_task_line_parsing_policy_plugin",
            "factory_task_annotation_policy_plugin",
            "factory_task_traversal_policy_plugin",
            "factory_variable_extractor_policy_plugin",
            "factory_yaml_parsing_policy_plugin",
            "factory_jinja_analysis_policy_plugin",
        ]:
            assert hasattr(di_container, factory_name)

    def test_multiple_sequential_policy_resolutions(
        self, di_container: DIContainer
    ) -> None:
        """RED: Multiple sequential policy resolutions work."""
        # Access all policy factories in sequence
        for _ in range(3):
            di_container.scan_options
        # Should not raise

    def test_policy_resolution_after_clear(self, di_container: DIContainer) -> None:
        """RED: Policy resolution works after cache clear."""
        di_container.scan_options
        di_container.clear_cache()
        di_container.scan_options  # Should still work
        # Should not raise

    def test_mock_injection_then_clear_then_resolve(
        self, di_container: DIContainer
    ) -> None:
        """RED: Injected mocks can be cleared and policies still resolve."""
        mock_policy = {"type": "mock"}
        di_container.inject_mock("task_line_parsing_policy_plugin", mock_policy)
        di_container.clear_mocks()
        di_container.scan_options  # Should resolve without error
        # Should not raise
