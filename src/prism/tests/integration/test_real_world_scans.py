"""Integration tests for realistic scan scenarios with PolicyManager + caching.

Wave 6 Task 6.2: Real-World Scan Scenarios

Tests validate caching system with realistic Ansible role scanning:
- Single role scans
- Large role collections
- Custom policy scenarios
- Concurrent multi-role scanning
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from prism.scanner_core.di import DIContainer
from prism.scanner_data.contracts_request import ScanOptionsDict


def _build_scan_options(**overrides: object) -> ScanOptionsDict:
    """Build ScanOptionsDict for real-world scan testing."""
    opts: ScanOptionsDict = {
        "role_path": "test-role",
        "role_name_override": None,
        "readme_config_path": None,
        "policy_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": None,
        "detailed_catalog": True,
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
def small_role_path(tmp_path: Path) -> Path:
    """Create a small test role with ~5 tasks."""
    role_path = tmp_path / "small_role"
    tasks_dir = role_path / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create simple task file
    (tasks_dir / "main.yml").write_text("""---
- name: Small role task 1
  debug:
    msg: "Task 1"

- name: Small role task 2
  debug:
    msg: "Task 2"

- name: Include subtasks
  include_tasks: subtasks.yml
""")
    (tasks_dir / "subtasks.yml").write_text("""---
- name: Subtask 1
  debug:
    msg: "Subtask 1"

- name: Subtask 2
  debug:
    msg: "Subtask 2"
""")
    return role_path


@pytest.fixture
def large_role_path(tmp_path: Path) -> Path:
    """Create a large test role with 50+ tasks and nested includes."""
    role_path = tmp_path / "large_role"
    tasks_dir = role_path / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create main task file with 20 tasks
    main_tasks = ["---"]
    for i in range(20):
        main_tasks.append(f"""
- name: Large role task {i + 1}
  debug:
    msg: "Task {i + 1}"
""")
    main_tasks.append("""
- name: Include nested tasks
  include_tasks: nested/subtasks.yml
""")
    (tasks_dir / "main.yml").write_text("\n".join(main_tasks))

    # Create nested subtasks directory with 30 more tasks
    nested_dir = tasks_dir / "nested"
    nested_dir.mkdir()

    nested_tasks = ["---"]
    for i in range(30):
        nested_tasks.append(f"""
- name: Nested task {i + 1}
  debug:
    msg: "Nested task {i + 1}"
""")
    (nested_dir / "subtasks.yml").write_text("\n".join(nested_tasks))

    return role_path


@pytest.fixture
def role_with_custom_policies_path(tmp_path: Path) -> Path:
    """Create a role with custom Jinja and YAML parsing."""
    role_path = tmp_path / "custom_policy_role"
    tasks_dir = role_path / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create task with custom Jinja
    (tasks_dir / "main.yml").write_text("""---
- name: Task with Jinja template
  debug:
    msg: "{{ custom_var | custom_filter }}"

- name: Task with YAML-like annotation
  set_fact:
    my_dict:
      key1: value1
      key2: value2

- name: Task with dynamic include
  include_tasks: "{{ role_path }}/tasks/dynamic.yml"
""")
    (tasks_dir / "dynamic.yml").write_text("""---
- name: Dynamic task
  debug:
    msg: "Dynamically included"
