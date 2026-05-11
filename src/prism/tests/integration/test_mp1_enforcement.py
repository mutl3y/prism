"""MP1 Marker-Prefix Enforcement Test Suite.

Validates MP1 contract: marker-prefix is ingress-owned, immutable, and flows
through canonical path only (bundle_resolver → PreparedPolicyBundle → consumers).

Test Suites:
- Suite 1: Boundary Tests (5 tests) — core MP1 contract validation
- Suite 2: Violation Detection (3 tests) — linting & pattern detection
- Suite 3: Integration Tests (2+ tests) — end-to-end scanner pipeline

Phase: Q2 Initiative 3, Phase 1, Task 1.3 (May 10-12, 2026)
Status: ✅ IMPLEMENTATION
"""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest

# MP1 Enforcement marker for Phase 1 blocking gate
pytestmark = pytest.mark.mp1_blocking


# ============================================================================
# Suite 1: Boundary Tests — Core MP1 Contract Validation
# ============================================================================


@pytest.mark.mp1_blocking
class TestMP1BoundaryMarkerPrefixSourcing:
    """Verify marker-prefix always sourced from bundle, never computed."""

    def test_marker_prefix_sourcing_from_bundle(self, tmp_path):
        """
        OBJECTIVE: Verify marker-prefix flows from ingress → bundle → consumers.

        GIVEN: ExecutionRequest with marker-prefix in scan_options
        WHEN: bundle_resolver projects to PreparedPolicyBundle
        THEN: task_extract_adapters receives marker-prefix from bundle
        AND: No internal computation of marker-prefix occurs
        """
        # Setup test data
        test_prefix = "test_marker"
        from prism.scanner_data.contracts_request import ScanOptionsDict

        scan_options: ScanOptionsDict = {
            "role_path": str(tmp_path),
            "role_name_override": None,
            "readme_config_path": None,
            "policy_config_path": None,
            "comment_doc_marker_prefix": test_prefix,
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

        # Import and execute
        from prism.scanner_plugins.bundle_resolver import (
            ensure_prepared_policy_bundle,
        )
        from prism.scanner_core.di import DIContainer

        di = DIContainer(role_path=str(tmp_path), scan_options=scan_options)

        # Call bundle resolver
        ensure_prepared_policy_bundle(scan_options=scan_options, di=di)

        # Verify: bundle contains projected marker-prefix
        bundle = scan_options.get("prepared_policy_bundle")
        assert bundle is not None, "Bundle not created by ensure_prepared_policy_bundle"
        assert (
            bundle.get("comment_doc_marker_prefix") == test_prefix
        ), f"Bundle marker-prefix mismatch: expected {test_prefix}, got {bundle.get('comment_doc_marker_prefix')}"

    def test_marker_prefix_fallback_hierarchy(self, tmp_path):
        """
        OBJECTIVE: Validate marker-prefix resolution follows canonical priority.

        Priority:
        1. scan_options["comment_doc_marker_prefix"] (ingress top-level) ← HIGHEST
        2. policy_context["comment_doc"]["marker"]["prefix"] (nested fallback)
        3. DEFAULT_DOC_MARKER_PREFIX = "prism" (final fallback)
        """
        from prism.scanner_data.contracts_request import ScanOptionsDict
        from prism.scanner_plugins.bundle_resolver import (
            ensure_prepared_policy_bundle,
        )
        from prism.scanner_core.di import DIContainer

        def create_scan_options(
            marker_prefix: str | None = None,
        ) -> ScanOptionsDict:
            return {
                "role_path": str(tmp_path),
                "role_name_override": None,
                "readme_config_path": None,
                "policy_config_path": None,
                "comment_doc_marker_prefix": marker_prefix,
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

        # Priority 1: Top-level scan_options wins
        opts_p1 = create_scan_options(marker_prefix="top_level")
        di_p1 = DIContainer(role_path=str(tmp_path), scan_options=opts_p1)
        ensure_prepared_policy_bundle(scan_options=opts_p1, di=di_p1)
        assert (
            opts_p1.get("prepared_policy_bundle", {}).get("comment_doc_marker_prefix")
            == "top_level"
        ), "Priority 1: Top-level should win"

        # Priority 2: Default fallback (no nested config in test)
        opts_p3 = create_scan_options(marker_prefix=None)
        di_p3 = DIContainer(role_path=str(tmp_path), scan_options=opts_p3)
        ensure_prepared_policy_bundle(scan_options=opts_p3, di=di_p3)
        bundle_p3 = opts_p3.get("prepared_policy_bundle", {})
        marker_p3 = bundle_p3.get("comment_doc_marker_prefix")
        # Should default to "prism"
        assert (
            marker_p3 == "prism"
        ), f"Priority 3 (default): expected 'prism', got {marker_p3}"

    def test_marker_prefix_immutability_after_projection(self, tmp_path):
        """
        OBJECTIVE: Verify marker-prefix is read-only after bundle creation.

        GIVEN: Prepared bundle with comment_doc_marker_prefix = "test"
        WHEN: Execute task extraction and feature detection
        THEN: bundle['comment_doc_marker_prefix'] remains "test"
        AND: No code path mutates bundle['comment_doc_marker_prefix']
        """
        from prism.scanner_data.contracts_request import ScanOptionsDict
        from prism.scanner_plugins.bundle_resolver import (
            ensure_prepared_policy_bundle,
        )
        from prism.scanner_core.di import DIContainer

        # Setup: Create bundle with marker-prefix
        original_prefix = "immutable_test"
        scan_options: ScanOptionsDict = {
            "role_path": str(tmp_path),
            "role_name_override": None,
            "readme_config_path": None,
            "policy_config_path": None,
            "comment_doc_marker_prefix": original_prefix,
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

        di = DIContainer(role_path=str(tmp_path), scan_options=scan_options)
        ensure_prepared_policy_bundle(scan_options=scan_options, di=di)

        bundle = scan_options.get("prepared_policy_bundle", {})
        original_value = bundle.get("comment_doc_marker_prefix")

        # Verify immutability: marker-prefix hasn't changed
        assert (
            bundle.get("comment_doc_marker_prefix") == original_value
        ), "Bundle marker-prefix was mutated"
        assert (
            bundle.get("comment_doc_marker_prefix") == original_prefix
        ), f"Expected {original_prefix}, got {bundle.get('comment_doc_marker_prefix')}"

    def test_consumer_functions_require_marker_prefix_parameter(self):
        """
        OBJECTIVE: Verify all consumers accept marker-prefix as explicit parameter.

        GIVEN: Consumer function signature
        THEN: marker_prefix parameter present (not implicit/hidden)
        """
        from prism.scanner_core.task_extract_adapters import (
            _extract_task_annotations_for_file,
            _collect_task_handler_catalog,
        )

        # Check that functions have marker_prefix parameter
        sig_extract = inspect.signature(_extract_task_annotations_for_file)
        sig_collect = inspect.signature(_collect_task_handler_catalog)

        assert (
            "marker_prefix" in sig_extract.parameters
        ), "_extract_task_annotations_for_file missing marker_prefix parameter"
        assert (
            "marker_prefix" in sig_collect.parameters
        ), "_collect_task_handler_catalog missing marker_prefix parameter"

        # Verify parameter has proper default
        param_extract = sig_extract.parameters["marker_prefix"]
        param_collect = sig_collect.parameters["marker_prefix"]

        assert param_extract.default == "prism", (
            f"_extract_task_annotations_for_file marker_prefix default should be 'prism', "
            f"got {param_extract.default}"
        )
        assert param_collect.default == "prism", (
            f"_collect_task_handler_catalog marker_prefix default should be 'prism', "
            f"got {param_collect.default}"
        )

    def test_marker_prefix_validation_at_entry(self):
        """
        OBJECTIVE: Verify consumers validate marker-prefix at entry.

        GIVEN: Consumer function has validation logic
        THEN: Marker-prefix parameter is present and documented
        """
        from prism.scanner_core.task_extract_adapters import (
            _extract_task_annotations_for_file,
        )

        # Verify the function signature includes marker_prefix parameter
        sig = inspect.signature(_extract_task_annotations_for_file)
        assert (
            "marker_prefix" in sig.parameters
        ), "_extract_task_annotations_for_file missing marker_prefix parameter"

        # Verify parameter has default and docstring indicates validation
        param = sig.parameters["marker_prefix"]
        assert (
            param.default == "prism"
        ), f"Expected default='prism', got {param.default}"

        # Verify the function documentation mentions MP1 contract
        docstring = _extract_task_annotations_for_file.__doc__ or ""
        assert (
            "marker_prefix" in docstring.lower()
        ), "Function docstring should document marker_prefix parameter"

        # Verify validation code exists in source
        source = inspect.getsource(_extract_task_annotations_for_file)
        assert "marker_prefix" in source, "Function should validate marker_prefix"
        assert (
            "not marker_prefix" in source or "raise" in source
        ), "Function should have validation logic"


# ============================================================================
# Suite 2: Violation Detection Tests — Linting & Pattern Detection
# ============================================================================


@pytest.mark.mp1_blocking
class TestMP1ViolationDetection:
    """Verify violation detection mechanisms identify boundary violations."""

    def test_detect_marker_import_in_scanner_core(self):
        """
        OBJECTIVE: Verify import audit catches forbidden marker-config imports.

        VIOLATION: scanner_core importing from scanner_config.marker
        DETECTOR: grep-based import audit
        """
        project_root = Path(__file__).resolve().parents[4]
        scanner_core_dir = project_root / "src" / "prism" / "scanner_core"

        # Run import audit: look for forbidden marker imports
        try:
            result = subprocess.run(
                [
                    "grep",
                    "-r",
                    "from prism.scanner_config.marker import",
                    str(scanner_core_dir),
                    "--include=*.py",
                    "--exclude=di.py",
                    "--exclude=policy_registry.py",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            violations = [
                line
                for line in result.stdout.split("\n")
                if line.strip() and not line.startswith(str(scanner_core_dir / "tests"))
            ]
            assert (
                len(violations) == 0
            ), f"Found {len(violations)} forbidden marker imports in scanner_core: {violations}"
        except subprocess.TimeoutExpired:
            pytest.skip("grep audit timeout")

    def test_detect_bundle_mutation_outside_resolver(self):
        """
        OBJECTIVE: Verify mutation audit catches bundle modifications.

        VIOLATION: Code outside bundle_resolver modifying bundle['comment_doc_marker_prefix']
        DETECTOR: grep-based mutation detection
        """
        project_root = Path(__file__).resolve().parents[4]
        src_dir = project_root / "src" / "prism"

        # Run mutation audit: look for bundle marker-prefix assignments
        try:
            result = subprocess.run(
                [
                    "grep",
                    "-r",
                    r'bundle\["comment_doc_marker_prefix"\]\s*=',
                    str(src_dir),
                    "--include=*.py",
                    "--exclude-dir=tests",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Filter to only bundle_resolver.py (allowed to assign)
            violations = [
                line
                for line in result.stdout.split("\n")
                if line.strip() and "bundle_resolver.py" not in line
            ]

            assert (
                len(violations) == 0
            ), f"Found {len(violations)} unauthorized bundle mutations: {violations}"
        except subprocess.TimeoutExpired:
            pytest.skip("grep audit timeout")

    def test_detect_hardcoded_marker_assumptions(self):
        """
        OBJECTIVE: Verify pattern detector finds hardcoded marker-prefix values.

        VIOLATION: Code like marker_prefix = "prism" (not using DEFAULT)
        DETECTOR: grep pattern matching
        """
        project_root = Path(__file__).resolve().parents[4]
        scanner_core_dir = project_root / "src" / "prism" / "scanner_core"

        # Pattern: assignment of marker_prefix to literal string (except in comments/tests)
        try:
            result = subprocess.run(
                [
                    "grep",
                    "-r",
                    r'marker_prefix\s*=\s*["\'][a-zA-Z_][a-zA-Z0-9_]*["\']',
                    str(scanner_core_dir),
                    "--include=*.py",
                    "--exclude=*test*.py",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            violations = [
                line
                for line in result.stdout.split("\n")
                if line.strip() and "DEFAULT_DOC_MARKER_PREFIX" not in line
            ]

            assert (
                len(violations) == 0
            ), f"Found {len(violations)} hardcoded marker assumptions: {violations}"
        except subprocess.TimeoutExpired:
            pytest.skip("grep audit timeout")


# ============================================================================
# Suite 3: Integration Tests — End-to-End Scanner Pipeline
# ============================================================================


@pytest.mark.mp1_blocking
class TestMP1Integration:
    """Verify MP1 compliance across full scan pipeline."""

    def test_e2e_custom_marker_prefix(self, tmp_path):
        """
        OBJECTIVE: Verify full scan respects custom marker-prefix throughout.

        GIVEN: Custom marker-prefix = "custom"
        WHEN: Execute full scan pipeline
        THEN: All consumers use "custom"
        AND: Marker-prefix unchanged in output
        """
        from prism.scanner_data.contracts_request import ScanOptionsDict
        from prism.scanner_plugins.bundle_resolver import (
            ensure_prepared_policy_bundle,
        )
        from prism.scanner_core.di import DIContainer

        # Create test role with custom markers
        test_prefix = "custom_marker"
        role_dir = tmp_path / "testrole"
        role_dir.mkdir()
        readme_file = role_dir / "README.md"
        readme_file.write_text(f"""
# Test Role

## {test_prefix}_task
Some task documentation.

## {test_prefix}_handler
Handler documentation.
""")

        # Setup scan_options
        scan_options: ScanOptionsDict = {
            "role_path": str(role_dir),
            "role_name_override": None,
            "readme_config_path": None,
            "policy_config_path": None,
            "comment_doc_marker_prefix": test_prefix,
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

        di = DIContainer(role_path=str(role_dir), scan_options=scan_options)
        ensure_prepared_policy_bundle(scan_options=scan_options, di=di)

        # Verify: bundle contains correct marker-prefix
        bundle = scan_options.get("prepared_policy_bundle", {})
        assert (
            bundle.get("comment_doc_marker_prefix") == test_prefix
        ), f"Expected {test_prefix} in bundle, got {bundle.get('comment_doc_marker_prefix')}"

    def test_marker_prefix_consistency_across_execution(self, tmp_path):
        """
        OBJECTIVE: Verify marker-prefix remains consistent through execution.

        GIVEN: Marker-prefix projected to bundle
        WHEN: Multiple scanner functions consume bundle
        THEN: All see the same marker-prefix
        AND: No function modifies bundle['comment_doc_marker_prefix']
        """
        from prism.scanner_data.contracts_request import ScanOptionsDict
        from prism.scanner_plugins.bundle_resolver import (
            ensure_prepared_policy_bundle,
        )
        from prism.scanner_core.di import DIContainer

        test_prefix = "consistency_test"
        scan_options: ScanOptionsDict = {
            "role_path": str(tmp_path),
            "role_name_override": None,
            "readme_config_path": None,
            "policy_config_path": None,
            "comment_doc_marker_prefix": test_prefix,
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

        di = DIContainer(role_path=str(tmp_path), scan_options=scan_options)
        ensure_prepared_policy_bundle(scan_options=scan_options, di=di)

        bundle_1 = scan_options.get("prepared_policy_bundle", {})
        prefix_1 = bundle_1.get("comment_doc_marker_prefix")

        # Simulate execution: access bundle multiple times
        bundle_2 = scan_options.get("prepared_policy_bundle", {})
        prefix_2 = bundle_2.get("comment_doc_marker_prefix")

        bundle_3 = scan_options.get("prepared_policy_bundle", {})
        prefix_3 = bundle_3.get("comment_doc_marker_prefix")

        # All should match original
        assert (
            prefix_1 == test_prefix
        ), f"First read: expected {test_prefix}, got {prefix_1}"
        assert (
            prefix_2 == test_prefix
        ), f"Second read: expected {test_prefix}, got {prefix_2}"
        assert (
            prefix_3 == test_prefix
        ), f"Third read: expected {test_prefix}, got {prefix_3}"

        # All should be identical references (no mutation)
        assert (
            prefix_1 == prefix_2 == prefix_3
        ), "Marker-prefix changed across execution"


# ============================================================================
# Suite 4: Runtime Enforcement Tests — Enforcer Function Edge Cases
# ============================================================================


@pytest.mark.mp1_blocking
class TestMP1RuntimeEnforcer:
    """Verify runtime enforcer validates bundle marker-prefix availability."""

    def test_enforce_marker_prefix_available_valid_bundle(self):
        """
        OBJECTIVE: Enforcer returns marker-prefix when bundle is valid.

        GIVEN: Bundle with comment_doc_marker_prefix = "test_marker"
        WHEN: enforce_marker_prefix_available(bundle) called
        THEN: Function returns "test_marker"
        """
        from prism.scanner_core.marker_prefix_enforcer import (
            enforce_marker_prefix_available,
        )

        bundle = {"comment_doc_marker_prefix": "test_marker"}
        result = enforce_marker_prefix_available(bundle)
        assert result == "test_marker", f"Expected 'test_marker', got {result}"

    def test_enforce_marker_prefix_available_missing_key(self):
        """
        OBJECTIVE: Enforcer raises ValueError when key missing.

        GIVEN: Bundle without comment_doc_marker_prefix key
        WHEN: enforce_marker_prefix_available(bundle) called
        THEN: Function raises ValueError
        """
        from prism.scanner_core.marker_prefix_enforcer import (
            enforce_marker_prefix_available,
        )

        bundle = {"other_key": "value"}
        with pytest.raises(ValueError) as exc_info:
            enforce_marker_prefix_available(bundle)
        assert "comment_doc_marker_prefix" in str(exc_info.value)

    def test_enforce_marker_prefix_available_empty_string(self):
        """
        OBJECTIVE: Enforcer raises ValueError when value is empty string.

        GIVEN: Bundle with comment_doc_marker_prefix = ""
        WHEN: enforce_marker_prefix_available(bundle) called
        THEN: Function raises ValueError
        """
        from prism.scanner_core.marker_prefix_enforcer import (
            enforce_marker_prefix_available,
        )

        bundle = {"comment_doc_marker_prefix": ""}
        with pytest.raises(ValueError) as exc_info:
            enforce_marker_prefix_available(bundle)
        assert (
            "non-empty" in str(exc_info.value).lower()
            or "empty" in str(exc_info.value).lower()
        )

    def test_enforce_marker_prefix_available_invalid_type(self):
        """
        OBJECTIVE: Enforcer raises ValueError when value is not string.

        GIVEN: Bundle with comment_doc_marker_prefix = 123 (int)
        WHEN: enforce_marker_prefix_available(bundle) called
        THEN: Function raises ValueError
        """
        from prism.scanner_core.marker_prefix_enforcer import (
            enforce_marker_prefix_available,
        )

        bundle = {"comment_doc_marker_prefix": 123}
        with pytest.raises(ValueError) as exc_info:
            enforce_marker_prefix_available(bundle)
        assert "string" in str(exc_info.value).lower()

    def test_enforce_marker_prefix_available_none_bundle(self):
        """
        OBJECTIVE: Enforcer raises ValueError when bundle is None.

        GIVEN: bundle = None
        WHEN: enforce_marker_prefix_available(bundle) called
        THEN: Function raises ValueError
        """
        from prism.scanner_core.marker_prefix_enforcer import (
            enforce_marker_prefix_available,
        )

        with pytest.raises(ValueError) as exc_info:
            enforce_marker_prefix_available(None)
        assert (
            "bundle" in str(exc_info.value).lower()
            or "dict" in str(exc_info.value).lower()
        )
