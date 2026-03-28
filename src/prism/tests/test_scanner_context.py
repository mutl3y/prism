"""Tests for ScannerContext (main scan orchestrator).

Validates that ScannerContext orchestrates scan phases, maintains immutable
state contracts, and integrates properly with DIContainer and existing
scanner.py infrastructure.
"""

from __future__ import annotations

import pytest

from prism.scanner_core import DIContainer, ScannerContext


class TestScannerContextInstantiation:
    """Test ScannerContext initialization and validation."""

    def test_scanner_context_can_be_instantiated(self) -> None:
        """ScannerContext accepts di, role_path, and scan_options."""
        di = DIContainer(role_path="/path/to/role", scan_options={})
        context = ScannerContext(
            di=di,
            role_path="/path/to/role",
            scan_options={"role_name_override": None},
        )
        assert context is not None

    def test_scanner_context_stores_role_path(self) -> None:
        """ScannerContext stores role_path for orchestration."""
        di = DIContainer(role_path="/path/to/role", scan_options={})
        role_path = "/path/to/test/role"
        context = ScannerContext(
            di=di,
            role_path=role_path,
            scan_options={},
        )
        assert context._role_path == role_path

    def test_scanner_context_stores_scan_options(self) -> None:
        """ScannerContext stores scan_options for orchestration."""
        di = DIContainer(role_path="/path", scan_options={})
        options = {"include_vars_main": True, "detailed_catalog": False}
        context = ScannerContext(
            di=di,
            role_path="/path",
            scan_options=options,
        )
        assert context._scan_options == options

    def test_scanner_context_rejects_none_di(self) -> None:
        """ScannerContext raises ValueError if di is None."""
        with pytest.raises(ValueError, match="di .* must not be None"):
            ScannerContext(di=None, role_path="/path", scan_options={})  # type: ignore

    def test_scanner_context_rejects_empty_role_path(self) -> None:
        """ScannerContext raises ValueError if role_path is empty."""
        di = DIContainer(role_path="/path", scan_options={})
        with pytest.raises(ValueError, match="role_path must not be empty"):
            ScannerContext(di=di, role_path="", scan_options={})

    def test_scanner_context_rejects_none_scan_options(self) -> None:
        """ScannerContext raises ValueError if scan_options is None."""
        di = DIContainer(role_path="/path", scan_options={})
        with pytest.raises(ValueError, match="scan_options must not be None"):
            ScannerContext(di=di, role_path="/path", scan_options=None)  # type: ignore


class TestScannerContextOrchestration:
    """Test the main orchestration flow."""

    @pytest.fixture
    def context(self) -> ScannerContext:
        """Provide a configured context for tests."""
        di = DIContainer(
            role_path="/path/to/role",
            scan_options={"include_vars_main": True},
        )
        return ScannerContext(
            di=di,
            role_path="/path/to/role",
            scan_options={"include_vars_main": True, "detailed_catalog": False},
        )

    def test_orchestrate_scan_can_be_called(self, context: ScannerContext) -> None:
        """orchestrate_scan method exists and is callable."""
        assert hasattr(context, "orchestrate_scan")
        assert callable(context.orchestrate_scan)

    def test_orchestrate_scan_returns_dict(self, context: ScannerContext) -> None:
        """orchestrate_scan returns a dict (placeholder payload structure)."""
        result = context.orchestrate_scan()
        assert isinstance(result, dict)

    def test_orchestrate_scan_returns_expected_keys(
        self, context: ScannerContext
    ) -> None:
        """orchestrate_scan returns dict with RunScanOutputPayload keys."""
        result = context.orchestrate_scan()
        expected_keys = {
            "role_name",
            "description",
            "display_variables",
            "requirements_display",
            "undocumented_default_filters",
            "metadata",
        }
        assert set(result.keys()) == expected_keys

    def test_orchestrate_scan_sets_non_empty_role_name_from_role_path(
        self, context: ScannerContext
    ) -> None:
        """orchestrate_scan returns non-empty role_name for normal role paths."""
        result = context.orchestrate_scan()
        assert result["role_name"] == "role"

    def test_orchestrate_scan_prefers_role_name_override(self) -> None:
        """orchestrate_scan uses role_name_override when provided."""
        di = DIContainer(
            role_path="/path/to/role",
            scan_options={"role_name_override": "custom_role"},
        )
        context = ScannerContext(
            di=di,
            role_path="/path/to/role",
            scan_options={"role_name_override": "custom_role"},
        )

        result = context.orchestrate_scan()
        assert result["role_name"] == "custom_role"

    def test_orchestrate_scan_metadata_is_dict(self, context: ScannerContext) -> None:
        """orchestrate_scan payload includes metadata dict."""
        result = context.orchestrate_scan()
        assert "metadata" in result
        assert isinstance(result["metadata"], dict)

    def test_orchestrate_scan_display_variables_is_dict(
        self, context: ScannerContext
    ) -> None:
        """orchestrate_scan payload includes display_variables dict."""
        result = context.orchestrate_scan()
        assert "display_variables" in result
        assert isinstance(result["display_variables"], dict)

    def test_orchestrate_scan_requirements_display_is_list(
        self, context: ScannerContext
    ) -> None:
        """orchestrate_scan payload includes requirements_display list."""
        result = context.orchestrate_scan()
        assert "requirements_display" in result
        assert isinstance(result["requirements_display"], list)

    def test_orchestrate_scan_undocumented_filters_is_list(
        self, context: ScannerContext
    ) -> None:
        """orchestrate_scan payload includes undocumented_default_filters list."""
        result = context.orchestrate_scan()
        assert "undocumented_default_filters" in result
        assert isinstance(result["undocumented_default_filters"], list)


