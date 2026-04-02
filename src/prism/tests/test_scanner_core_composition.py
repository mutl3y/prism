"""Tests for scanner_core composition consistency.

Validates that:
1. All scanner_core orchestrators use consistent explicit injection patterns
2. No module constructs orchestrators inline
3. All runtime seams use the same composition style
4. DI wiring is complete and enforced
"""

from __future__ import annotations

import pytest

from prism.scanner_core.di import DIContainer


class TestScannerCoreOrchestratorComposition:
    """Test that all orchestrators use consistent composition via DIContainer."""

    @pytest.fixture
    def di_container(self) -> DIContainer:
        """Provide a configured DI container."""
        return DIContainer(
            role_path="/path/to/role",
            scan_options={"include_vars_main": True},
        )

    def test_variable_discovery_receives_di_container(
        self, di_container: DIContainer
    ) -> None:
        """VariableDiscovery receives DIContainer and stores it."""
        from prism.scanner_core.variable_discovery import VariableDiscovery as VD

        discovery = di_container.factory_variable_discovery()
        assert isinstance(discovery, VD)
        assert hasattr(discovery, "_di")
        assert discovery._di is di_container

    def test_feature_detector_receives_di_container(
        self, di_container: DIContainer
    ) -> None:
        """FeatureDetector receives DIContainer and stores it."""
        from prism.scanner_core.feature_detector import FeatureDetector as FD

        detector = di_container.factory_feature_detector()
        assert isinstance(detector, FD)
        assert hasattr(detector, "_di")
        assert detector._di is di_container

    def test_output_orchestrator_receives_di_container(
        self, di_container: DIContainer
    ) -> None:
        """OutputOrchestrator receives DIContainer and stores it."""
        from prism.scanner_core.output_orchestrator import OutputOrchestrator as OO

        orchestrator = di_container.factory_output_orchestrator("/tmp/output.md")
        assert isinstance(orchestrator, OO)
        assert hasattr(orchestrator, "_di")
        assert orchestrator._di is di_container

    def test_all_orchestrators_receive_same_container(
        self, di_container: DIContainer
    ) -> None:
        """All orchestrators created by same container reference the same container."""
        discovery = di_container.factory_variable_discovery()
        detector = di_container.factory_feature_detector()
        orchestrator = di_container.factory_output_orchestrator("/tmp/output.md")

        # All should have the same DIContainer reference
        assert discovery._di is di_container
        assert detector._di is di_container
        assert orchestrator._di is di_container

    def test_di_container_factory_methods_consistent_return_types(
        self, di_container: DIContainer
    ) -> None:
        """All factory methods return correctly typed instances."""
        from prism.scanner_core.feature_detector import FeatureDetector as FD
        from prism.scanner_core.output_orchestrator import OutputOrchestrator as OO
        from prism.scanner_core.variable_discovery import VariableDiscovery as VD
        from prism.scanner_data.builders import VariableRowBuilder as VRB

        # Get instances via factory methods
        discovery = di_container.factory_variable_discovery()
        detector = di_container.factory_feature_detector()
        orchestrator = di_container.factory_output_orchestrator("/tmp/output.md")
        builder = di_container.factory_variable_row_builder()

        # Verify types
        assert isinstance(discovery, VD)
        assert isinstance(detector, FD)
        assert isinstance(orchestrator, OO)
        assert isinstance(builder, VRB)


class TestCompositionConsistency:
    """Test that comparable runtime seams use comparable composition patterns."""

    def test_scanner_context_composition_requires_explicit_wiring(self) -> None:
        """ScannerContext requires explicit wiring to be created via DI."""
        container = DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )

        # Without wiring, factory should raise explicit error
        with pytest.raises(RuntimeError) as exc_info:
            container.factory_scanner_context()

        error_msg = str(exc_info.value)
        assert "scanner_context_wiring is not configured" in error_msg
        assert "prepare_scan_context_fn" in error_msg

    def test_all_di_factory_methods_follow_consistent_pattern(
        self,
    ) -> None:
        """All DIContainer factory methods follow the same consistency pattern."""
        from prism.scanner_core.feature_detector import FeatureDetector
        from prism.scanner_core.variable_discovery import VariableDiscovery
        from prism.scanner_data.builders import VariableRowBuilder

        container = DIContainer(
            role_path="/path/to/role",
            scan_options={"include_vars_main": True},
        )

        # All factory methods should be callable and return instances
        factory_methods = {
            "factory_variable_discovery": VariableDiscovery,
            "factory_feature_detector": FeatureDetector,
            "factory_variable_row_builder": VariableRowBuilder,
        }

        for method_name, expected_type in factory_methods.items():
            factory_method = getattr(container, method_name)
            result = factory_method()
            assert isinstance(result, expected_type), (
                f"{method_name} should return {expected_type.__name__}, "
                f"got {type(result).__name__}"
            )


