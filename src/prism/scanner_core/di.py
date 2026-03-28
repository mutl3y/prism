"""Hand-crafted Dependency Injection container for scanner orchestrators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .feature_detector import FeatureDetector
    from .output_orchestrator import OutputOrchestrator
    from .scanner_context import ScannerContext
    from .variable_discovery import VariableDiscovery


class DIContainer:
    """Lightweight DI container for scanner orchestrators (no external frameworks).

    Provides lazy instantiation of ScannerContext, VariableDiscovery,
    OutputOrchestrator, FeatureDetector with optional mock injection for testing.
    """

    def __init__(self, role_path: str, scan_options: dict[str, Any]) -> None:
        """Initialize container with role path and scan options.

        Args:
            role_path: Path to Ansible role directory.
            scan_options: Normalized scan configuration dict.

        Raises:
            ValueError: If role_path is empty or scan_options is None.
        """
        if not role_path:
            raise ValueError("role_path must not be empty")
        if scan_options is None:
            raise ValueError("scan_options must not be None")

        self._role_path = role_path
        self._scan_options = scan_options
        self._cache: dict[str, Any] = {}
        self._mocks: dict[str, Any] = {}

    def factory_scanner_context(self) -> ScannerContext | None:
        """Create ScannerContext orchestrator (Wave 2 placeholder)."""
        return None

    def factory_variable_discovery(self) -> VariableDiscovery:
        """Create VariableDiscovery analyzer with caching for reuse.

        Returns cached instance if previously created, or creates new one
        with role_path and scan_options from container initialization.
        Allows mock injection for testing.
        """
        if "variable_discovery" in self._mocks:
            return self._mocks["variable_discovery"]

        key = "variable_discovery"
        if key not in self._cache:
            from .variable_discovery import VariableDiscovery

            self._cache[key] = VariableDiscovery(
                self, self._role_path, self._scan_options
            )

        return self._cache[key]

    def factory_output_orchestrator(
        self, output_path: str
    ) -> OutputOrchestrator | None:
        """Create OutputOrchestrator (Wave 2 placeholder)."""
        _ = output_path
        return None

    def factory_feature_detector(self) -> FeatureDetector:
        """Create FeatureDetector (Wave 2 implementation).

        Returns cached instance if previously created, or creates new one
        with role_path and scan_options from container initialization.
        """
        key = "feature_detector"
        if "feature_detector" in self._mocks:
            return self._mocks["feature_detector"]

        if key not in self._cache:
            from .feature_detector import FeatureDetector

            self._cache[key] = FeatureDetector(
                self, self._role_path, self._scan_options
            )

        return self._cache[key]

    def factory_variable_row_builder(self) -> Any:
        """Create VariableRowBuilder (cached; Wave 2 placeholder)."""
        key = "variable_row_builder"
        if key not in self._cache:
            pass  # self._cache[key] = VariableRowBuilder()
        return self._cache.get(key)

    def inject_mock_variable_discovery(self, mock: Any) -> None:
        """Inject a mock VariableDiscovery for testing."""
        self._mocks["variable_discovery"] = mock

    def inject_mock_feature_detector(self, mock: Any) -> None:
        """Inject a mock FeatureDetector for testing."""
        self._mocks["feature_detector"] = mock

    def clear_mocks(self) -> None:
        """Clear all injected mocks."""
        self._mocks.clear()

    def clear_cache(self) -> None:
        """Clear cached instances."""
        self._cache.clear()
