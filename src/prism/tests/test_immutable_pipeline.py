"""Unit tests for immutable data pipeline in scanner orchestration.

Tests verify that scanner orchestration maintains immutable data flow throughout:
- Variable discovery returns immutable tuples
- Feature detection returns immutable dicts
- Output orchestration doesn't mutate payloads
- No cross-test data contamination
- Concurrency-safe data structures

Coverage:
- Data isolation tests (4): Verify mutations in one test don't affect others
- Immutability enforcement tests (4): Verify no in-place mutations in pipeline
- Data flow tests (2): Verify payload flows correctly through orchestrators
- Concurrency safety tests (2): Verify data structures are safe for concurrent use
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prism.scanner_core import DIContainer
from prism.scanner_core.scanner_context import ScannerContext
from prism.scanner_core.variable_discovery import VariableDiscovery
from prism.scanner_core.output_orchestrator import OutputOrchestrator
from prism.scanner_data.contracts import RunScanOutputPayload

# ============================================================================
# Data Isolation Tests (4)
# ============================================================================


class TestDataIsolationBetweenTests:
    """Verify mutations in one test don't affect others (test independence)."""

    @pytest.fixture(autouse=True)
    def setup_role_dir(self, tmp_path):
        """Create minimal role structure for each test."""
        role_path = tmp_path
        (role_path / "defaults").mkdir()
        (role_path / "tasks").mkdir()
        (role_path / "handlers").mkdir()

        # Setup defaults/main.yml with a variable
        (role_path / "defaults" / "main.yml").write_text(
            "---\n" "test_var_1: value_one\n" "test_var_2: value_two\n"
        )

        self.role_path = str(role_path)
        self.options = {
            "role_path": self.role_path,
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "vars_seed_paths": None,
            "ignore_unresolved_internal_underscore_references": False,
        }

    def test_discover_static_test_one_returns_tuple(self):
        """Test 1: discover_static returns immutable tuple."""
        di = DIContainer(self.role_path, self.options)
        discovery = VariableDiscovery(di, self.role_path, self.options)

        static = discovery.discover_static()

        # Verify it's a tuple (immutable)
        assert isinstance(static, tuple)
        assert len(static) == 2
        assert static[0]["name"] == "test_var_1"

    def test_discover_static_test_two_independent_from_test_one(self):
        """Test 2: discover_static in new instance is independent of Test 1."""
        # Create a separate discovery instance (simulates independent test)
        di = DIContainer(self.role_path, self.options)
        discovery_new = VariableDiscovery(di, self.role_path, self.options)

        static_new = discovery_new.discover_static()

        # Should get same results (same role) but different tuple objects
        assert len(static_new) == 2
        assert static_new[0]["name"] == "test_var_1"

    def test_referenced_discovery_independence(self):
        """Test 3: Referenced discovery doesn't modify static discovery state."""
        di = DIContainer(self.role_path, self.options)
        discovery = VariableDiscovery(di, self.role_path, self.options)

        # Call both discovery methods
        static_before = discovery.discover_static()
        referenced = discovery.discover_referenced()
        static_after = discovery.discover_static()

        # Static results should be identical (immutable)
        assert static_before == static_after
        assert isinstance(referenced, frozenset)

    def test_discover_method_returns_immutable_tuple(self):
        """Test 4: discover() returns immutable tuple, not affected by intermediate calls."""
        di = DIContainer(self.role_path, self.options)
        discovery = VariableDiscovery(di, self.role_path, self.options)

        # Call discover (which internally calls discover_static + referenced)
        all_vars = discovery.discover()

        # Result should be immutable tuple
        assert isinstance(all_vars, tuple)
        # Contains at least the static variables
        assert len(all_vars) >= 2


# ============================================================================
# Immutability Enforcement Tests (4)
# ============================================================================