class TestCompositionExplicitness:
    """Test that all composition is explicit and goes through configured seams."""

    def test_no_implicit_orchestrator_construction(self) -> None:
        """Orchestrators should only be created via DIContainer factories."""
        container = DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )

        # These should only be accessible via factory methods
        assert not hasattr(container, "_variable_discovery")
        assert not hasattr(container, "_feature_detector")
        assert not hasattr(container, "_output_orchestrators")

        # Creation must go through factory methods
        discovery = container.factory_variable_discovery()
        detector = container.factory_feature_detector()
        orchestrator = container.factory_output_orchestrator("/tmp/README.md")

        assert discovery is not None
        assert detector is not None
        assert orchestrator is not None

    def test_di_injection_is_explicit_not_implicit(self) -> None:
        """DIContainer dependencies are explicitly passed, not implicitly resolved."""
        # Verify that orchestrators require di to be passed explicitly
        container = DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )

        # Getting orchestrators should return instances that reference the container
        discovery = container.factory_variable_discovery()
        assert discovery._di is container

        detector = container.factory_feature_detector()
        assert detector._di is container

        orchestrator = container.factory_output_orchestrator("/tmp/output.md")
        assert orchestrator._di is container

    def test_composition_via_factory_overrides(self) -> None:
        """Factory overrides allow explicit alternative composition."""
        sentinel_discovery = object()
        sentinel_detector = object()

        def fake_discovery_factory(_di, _role_path, _options):
            return sentinel_discovery

        def fake_detector_factory(_di, _role_path, _options):
            return sentinel_detector

        container = DIContainer(
            role_path="/path/to/role",
            scan_options={},
            factory_overrides={
                "variable_discovery_factory": fake_discovery_factory,
                "feature_detector_factory": fake_detector_factory,
            },
        )

        # Verify overrides are used
        assert container.factory_variable_discovery() is sentinel_discovery
        assert container.factory_feature_detector() is sentinel_detector


class TestDICacheConsistency:
    """Test that DI caching is consistent and predictable."""

    def test_orchestrators_are_cached_per_container(self) -> None:
        """Same container returns same orchestrator instance."""
        container = DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )

        # Same container, same instance
        discovery1 = container.factory_variable_discovery()
        discovery2 = container.factory_variable_discovery()
        assert discovery1 is discovery2

        detector1 = container.factory_feature_detector()
        detector2 = container.factory_feature_detector()
        assert detector1 is detector2

    def test_different_containers_create_different_instances(self) -> None:
        """Different containers create different orchestrator instances."""
        container1 = DIContainer(
            role_path="/path/to/role1",
            scan_options={},
        )
        container2 = DIContainer(
            role_path="/path/to/role2",
            scan_options={},
        )

        discovery1 = container1.factory_variable_discovery()
        discovery2 = container2.factory_variable_discovery()
        assert discovery1 is not discovery2

    def test_cache_can_be_cleared(self) -> None:
        """DIContainer.clear_cache() resets cached instances."""
        container = DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )

        discovery1 = container.factory_variable_discovery()
        container.clear_cache()
        discovery2 = container.factory_variable_discovery()

        assert discovery1 is not discovery2


class TestCompositionPatternEnforcement:
    """Test that composition patterns are enforced consistently."""

    def test_orchestrator_initialization_requires_di_parameter(self) -> None:
        """All orchestrators require 'di' parameter in __init__."""
        # Each orchestrator class should require di parameter
        container = DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )

        # Verify that orchestrators store and use the di reference
        discovery = container.factory_variable_discovery()
        assert hasattr(discovery, "_di"), "VariableDiscovery must store di"

        detector = container.factory_feature_detector()
        assert hasattr(detector, "_di"), "FeatureDetector must store di"

        orchestrator = container.factory_output_orchestrator("/tmp/output.md")
        assert hasattr(orchestrator, "_di"), "OutputOrchestrator must store di"

    def test_explicit_wiring_required_for_dependencies(self) -> None:
        """Explicit wiring is required for orchestrators with runtime dependencies."""
        from prism.scanner_core.scanner_context import ScannerContext

        container = DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )

        # ScannerContext requires explicit wiring
        with pytest.raises(RuntimeError):
            container.factory_scanner_context()

        # With wiring, it should work
        def fake_prepare(_options):
            return {
                "rp": "/role",
                "role_name": "test",
                "description": "",
                "requirements_display": [],
                "undocumented_default_filters": [],
                "display_variables": {},
                "metadata": {},
            }

        container_with_wiring = DIContainer(
            role_path="/path/to/role",
            scan_options={"role_path": "/role"},
            scanner_context_wiring={
                "scanner_context_cls": ScannerContext,
                "prepare_scan_context_fn": fake_prepare,
            },
        )

        context = container_with_wiring.factory_scanner_context()
        assert context is not None
        assert isinstance(context, ScannerContext)
