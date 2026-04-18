"""Hand-crafted Dependency Injection container for scanner orchestrators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

try:
    from prism.scanner_data.builders import VariableRowBuilder
except ModuleNotFoundError:

    class VariableRowBuilder:  # pragma: no cover - fallback for fsrc bootstrap only
        """Minimal fallback builder for fsrc bootstrap wiring."""

        pass


if TYPE_CHECKING:
    from prism.scanner_core.feature_detector import FeatureDetector
    from prism.scanner_core.output_orchestrator import OutputOrchestrator
    from prism.scanner_core.scanner_context import ScannerContext
    from prism.scanner_core.variable_discovery import VariableDiscovery


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
        build_run_scan_options_fn = self._scanner_context_wiring.get(
            "build_run_scan_options_fn"
        )
        if scanner_context_cls is None or prepare_scan_context_fn is None:
            raise RuntimeError(
                "factory_scanner_context is disabled: scanner_context_wiring is "
                "not configured. ScannerContext requires prepare_scan_context_fn "
                "runtime seam injection."
            )

        scanner_context_kwargs: dict[str, Any] = {
            "di": self,
            "role_path": self._role_path,
            "scan_options": self._scan_options,
            "prepare_scan_context_fn": prepare_scan_context_fn,
        }
        if build_run_scan_options_fn is not None:
            scanner_context_kwargs["build_run_scan_options_fn"] = (
                build_run_scan_options_fn
            )

        return scanner_context_cls(**scanner_context_kwargs)

    def factory_variable_discovery(self) -> VariableDiscovery:
        """Create or return cached VariableDiscovery."""
        if "variable_discovery" in self._mocks:
            return self._mocks["variable_discovery"]

        override = self._factory_overrides.get("variable_discovery_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)

        key = "variable_discovery"
        if key not in self._cache:
            try:
                from prism.scanner_core.variable_discovery import VariableDiscovery
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "factory_variable_discovery is unavailable in fsrc lane until "
                    "prism.scanner_core.variable_discovery is ported."
                ) from exc

            self._cache[key] = VariableDiscovery(
                self, self._role_path, self._scan_options
            )

        return self._cache[key]

    def factory_output_orchestrator(self, output_path: str) -> OutputOrchestrator:
        """Create OutputOrchestrator for a specific output path."""
        cache_key = f"output_orchestrator:{output_path}"
        if cache_key not in self._cache:
            try:
                from prism.scanner_core.output_orchestrator import OutputOrchestrator
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "factory_output_orchestrator is unavailable in fsrc lane until "
                    "prism.scanner_core.output_orchestrator is ported."
                ) from exc

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
            try:
                from prism.scanner_core.feature_detector import FeatureDetector
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "factory_feature_detector is unavailable in fsrc lane until "
                    "prism.scanner_core.feature_detector is ported."
                ) from exc

            self._cache[key] = FeatureDetector(
                self, self._role_path, self._scan_options
            )

        return self._cache[key]

    def factory_variable_row_builder(self) -> VariableRowBuilder:
        """Create cached VariableRowBuilder for row construction helpers."""
        key = "variable_row_builder"
        if key not in self._cache:
            self._cache[key] = VariableRowBuilder()
        return self._cache[key]

    def factory_variable_discovery_plugin(self) -> Any | None:
        """Resolve optional variable-discovery plugin from DI wiring."""
        if "variable_discovery_plugin" in self._mocks:
            return self._mocks["variable_discovery_plugin"]

        override = self._factory_overrides.get("variable_discovery_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_feature_detection_plugin(self) -> Any | None:
        """Resolve optional feature-detection plugin from DI wiring."""
        if "feature_detection_plugin" in self._mocks:
            return self._mocks["feature_detection_plugin"]

        override = self._factory_overrides.get("feature_detection_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_comment_driven_doc_plugin(self) -> Any | None:
        """Resolve optional comment-driven documentation plugin from DI wiring."""
        if "comment_driven_doc_plugin" in self._mocks:
            return self._mocks["comment_driven_doc_plugin"]

        override = self._factory_overrides.get("comment_driven_doc_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_task_annotation_policy_plugin(self) -> Any | None:
        """Resolve optional task-annotation policy plugin from DI wiring."""
        if "task_annotation_policy_plugin" in self._mocks:
            return self._mocks["task_annotation_policy_plugin"]

        override = self._factory_overrides.get("task_annotation_policy_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_task_line_parsing_policy_plugin(self) -> Any | None:
        """Resolve optional task-line parsing policy plugin from DI wiring."""
        if "task_line_parsing_policy_plugin" in self._mocks:
            return self._mocks["task_line_parsing_policy_plugin"]

        override = self._factory_overrides.get(
            "task_line_parsing_policy_plugin_factory"
        )
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_task_traversal_policy_plugin(self) -> Any | None:
        """Resolve optional task-traversal policy plugin from DI wiring."""
        if "task_traversal_policy_plugin" in self._mocks:
            return self._mocks["task_traversal_policy_plugin"]

        override = self._factory_overrides.get("task_traversal_policy_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_variable_extractor_policy_plugin(self) -> Any | None:
        """Resolve optional variable-extractor policy plugin from DI wiring."""
        if "variable_extractor_policy_plugin" in self._mocks:
            return self._mocks["variable_extractor_policy_plugin"]

        override = self._factory_overrides.get(
            "variable_extractor_policy_plugin_factory"
        )
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_yaml_parsing_policy_plugin(self) -> Any | None:
        """Resolve optional YAML parsing policy plugin from DI wiring."""
        if "yaml_parsing_policy_plugin" in self._mocks:
            return self._mocks["yaml_parsing_policy_plugin"]

        override = self._factory_overrides.get("yaml_parsing_policy_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_jinja_analysis_policy_plugin(self) -> Any | None:
        """Resolve optional Jinja analysis policy plugin from DI wiring."""
        if "jinja_analysis_policy_plugin" in self._mocks:
            return self._mocks["jinja_analysis_policy_plugin"]

        override = self._factory_overrides.get("jinja_analysis_policy_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def inject_mock_variable_discovery(self, mock: Any) -> None:
        """Inject a mock VariableDiscovery for testing."""
        self._mocks["variable_discovery"] = mock

    def inject_mock_feature_detector(self, mock: Any) -> None:
        """Inject a mock FeatureDetector for testing."""
        self._mocks["feature_detector"] = mock

    def inject_mock_variable_discovery_plugin(self, mock: Any) -> None:
        """Inject a mock variable-discovery plugin for testing."""
        self._mocks["variable_discovery_plugin"] = mock

    def inject_mock_feature_detection_plugin(self, mock: Any) -> None:
        """Inject a mock feature-detection plugin for testing."""
        self._mocks["feature_detection_plugin"] = mock

    def inject_mock_comment_driven_doc_plugin(self, mock: Any) -> None:
        """Inject a mock comment-driven documentation plugin for testing."""
        self._mocks["comment_driven_doc_plugin"] = mock

    def inject_mock_task_annotation_policy_plugin(self, mock: Any) -> None:
        """Inject a mock task-annotation policy plugin for testing."""
        self._mocks["task_annotation_policy_plugin"] = mock

    def inject_mock_task_line_parsing_policy_plugin(self, mock: Any) -> None:
        """Inject a mock task-line parsing policy plugin for testing."""
        self._mocks["task_line_parsing_policy_plugin"] = mock

    def inject_mock_task_traversal_policy_plugin(self, mock: Any) -> None:
        """Inject a mock task-traversal policy plugin for testing."""
        self._mocks["task_traversal_policy_plugin"] = mock

    def inject_mock_variable_extractor_policy_plugin(self, mock: Any) -> None:
        """Inject a mock variable-extractor policy plugin for testing."""
        self._mocks["variable_extractor_policy_plugin"] = mock

    def inject_mock_yaml_parsing_policy_plugin(self, mock: Any) -> None:
        """Inject a mock YAML parsing policy plugin for testing."""
        self._mocks["yaml_parsing_policy_plugin"] = mock

    def inject_mock_jinja_analysis_policy_plugin(self, mock: Any) -> None:
        """Inject a mock Jinja analysis policy plugin for testing."""
        self._mocks["jinja_analysis_policy_plugin"] = mock

    def clear_mocks(self) -> None:
        """Clear all injected mocks."""
        self._mocks.clear()

    def clear_cache(self) -> None:
        """Clear cached instances."""
        self._cache.clear()
