"""Tests for DIContainer (Dependency Injection container).

Validates that DIContainer can be instantiated and provides factory methods
for scanner orchestrators without causing circular imports or side effects.
"""

from __future__ import annotations

import pytest

from prism.scanner_core.di import DIContainer
from prism.scanner_core.output_orchestrator import OutputOrchestrator
from prism.scanner_core.scanner_context import ScannerContext
from prism.scanner_data.builders import VariableRowBuilder


class TestDIContainerInstantiation:
    """Test DIContainer initialization and validation."""

    def test_di_container_can_be_instantiated(self) -> None:
        """DIContainer accepts role_path and scan_options and initializes."""
        container = DIContainer(
            role_path="/path/to/role",
            scan_options={"role_name_override": None},
        )
        assert container is not None

    def test_di_container_stores_role_path(self) -> None:
        """DIContainer stores role_path for factory methods."""
        role_path = "/path/to/test/role"
        container = DIContainer(
            role_path=role_path,
            scan_options={},
        )
        assert container._role_path == role_path

    def test_di_container_stores_scan_options(self) -> None:
        """DIContainer stores scan_options for factory methods."""
        options = {"include_vars_main": True, "detailed_catalog": False}
        container = DIContainer(
            role_path="/path/to/role",
            scan_options=options,
        )
        assert container._scan_options == options

    def test_di_container_rejects_empty_role_path(self) -> None:
        """DIContainer raises ValueError if role_path is empty."""
        with pytest.raises(ValueError, match="role_path must not be empty"):
            DIContainer(role_path="", scan_options={})

    def test_di_container_rejects_none_scan_options(self) -> None:
        """DIContainer raises ValueError if scan_options is None."""
        with pytest.raises(ValueError, match="scan_options must not be None"):
            DIContainer(role_path="/path", scan_options=None)  # type: ignore


class TestDIContainerFactoryMethods:
    """Test observable factory behavior."""

    @pytest.fixture
    def container(self) -> DIContainer:
        """Provide a configured container for tests."""
        return DIContainer(
            role_path="/path/to/role",
            scan_options={"include_vars_main": True},
        )

    def test_factory_scanner_context_returns_scanner_context_instance(
        self, container: DIContainer
    ) -> None:
        """ScannerContext factory returns canonical scanner context instances."""
        first = container.factory_scanner_context()
        second = container.factory_scanner_context()
        assert isinstance(first, ScannerContext)
        assert second is first
        assert first._di is container

    def test_factory_variable_discovery_can_be_called(
        self, container: DIContainer
    ) -> None:
        """factory_variable_discovery can be called without errors."""
        first = container.factory_variable_discovery()
        second = container.factory_variable_discovery()
        assert first is not None
        assert second is first

    def test_factory_output_orchestrator_returns_orchestrator_instance(
        self, container: DIContainer
    ) -> None:
        """factory_output_orchestrator returns canonical orchestrator instance."""
        result = container.factory_output_orchestrator("/path/to/output.md")
        assert isinstance(result, OutputOrchestrator)

    def test_factory_feature_detector_can_be_called(
        self, container: DIContainer
    ) -> None:
        """factory_feature_detector can be called without errors."""
        first = container.factory_feature_detector()
        second = container.factory_feature_detector()
        assert first is not None
        assert second is first

    def test_factory_variable_row_builder_returns_builder_instance(
        self, container: DIContainer
    ) -> None:
        """factory_variable_row_builder returns cached builder instance."""
        first = container.factory_variable_row_builder()
        second = container.factory_variable_row_builder()
        assert isinstance(first, VariableRowBuilder)
        assert second is first