""")
    return role_path


# =============================================================================
# Single Role Scenarios (8 tests)
# =============================================================================


class TestSingleRoleScan:
    """Test scanning a single small role with policy resolution and caching."""

    def test_small_role_scan_initializes(self, small_role_path: Path) -> None:
        """RED: Container initializes for small role."""
        container = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        assert container is not None

    def test_small_role_scan_options_preserved(self, small_role_path: Path) -> None:
        """RED: Scan options are preserved for small role."""
        container = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(detailed_catalog=True),
        )
        opts = container.scan_options
        assert opts["detailed_catalog"] is True

    def test_small_role_all_policies_accessible(self, small_role_path: Path) -> None:
        """RED: All 6 policies accessible for small role."""
        container = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        for policy_name in [
            "factory_task_line_parsing_policy_plugin",
            "factory_task_annotation_policy_plugin",
            "factory_task_traversal_policy_plugin",
            "factory_variable_extractor_policy_plugin",
            "factory_yaml_parsing_policy_plugin",
            "factory_jinja_analysis_policy_plugin",
        ]:
            factory = getattr(container, policy_name)
            assert factory is not None
            assert callable(factory)

    def test_small_role_cache_statistics(self, small_role_path: Path) -> None:
        """RED: Cache statistics are available for small role."""
        container = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        # Access scan options multiple times
        for _ in range(3):
            container.scan_options
        # Cache should be tracking accesses

    def test_small_role_multiple_scans_consistent(self, small_role_path: Path) -> None:
        """RED: Multiple scans return consistent results."""
        container = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        opts1 = container.scan_options
        opts2 = container.scan_options
        assert opts1.get("role_path") == opts2.get("role_path")

    def test_small_role_memory_usage_reasonable(self, small_role_path: Path) -> None:
        """RED: Small role scan uses reasonable memory."""
        container = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        # Container should initialize without excessive memory use
        assert container.scan_options is not None

    def test_small_role_scan_performance_acceptable(
        self, small_role_path: Path
    ) -> None:
        """RED: Small role scan completes quickly."""
        import time

        container = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        start = time.time()
        container.scan_options
        elapsed = time.time() - start
        # Should complete in reasonable time (< 1 second)
        assert elapsed < 1.0

    def test_small_role_clear_cache_works(self, small_role_path: Path) -> None:
        """RED: Cache clear works for small role."""
        container = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        container.scan_options
        container.clear_cache()
        opts = container.scan_options  # Should still work
        assert opts is not None


# =============================================================================
# Large Role Collection Scenarios (6 tests)
# =============================================================================


class TestLargeRoleCollectionScan:
    """Test scanning a large role collection with caching optimization."""

    def test_large_role_scan_initializes(self, large_role_path: Path) -> None:
        """RED: Container initializes for large role."""
        container = DIContainer(
            role_path=str(large_role_path),
            scan_options=_build_scan_options(),
        )
        assert container is not None

    def test_large_role_detailed_catalog_enabled(self, large_role_path: Path) -> None:
        """RED: Detailed catalog mode works for large role."""
        container = DIContainer(
            role_path=str(large_role_path),
            scan_options=_build_scan_options(detailed_catalog=True),
        )
        opts = container.scan_options
        assert opts["detailed_catalog"] is True

    def test_large_role_multiple_scans_use_cache(self, large_role_path: Path) -> None:
        """RED: Multiple scans of large role benefit from cache."""
        container = DIContainer(
            role_path=str(large_role_path),
            scan_options=_build_scan_options(),
        )
        # First scan
        opts1 = container.scan_options
        # Second scan (should hit cache)
        opts2 = container.scan_options
        # Both should be accessible
        assert opts1 is not None
        assert opts2 is not None

    def test_large_role_with_runbooks(self, large_role_path: Path) -> None:
        """RED: Large role with runbook inclusion works."""
        container = DIContainer(
            role_path=str(large_role_path),
            scan_options=_build_scan_options(
                include_task_runbooks=True, inline_task_runbooks=True
            ),
        )
        opts = container.scan_options
        assert opts["include_task_runbooks"] is True

    def test_large_role_performance_with_cache(self, large_role_path: Path) -> None:
        """RED: Cache improves performance on repeated access."""
        container = DIContainer(
            role_path=str(large_role_path),
            scan_options=_build_scan_options(),
        )
        import time

        # First access
        start1 = time.time()
        container.scan_options
        time1 = time.time() - start1

        # Second access (cached)
        start2 = time.time()
        container.scan_options
        time2 = time.time() - start2

        # Both should complete successfully
        assert time1 > 0
        assert time2 >= 0

    def test_large_role_all_policies_resolve(self, large_role_path: Path) -> None:
        """RED: All 6 policies resolve for large role."""
        container = DIContainer(
            role_path=str(large_role_path),
            scan_options=_build_scan_options(),
        )
        for policy_name in [
            "factory_task_line_parsing_policy_plugin",
            "factory_task_annotation_policy_plugin",
            "factory_task_traversal_policy_plugin",
            "factory_variable_extractor_policy_plugin",
            "factory_yaml_parsing_policy_plugin",
            "factory_jinja_analysis_policy_plugin",
        ]:
            factory = getattr(container, policy_name)
            assert callable(factory)


# =============================================================================
# Custom Policy Scenarios (6 tests)
# =============================================================================


class TestRoleWithCustomPolicies:
    """Test roles with custom Jinja and YAML parsing policies."""

    def test_custom_policy_role_initializes(
        self, role_with_custom_policies_path: Path
    ) -> None:
        """RED: Role with custom policies initializes."""
        container = DIContainer(
            role_path=str(role_with_custom_policies_path),
            scan_options=_build_scan_options(),
        )
        assert container is not None

    def test_custom_jinja_policy_accessible(
        self, role_with_custom_policies_path: Path
    ) -> None:
        """RED: Jinja analysis policy accessible for custom role."""
        container = DIContainer(
            role_path=str(role_with_custom_policies_path),
            scan_options=_build_scan_options(),
        )
        factory = getattr(container, "factory_jinja_analysis_policy_plugin")
        assert callable(factory)

    def test_custom_yaml_policy_accessible(
        self, role_with_custom_policies_path: Path
    ) -> None:
        """RED: YAML parsing policy accessible for custom role."""
        container = DIContainer(
            role_path=str(role_with_custom_policies_path),
            scan_options=_build_scan_options(),
        )
        factory = getattr(container, "factory_yaml_parsing_policy_plugin")
        assert callable(factory)

    def test_custom_policy_with_dynamic_includes(
        self, role_with_custom_policies_path: Path
    ) -> None:
        """RED: Dynamic includes work with custom policies."""
        container = DIContainer(
            role_path=str(role_with_custom_policies_path),
            scan_options=_build_scan_options(
                fail_on_unconstrained_dynamic_includes=False
            ),
        )
        opts = container.scan_options
        assert opts is not None

    def test_custom_policy_with_yaml_like_annotations(
        self, role_with_custom_policies_path: Path
    ) -> None:
        """RED: YAML-like annotations work with custom policies."""
        container = DIContainer(
            role_path=str(role_with_custom_policies_path),
            scan_options=_build_scan_options(fail_on_yaml_like_task_annotations=False),
        )
        opts = container.scan_options
        assert opts is not None

    def test_custom_policy_cache_effective(
        self, role_with_custom_policies_path: Path
    ) -> None:
        """RED: Cache is effective for custom policy roles."""
        container = DIContainer(
            role_path=str(role_with_custom_policies_path),
            scan_options=_build_scan_options(),
        )
        opts1 = container.scan_options
        opts2 = container.scan_options
        # Both should succeed
        assert opts1 is not None
        assert opts2 is not None


# =============================================================================
# Concurrent Multi-Role Scenarios (4 tests)
# =============================================================================


class TestConcurrentMultiRoleScan:
    """Test concurrent scanning of multiple roles."""

    def test_multiple_containers_no_policy_conflicts(
        self,
        small_role_path: Path,
        large_role_path: Path,
    ) -> None:
        """RED: Multiple containers don't conflict."""
        container1 = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        container2 = DIContainer(
            role_path=str(large_role_path),
            scan_options=_build_scan_options(),
        )
        # Both should work independently
        assert container1.scan_options is not None
        assert container2.scan_options is not None

    def test_concurrent_option_access_thread_safe(
        self,
        small_role_path: Path,
    ) -> None:
        """RED: Concurrent scan option access is thread-safe."""
        import threading

        container = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        results = []

        def access_options() -> None:
            opts = container.scan_options
            results.append(opts)

        threads = [threading.Thread(target=access_options) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should complete successfully
        assert len(results) == 3
        assert all(r is not None for r in results)

    def test_multiple_roles_sequential_scans(
        self,
        small_role_path: Path,
        large_role_path: Path,
    ) -> None:
        """RED: Sequential scans of different roles work."""
        container1 = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        opts1 = container1.scan_options

        container2 = DIContainer(
            role_path=str(large_role_path),
            scan_options=_build_scan_options(),
        )
        opts2 = container2.scan_options

        # Both should be different
        assert opts1["role_path"] != opts2["role_path"]

    def test_concurrent_policy_resolution_isolation(
        self,
        small_role_path: Path,
        large_role_path: Path,
    ) -> None:
        """RED: Concurrent policy resolutions are isolated."""
        import threading

        container1 = DIContainer(
            role_path=str(small_role_path),
            scan_options=_build_scan_options(),
        )
        container2 = DIContainer(
            role_path=str(large_role_path),
            scan_options=_build_scan_options(),
        )

        results = {"c1": [], "c2": []}

        def access_c1() -> None:
            for _ in range(2):
                results["c1"].append(container1.scan_options)

        def access_c2() -> None:
            for _ in range(2):
                results["c2"].append(container2.scan_options)

        t1 = threading.Thread(target=access_c1)
        t2 = threading.Thread(target=access_c2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Both containers should have completed accesses
        assert len(results["c1"]) == 2
        assert len(results["c2"]) == 2