class TestScannerContextStateImmutability:
    """Test that state is managed immutably via properties."""

    @pytest.fixture
    def context(self) -> ScannerContext:
        """Provide a configured context for tests."""
        di = DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )
        return ScannerContext(
            di=di,
            role_path="/path/to/role",
            scan_options={},
        )

    def test_discovered_variables_property_exists(
        self, context: ScannerContext
    ) -> None:
        """discovered_variables property is accessible (immutable tuple)."""
        assert hasattr(context, "discovered_variables")
        result = context.discovered_variables
        assert isinstance(result, tuple)

    def test_discovered_variables_empty_before_orchestration(
        self, context: ScannerContext
    ) -> None:
        """discovered_variables is empty tuple before orchestrate_scan."""
        assert context.discovered_variables == ()

    def test_discovered_variables_after_orchestration(
        self, context: ScannerContext
    ) -> None:
        """discovered_variables updated after orchestrate_scan (immutable tuple)."""
        context.orchestrate_scan()
        # Returns immutable tuple (even if currently empty)
        assert isinstance(context.discovered_variables, tuple)

    def test_detected_features_property_exists(self, context: ScannerContext) -> None:
        """detected_features property is accessible."""
        assert hasattr(context, "detected_features")
        result = context.detected_features
        assert isinstance(result, dict)

    def test_detected_features_empty_before_orchestration(
        self, context: ScannerContext
    ) -> None:
        """detected_features is empty dict before orchestrate_scan."""
        assert context.detected_features == {}

    def test_detected_features_after_orchestration(
        self, context: ScannerContext
    ) -> None:
        """detected_features updated after orchestrate_scan (currently empty)."""
        context.orchestrate_scan()
        # Currently returns empty dict (placeholder until task_2_4)
        assert isinstance(context.detected_features, dict)

    def test_scan_metadata_property_exists(self, context: ScannerContext) -> None:
        """scan_metadata property is accessible."""
        assert hasattr(context, "scan_metadata")
        result = context.scan_metadata
        assert isinstance(result, dict)

    def test_scan_metadata_accessible_after_orchestration(
        self, context: ScannerContext
    ) -> None:
        """scan_metadata accessible after orchestrate_scan."""
        context.orchestrate_scan()
        metadata = context.scan_metadata
        assert isinstance(metadata, dict)

    def test_properties_return_same_reference(self, context: ScannerContext) -> None:
        """Properties return references to internal state (immutable from caller)."""
        context.orchestrate_scan()
        metadata1 = context.scan_metadata
        metadata2 = context.scan_metadata
        # Same reference expected (immutable view of internal state)
        assert metadata1 is metadata2