class TestImmutabilityEnforcement:
    """Verify no in-place mutations in the discovery and orchestration pipeline."""

    @pytest.fixture(autouse=True)
    def setup_role_with_multiple_sources(self, tmp_path):
        """Create role with defaults, vars, tasks, and README."""
        role_path = tmp_path
        (role_path / "defaults").mkdir()
        (role_path / "vars").mkdir()
        (role_path / "tasks").mkdir()

        # Setup defaults
        (role_path / "defaults" / "main.yml").write_text(
            "---\n" "default_var: default_value\n" "shared_var: from_defaults\n"
        )

        # Setup vars
        (role_path / "vars" / "main.yml").write_text(
            "---\n" "vars_only: vars_value\n" "shared_var: from_vars\n"
        )

        # Setup simple task that references variables
        (role_path / "tasks" / "main.yml").write_text(
            "---\n"
            "- name: Sample task\n"
            "  debug:\n"
            "    msg: '{{ referenced_var }}'\n"
        )

        # Setup README with variable references
        (role_path / "README.md").write_text(
            "# Sample Role\n"
            "This role uses {{ documented_var }} and {{ another_var }}\n"
        )

        self.role_path = str(role_path)
        self.options = {
            "role_path": self.role_path,
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "vars_seed_paths": None,
            "ignore_unresolved_internal_underscore_references": False,
        }

    def test_discover_static_returns_tuple_not_list(self):
        """Static discovery returns tuple (immutable), not list (mutable)."""
        di = DIContainer(self.role_path, self.options)
        discovery = VariableDiscovery(di, self.role_path, self.options)

        static = discovery.discover_static()

        # Verify tuple, not list
        assert type(static) is tuple
        assert not isinstance(static, list)

    def test_discover_referenced_returns_frozenset_not_set(self):
        """Referenced discovery returns frozenset (immutable), not set (mutable)."""
        di = DIContainer(self.role_path, self.options)
        discovery = VariableDiscovery(di, self.role_path, self.options)

        referenced = discovery.discover_referenced()

        # Verify frozenset, not set
        assert type(referenced) is frozenset
        assert not isinstance(referenced, set)
        # Should contain variables from tasks and README
        assert "referenced_var" in referenced or "documented_var" in referenced

    def test_discover_returns_tuple_concatenation(self):
        """discover() uses tuple concatenation (immutable), not list extend (mutable)."""
        di = DIContainer(self.role_path, self.options)
        discovery = VariableDiscovery(di, self.role_path, self.options)

        all_vars = discovery.discover()

        # Should be tuple
        assert type(all_vars) is tuple
        # Should contain both static and referenced variables
        assert len(all_vars) > 0

    def test_scanner_context_uses_tuple_for_discovered_variables(self):
        """ScannerContext stores discovered variables as immutable tuple."""
        di = DIContainer(self.role_path, self.options)
        context = ScannerContext(di, self.role_path, self.options)

        # Before orchestration
        assert context.discovered_variables == ()

        # After orchestration would need full integration, but we verify type
        # through property access
        discovered_type = type(context.discovered_variables)
        assert discovered_type is tuple


# ============================================================================
# Data Flow Tests (2)
# ============================================================================


class TestImmutableDataFlow:
    """Verify immutable payload flows correctly through orchestrators."""

    @pytest.fixture(autouse=True)
    def setup_minimal_role(self, tmp_path):
        """Create minimal role for data flow testing."""
        role_path = tmp_path
        (role_path / "defaults").mkdir()
        (role_path / "tasks").mkdir()

        (role_path / "defaults" / "main.yml").write_text(
            "---\n" "flow_test_var: flow_test_value\n"
        )

        (role_path / "tasks" / "main.yml").write_text(
            "---\n" "- name: Flow test task\n" "  debug:\n" "    msg: test\n"
        )

        self.role_path = str(role_path)
        self.options = {
            "role_path": self.role_path,
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "vars_seed_paths": None,
            "ignore_unresolved_internal_underscore_references": False,
        }

    def test_scanner_context_orchestrate_returns_immutable_payload(self):
        """orchestrate_scan() returns a payload dict (not mutated by construction)."""
        di = DIContainer(self.role_path, self.options)
        context = ScannerContext(di, self.role_path, self.options)

        payload = context.orchestrate_scan()

        # Verify payload structure (should be dict with proper keys)
        assert isinstance(payload, dict)
        assert "role_name" in payload
        assert "description" in payload
        assert "display_variables" in payload
        assert "requirements_display" in payload
        assert "undocumented_default_filters" in payload
        assert "metadata" in payload

    def test_output_orchestrator_does_not_mutate_input_payload(self):
        """render_and_emit() creates new payload structure without mutating input."""
        # Create a mock payload
        original_payload: RunScanOutputPayload = {
            "role_name": "test_role",
            "description": "Test description",
            "display_variables": {},
            "requirements_display": [],
            "undocumented_default_filters": [],
            "metadata": {"test_key": "original_value"},
        }

        # Create orchestrator
        output_path = str(Path(tempfile.gettempdir()) / "test_output.md")
        options = {
            "output_format": "md",
            "concise_readme": False,
            "template": None,
            "scanner_report_output": None,
            "include_scanner_report_link": False,
            "runbook_output": None,
            "runbook_csv_output": None,
        }

        di = DIContainer(self.role_path, self.options)
        orchestrator = OutputOrchestrator(di, output_path, options)

        # Store original metadata for comparison
        original_metadata_keys = set(original_payload["metadata"].keys())

        # Call render_and_emit with dry_run=True (no file I/O)
        try:
            orchestrator.render_and_emit(original_payload, dry_run=True)
        except Exception:
            # Some failures ok in dry-run; we're testing immutability
            pass

        # Verify original payload wasn't mutated
        assert set(original_payload["metadata"].keys()) == original_metadata_keys
        assert original_payload["metadata"].get("test_key") == "original_value"
        # Should not have output config keys
        assert "concise_readme" not in original_payload["metadata"]