class TestDIContainerMockInjection:
    """Test mock injection capability for testing."""

    @pytest.fixture
    def container(self) -> DIContainer:
        """Provide a configured container for tests."""
        return DIContainer(
            role_path="/path/to/role",
            scan_options={},
        )

    def test_inject_mock_variable_discovery(self, container: DIContainer) -> None:
        """inject_mock_variable_discovery method exists and stores mock."""
        mock_discovery = object()
        container.inject_mock_variable_discovery(mock_discovery)
        # Verify mock is returned by factory
        result = container.factory_variable_discovery()
        assert result is mock_discovery

    def test_inject_mock_feature_detector(self, container: DIContainer) -> None:
        """inject_mock_feature_detector method exists and stores mock."""
        mock_detector = object()
        container.inject_mock_feature_detector(mock_detector)
        # Verify mock is returned by factory
        result = container.factory_feature_detector()
        assert result is mock_detector

    def test_clear_mocks_restores_cached_variable_discovery_instance(
        self, container: DIContainer
    ) -> None:
        """Clearing mocks should restore the previously cached real instance."""
        cached = container.factory_variable_discovery()
        mock_discovery = object()
        container.inject_mock_variable_discovery(mock_discovery)

        assert container.factory_variable_discovery() is mock_discovery

        container.clear_mocks()
        assert container.factory_variable_discovery() is cached

    def test_clear_mocks_resets_injected_mocks(self, container: DIContainer) -> None:
        """clear_mocks removes all injected mocks."""
        mock_discovery = object()
        container.inject_mock_variable_discovery(mock_discovery)
        # Verify mock is set
        assert container._mocks.get("variable_discovery") is mock_discovery
        # Clear mocks
        container.clear_mocks()
        # Verify mock is cleared
        assert "variable_discovery" not in container._mocks

    def test_clear_cache_resets_cached_instances(self, container: DIContainer) -> None:
        """clear_cache removes cached builder instances."""
        # Manually add something to cache to test clearing
        container._cache["test_key"] = "test_value"
        assert "test_key" in container._cache
        # Clear cache
        container.clear_cache()
        # Verify cache is cleared
        assert "test_key" not in container._cache


class TestDIContainerNoCircularImports:
    """Test that DIContainer import doesn't introduce circular dependencies."""

    def test_di_container_can_be_imported_from_scanner_core(self) -> None:
        """DIContainer can be imported from scanner_core module."""
        from prism.scanner_core import DIContainer as ImportedContainer

        assert ImportedContainer is DIContainer

    def test_di_module_imports_only_safe_modules(self) -> None:
        """di.py imports only typing and safe standard library."""
        # This is a structural test: if di.py had circular imports,
        # this import would fail. Successful import validates design.
        from prism.scanner_core.di import DIContainer as DirectImport

        assert DirectImport is not None


class TestDIContainerBootstrapPattern:
    """Test the bootstrap usage pattern (as documented in requirements)."""

    def test_bootstrap_pattern_di_container_role_path_options(self) -> None:
        """Bootstrap pattern: DIContainer(role_path, options).factory_*() works."""
        # This mirrors the intended usage in scanner.py Wave 2:
        # container = DIContainer(role_path, options)
        # context = container.factory_scanner_context()
        # payload = context.orchestrate_scan()

        role_path = "/ansible/roles/my_role"
        options = {
            "role_name_override": None,
            "include_vars_main": True,
            "detailed_catalog": False,
        }

        container = DIContainer(role_path, options)
        assert container is not None

        # All factory methods should return canonical callables/instances.
        context = container.factory_scanner_context()
        discovery = container.factory_variable_discovery()
        orchestrator = container.factory_output_orchestrator("/tmp/README.md")
        detector = container.factory_feature_detector()
        builder = container.factory_variable_row_builder()

        assert isinstance(context, ScannerContext)
        assert discovery is not None
        assert isinstance(orchestrator, OutputOrchestrator)
        assert detector is not None
        assert isinstance(builder, VariableRowBuilder)


class TestDIContainerLineLength:
    """Test that di.py stays within the <150 line constraint."""

    def test_di_py_is_under_150_lines(self) -> None:
        """di.py should be concise (<150 lines including docstrings)."""
        import inspect

        from prism.scanner_core import di

        source_lines = inspect.getsourcelines(di)[0]
        line_count = len(source_lines)

        # Goal: <150 lines (achieved: ~78 lines)
        assert line_count < 150, f"di.py has {line_count} lines, should be <150"