class TestScannerContextPhaseCoordination:
    """Test coordination between discovery, detection, and output phases."""

    @pytest.fixture
    def context(self) -> ScannerContext:
        """Provide a configured context for tests."""
        di = DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )
        return ScannerContext(
            di=di,
            role_path="/path/to/role",
            scan_options={"include_vars_main": True},
        )

    def test_orchestrate_scan_runs_all_phases(self, context: ScannerContext) -> None:
        """orchestrate_scan executes all three phases without error."""
        # Should not raise exception
        result = context.orchestrate_scan()
        assert result is not None

    def test_discovered_variables_populated_after_phase_1(
        self, context: ScannerContext
    ) -> None:
        """discovered_variables available after orchestration (phase 1, immutable tuple)."""
        context.orchestrate_scan()
        discovered = context.discovered_variables
        # Immutable tuple (even if currently empty)
        assert isinstance(discovered, tuple)

    def test_detected_features_populated_after_phase_2(
        self, context: ScannerContext
    ) -> None:
        """detected_features available after orchestration (phase 2)."""
        context.orchestrate_scan()
        detected = context.detected_features
        # Currently empty (placeholder), but accessible
        assert isinstance(detected, dict)

    def test_metadata_available_from_output_payload(
        self, context: ScannerContext
    ) -> None:
        """Metadata returned in orchestrate_scan payload (phase 3)."""
        payload = context.orchestrate_scan()
        assert "metadata" in payload
        assert isinstance(payload["metadata"], dict)


class TestScannerContextDataFlow:
    """Test immutable data flow through orchestration."""

    @pytest.fixture
    def context(self) -> ScannerContext:
        """Provide a configured context for tests."""
        di = DIContainer(
            role_path="/path/to/role",
            scan_options={"include_vars_main": True, "detailed_catalog": False},
        )
        return ScannerContext(
            di=di,
            role_path="/path/to/role",
            scan_options={"include_vars_main": True, "detailed_catalog": False},
        )

    def test_payload_structure_matches_contract(self, context: ScannerContext) -> None:
        """Returned payload adheres to RunScanOutputPayload contract."""
        payload = context.orchestrate_scan()

        # Check each field type
        assert isinstance(payload["role_name"], str)
        assert isinstance(payload["description"], str)
        assert isinstance(payload["display_variables"], dict)
        assert isinstance(payload["requirements_display"], list)
        assert isinstance(payload["undocumented_default_filters"], list)
        assert isinstance(payload["metadata"], dict)

    def test_payload_is_complete(self, context: ScannerContext) -> None:
        """Payload contains no None fields (all fields initialized)."""
        payload = context.orchestrate_scan()
        for key, value in payload.items():
            assert value is not None, f"Field {key} should not be None"

    def test_state_immutability_after_multiple_phases(
        self, context: ScannerContext
    ) -> None:
        """State remains consistent across multiple phase calls."""
        context.orchestrate_scan()
        discovered1 = context.discovered_variables
        detected1 = context.detected_features

        # State should not change on re-access
        discovered2 = context.discovered_variables
        detected2 = context.detected_features

        assert discovered1 == discovered2
        assert detected1 == detected2


class TestScannerContextIntegration:
    """Integration tests with DIContainer and scanner infrastructure."""

    def test_scanner_context_works_with_mock_di(self) -> None:
        """ScannerContext integrates cleanly with DIContainer."""
        di = DIContainer(
            role_path="/path/to/role",
            scan_options={"include_vars_main": True},
        )
        context = ScannerContext(
            di=di,
            role_path="/path/to/role",
            scan_options={"include_vars_main": True},
        )
        assert context._di is di

    def test_scanner_context_preserves_di_configuration(self) -> None:
        """ScannerContext does not modify DIContainer."""
        scan_options = {"include_vars_main": True, "detailed_catalog": False}
        di = DIContainer(
            role_path="/path/to/role",
            scan_options=scan_options,
        )
        ScannerContext(
            di=di,
            role_path="/path/to/role",
            scan_options=scan_options,
        )
        # DI container state should be unchanged
        assert di._scan_options == scan_options

    def test_scanner_context_can_orchestrate_minimal_role(self) -> None:
        """ScannerContext orchestration completes without errors on minimal config."""
        di = DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )
        context = ScannerContext(
            di=di,
            role_path="/path/to/role",
            scan_options={},
        )
        # Should complete without exception
        payload = context.orchestrate_scan()
        assert payload is not None
        assert "role_name" in payload