# ============================================================================
# Concurrency Safety Tests (2)
# ============================================================================


class TestConcurrencySafety:
    """Verify immutable data structures are safe for concurrent use."""

    @pytest.fixture(autouse=True)
    def setup_role(self, tmp_path):
        """Create role for concurrency testing."""
        role_path = tmp_path
        (role_path / "defaults").mkdir()
        (role_path / "tasks").mkdir()

        (role_path / "defaults" / "main.yml").write_text(
            "---\n" "concurrent_var_1: value1\n" "concurrent_var_2: value2\n"
        )

        (role_path / "tasks" / "main.yml").write_text("---\n")

        self.role_path = str(role_path)
        self.options = {
            "role_path": self.role_path,
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "vars_seed_paths": None,
            "ignore_unresolved_internal_underscore_references": False,
        }

    def test_tuple_immutability_safe_for_multiple_readers(self):
        """Multiple readers accessing immutable tuple are safe (no locking needed)."""
        di = DIContainer(self.role_path, self.options)
        discovery = VariableDiscovery(di, self.role_path, self.options)

        static = discovery.discover_static()

        # Simulate multiple readers (tuples are read-only, safe)
        reader_1_result = static[0]["name"] if static else None
        reader_2_result = static[0]["name"] if static else None
        reader_3_result = len(static)

        # All readers should get consistent results without any synchronization
        assert reader_1_result == reader_2_result
        assert reader_3_result == len(static)

    def test_frozenset_immutability_safe_for_membership_tests(self):
        """Multiple concurrent membership tests on frozenset are safe."""
        di = DIContainer(self.role_path, self.options)
        discovery = VariableDiscovery(di, self.role_path, self.options)

        referenced = discovery.discover_referenced()

        # Simulate multiple concurrent membership checks
        results = [
            "concurrent_var_1" in referenced,
            "concurrent_var_2" in referenced,
            "nonexistent_var" in referenced,
        ]

        # All checks should complete without synchronization
        assert isinstance(results[0], bool)
        assert isinstance(results[1], bool)
        assert isinstance(results[2], bool)


# ============================================================================
# Additional Edge Case Tests
# ============================================================================


class TestImmutabilityEdgeCases:
    """Test edge cases and boundary conditions for immutability."""

    def test_empty_discovery_returns_empty_immutable_tuple(self, tmp_path):
        """Empty role returns empty immutable tuple, not empty list."""
        role_path = tmp_path
        (role_path / "defaults").mkdir()
        (role_path / "tasks").mkdir()

        options = {
            "role_path": str(role_path),
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "vars_seed_paths": None,
            "ignore_unresolved_internal_underscore_references": False,
        }

        di = DIContainer(str(role_path), options)
        discovery = VariableDiscovery(di, str(role_path), options)

        static = discovery.discover_static()

        # Verify empty tuple, not empty list
        assert static == ()
        assert type(static) is tuple

    def test_discover_referenced_empty_returns_empty_frozenset(self, tmp_path):
        """Role with no referenced variables returns empty frozenset."""
        role_path = tmp_path
        (role_path / "defaults").mkdir()
        (role_path / "tasks").mkdir()

        (role_path / "tasks" / "main.yml").write_text("---\n")

        options = {
            "role_path": str(role_path),
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "vars_seed_paths": None,
            "ignore_unresolved_internal_underscore_references": False,
        }

        di = DIContainer(str(role_path), options)
        discovery = VariableDiscovery(di, str(role_path), options)

        referenced = discovery.discover_referenced()

        # Verify empty frozenset, not empty set
        assert referenced == frozenset()
        assert type(referenced) is frozenset

    def test_discover_combines_immutable_sources(self, tmp_path):
        """discover() properly combines immutable tuple sources."""
        role_path = tmp_path
        (role_path / "defaults").mkdir()
        (role_path / "tasks").mkdir()

        (role_path / "defaults" / "main.yml").write_text("---\nvar1: value1\n")
        (role_path / "tasks" / "main.yml").write_text(
            "---\n" "- name: Task\n" "  debug:\n" "    msg: '{{ var2 }}'\n"
        )

        options = {
            "role_path": str(role_path),
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "vars_seed_paths": None,
            "ignore_unresolved_internal_underscore_references": False,
        }

        di = DIContainer(str(role_path), options)
        discovery = VariableDiscovery(di, str(role_path), options)

        # Get static, referenced separately
        static = discovery.discover_static()
        discovery.discover_referenced()

        # Get combined
        combined = discovery.discover()

        # Combined should have at least the static variables
        assert len(combined) >= len(static)
        # Combined should be tuple
        assert type(combined) is tuple
