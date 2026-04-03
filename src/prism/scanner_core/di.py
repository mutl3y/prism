"""Hand-crafted Dependency Injection container for scanner orchestrators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .feature_detector import FeatureDetector
    from .output_orchestrator import OutputOrchestrator
    from .scanner_context import ScannerContext
    from .variable_discovery import VariableDiscovery
    from ..scanner_data.builders import VariableRowBuilder


class DIContainer:
    """Lightweight DI container for scanner orchestrators."""

    def __init__(
        self,
        role_path: str,
        scan_options: dict[str, Any],
        *,
        scanner_context_wiring: dict[str, Any] | None = None,
        factory_overrides: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        """Initialize container with role path and scan options."""
        if not role_path:
            raise ValueError("role_path must not be empty")
        if scan_options is None:
            raise ValueError("scan_options must not be None")

        self._role_path = role_path
        self._scan_options = scan_options
        self._cache: dict[str, Any] = {}
        self._mocks: dict[str, Any] = {}
        self._scanner_context_wiring = scanner_context_wiring or {}
        self._factory_overrides = factory_overrides or {}

    def factory_scanner_context(self) -> ScannerContext:
        """Create ScannerContext only when runtime seam wiring is provided."""
        scanner_context_cls = self._scanner_context_wiring.get("scanner_context_cls")
        prepare_scan_context_fn = self._scanner_context_wiring.get(
            "prepare_scan_context_fn"
        )
        if scanner_context_cls is None or prepare_scan_context_fn is None:
            raise RuntimeError(
                "factory_scanner_context is disabled: scanner_context_wiring is "
                "not configured. ScannerContext requires prepare_scan_context_fn "
                "runtime seam injection."
            )

        return scanner_context_cls(
            di=self,
            role_path=self._role_path,
            scan_options=self._scan_options,
            prepare_scan_context_fn=prepare_scan_context_fn,
        )

    def factory_variable_discovery(self) -> VariableDiscovery:
        """Create or return cached VariableDiscovery."""
        if "variable_discovery" in self._mocks:
            return self._mocks["variable_discovery"]

        override = self._factory_overrides.get("variable_discovery_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)

        key = "variable_discovery"
        if key not in self._cache:
            from .variable_discovery import VariableDiscovery

            self._cache[key] = VariableDiscovery(
                self, self._role_path, self._scan_options
            )

        return self._cache[key]

    def factory_output_orchestrator(self, output_path: str) -> OutputOrchestrator:
        """Create OutputOrchestrator for a specific output path."""
        cache_key = f"output_orchestrator:{output_path}"
        if cache_key not in self._cache:
            from .output_orchestrator import OutputOrchestrator

            self._cache[cache_key] = OutputOrchestrator(
                di=self,
                output_path=output_path,
                options=self._scan_options,
            )

        return self._cache[cache_key]

    def factory_feature_detector(self) -> FeatureDetector:
        """Create or return cached FeatureDetector."""
        key = "feature_detector"
        if "feature_detector" in self._mocks:
            return self._mocks["feature_detector"]

        override = self._factory_overrides.get("feature_detector_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)

        if key not in self._cache:
            from .feature_detector import FeatureDetector

            self._cache[key] = FeatureDetector(
                self, self._role_path, self._scan_options
            )

        return self._cache[key]

    def factory_variable_row_builder(self) -> VariableRowBuilder:
        """Create cached VariableRowBuilder for row construction helpers."""
        key = "variable_row_builder"
        if key not in self._cache:
            from ..scanner_data.builders import VariableRowBuilder

            self._cache[key] = VariableRowBuilder()
        return self._cache[key]

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
