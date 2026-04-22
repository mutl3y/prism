"""Hand-crafted Dependency Injection container for scanner orchestrators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Mapping

from prism.scanner_data.builders import VariableRowBuilder

if TYPE_CHECKING:
    from prism.scanner_core.feature_detector import FeatureDetector
    from prism.scanner_core.scanner_context import ScannerContext
    from prism.scanner_core.variable_discovery import VariableDiscovery
    from prism.scanner_io.output_orchestrator import OutputOrchestrator
    from prism.scanner_plugins.interfaces import (
        CommentDrivenDocumentationPlugin,
        JinjaAnalysisPolicyPlugin,
        VariableDiscoveryPlugin,
        FeatureDetectionPlugin,
        YAMLParsingPolicyPlugin,
    )
    from prism.scanner_data.contracts_request import (
        PreparedTaskAnnotationPolicy,
        PreparedTaskLineParsingPolicy,
        PreparedTaskTraversalPolicy,
        PreparedVariableExtractorPolicy,
    )


def resolve_platform_key(
    scan_options: Mapping[str, Any],
    registry: Any | None = None,
) -> str:
    """Resolve platform key: scan_pipeline_plugin > policy_context > registry default."""
    if isinstance(scan_options, dict):
        explicit = scan_options.get("scan_pipeline_plugin")
        if isinstance(explicit, str) and explicit:
            return explicit
        policy_context = scan_options.get("policy_context")
        if isinstance(policy_context, dict):
            selection = policy_context.get("selection")
            if isinstance(selection, dict):
                plugin_key = selection.get("plugin")
                if isinstance(plugin_key, str) and plugin_key:
                    return plugin_key
    if registry is not None:
        default_key = registry.get_default_platform_key()
        if default_key is not None:
            return default_key
    raise ValueError(
        "No platform key resolvable from scan_options, policy_context, or registry default."
    )


class DIContainer:
    """Lightweight DI container for scanner orchestrators."""

    def __init__(
        self,
        role_path: str,
        scan_options: dict[str, Any],
        *,
        registry: Any | None = None,
        platform_key: str | None = None,
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
        self._registry = registry
        self._platform_key = platform_key
        self._cache: dict[str, Any] = {}
        self._mocks: dict[str, Any] = {}
        self._scanner_context_wiring = scanner_context_wiring or {}
        self._factory_overrides = factory_overrides or {}

    @property
    def scan_options(self) -> dict[str, Any]:
        return self._scan_options

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
            from prism.scanner_core.variable_discovery import VariableDiscovery

            self._cache[key] = VariableDiscovery(
                self, self._role_path, self._scan_options
            )

        return self._cache[key]

    def factory_output_orchestrator(self, output_path: str) -> OutputOrchestrator:
        """Create OutputOrchestrator for a specific output path."""
        cache_key = f"output_orchestrator:{output_path}"
        if cache_key not in self._cache:
            from prism.scanner_io.output_orchestrator import OutputOrchestrator

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
            from prism.scanner_core.feature_detector import FeatureDetector

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

    def factory_blocker_fact_builder(self) -> Callable[..., Any]:
        """Return the blocker-fact builder callable (plugin-layer owned)."""
        key = "blocker_fact_builder"
        if key not in self._cache:
            from prism.scanner_plugins.audit.blocker_fact_evaluator import (
                build_scan_policy_blocker_facts,
            )

            self._cache[key] = build_scan_policy_blocker_facts
        return self._cache[key]

    def _get_registry(self) -> Any:
        """Return the injected plugin registry or raise."""
        if self._registry is None:
            raise ValueError("No plugin registry provided to DIContainer")
        return self._registry

    def _resolve_platform_key(self) -> str:
        """Return pre-resolved platform key or delegate to module-level resolver."""
        if self._platform_key is not None:
            return self._platform_key
        return resolve_platform_key(self._scan_options, self._registry)

    def factory_variable_discovery_plugin(self) -> VariableDiscoveryPlugin:
        """Resolve variable-discovery plugin via registry; fail-closed if unregistered."""
        if "variable_discovery_plugin" in self._mocks:
            return self._mocks["variable_discovery_plugin"]

        override = self._factory_overrides.get("variable_discovery_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)

        platform_key = self._resolve_platform_key()
        registry = self._get_registry()
        plugin_cls = registry.get_variable_discovery_plugin(platform_key)
        if plugin_cls is None:
            raise ValueError(
                f"No variable_discovery plugin registered under '{platform_key}'. "
                "Ensure scanner_plugins bootstrap has run."
            )
        return plugin_cls(di=self)

    def factory_feature_detection_plugin(self) -> FeatureDetectionPlugin:
        """Resolve feature-detection plugin via registry; fail-closed if unregistered."""
        if "feature_detection_plugin" in self._mocks:
            return self._mocks["feature_detection_plugin"]

        override = self._factory_overrides.get("feature_detection_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)

        platform_key = self._resolve_platform_key()
        registry = self._get_registry()
        plugin_cls = registry.get_feature_detection_plugin(platform_key)
        if plugin_cls is None:
            raise ValueError(
                f"No feature_detection plugin registered under '{platform_key}'. "
                "Ensure scanner_plugins bootstrap has run."
            )
        return plugin_cls(di=self)

    def factory_comment_driven_doc_plugin(
        self,
    ) -> CommentDrivenDocumentationPlugin | None:
        """Resolve optional comment-driven documentation plugin from DI wiring."""
        if "comment_driven_doc_plugin" in self._mocks:
            return self._mocks["comment_driven_doc_plugin"]

        override = self._factory_overrides.get("comment_driven_doc_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_task_annotation_policy_plugin(
        self,
    ) -> PreparedTaskAnnotationPolicy | None:
        """Resolve optional task-annotation policy plugin from DI wiring."""
        if "task_annotation_policy_plugin" in self._mocks:
            return self._mocks["task_annotation_policy_plugin"]

        override = self._factory_overrides.get("task_annotation_policy_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_task_line_parsing_policy_plugin(
        self,
    ) -> PreparedTaskLineParsingPolicy | None:
        """Resolve optional task-line parsing policy plugin from DI wiring."""
        if "task_line_parsing_policy_plugin" in self._mocks:
            return self._mocks["task_line_parsing_policy_plugin"]

        override = self._factory_overrides.get(
            "task_line_parsing_policy_plugin_factory"
        )
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_task_traversal_policy_plugin(
        self,
    ) -> PreparedTaskTraversalPolicy | None:
        """Resolve optional task-traversal policy plugin from DI wiring."""
        if "task_traversal_policy_plugin" in self._mocks:
            return self._mocks["task_traversal_policy_plugin"]

        override = self._factory_overrides.get("task_traversal_policy_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_variable_extractor_policy_plugin(
        self,
    ) -> PreparedVariableExtractorPolicy | None:
        """Resolve optional variable-extractor policy plugin from DI wiring."""
        if "variable_extractor_policy_plugin" in self._mocks:
            return self._mocks["variable_extractor_policy_plugin"]

        override = self._factory_overrides.get(
            "variable_extractor_policy_plugin_factory"
        )
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_yaml_parsing_policy_plugin(self) -> YAMLParsingPolicyPlugin | None:
        """Resolve optional YAML parsing policy plugin from DI wiring."""
        if "yaml_parsing_policy_plugin" in self._mocks:
            return self._mocks["yaml_parsing_policy_plugin"]

        override = self._factory_overrides.get("yaml_parsing_policy_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def factory_jinja_analysis_policy_plugin(self) -> JinjaAnalysisPolicyPlugin | None:
        """Resolve optional Jinja analysis policy plugin from DI wiring."""
        if "jinja_analysis_policy_plugin" in self._mocks:
            return self._mocks["jinja_analysis_policy_plugin"]

        override = self._factory_overrides.get("jinja_analysis_policy_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def inject_mock(self, name: str, mock: Any) -> None:
        """Inject a mock for testing. Name must match a factory key."""
        self._mocks[name] = mock

    def inject_mock_variable_discovery(self, mock: Any) -> None:
        self.inject_mock("variable_discovery", mock)

    def inject_mock_feature_detector(self, mock: Any) -> None:
        self.inject_mock("feature_detector", mock)

    def inject_mock_variable_discovery_plugin(self, mock: Any) -> None:
        self.inject_mock("variable_discovery_plugin", mock)

    def inject_mock_feature_detection_plugin(self, mock: Any) -> None:
        self.inject_mock("feature_detection_plugin", mock)

    def inject_mock_comment_driven_doc_plugin(self, mock: Any) -> None:
        self.inject_mock("comment_driven_doc_plugin", mock)

    def inject_mock_task_annotation_policy_plugin(self, mock: Any) -> None:
        self.inject_mock("task_annotation_policy_plugin", mock)

    def inject_mock_task_line_parsing_policy_plugin(self, mock: Any) -> None:
        self.inject_mock("task_line_parsing_policy_plugin", mock)

    def inject_mock_task_traversal_policy_plugin(self, mock: Any) -> None:
        self.inject_mock("task_traversal_policy_plugin", mock)

    def inject_mock_variable_extractor_policy_plugin(self, mock: Any) -> None:
        self.inject_mock("variable_extractor_policy_plugin", mock)

    def inject_mock_yaml_parsing_policy_plugin(self, mock: Any) -> None:
        self.inject_mock("yaml_parsing_policy_plugin", mock)

    def inject_mock_jinja_analysis_policy_plugin(self, mock: Any) -> None:
        self.inject_mock("jinja_analysis_policy_plugin", mock)

    def factory_audit_plugin(self) -> Any | None:
        """Return the injected audit plugin, or None if audit is not configured (opt-in)."""
        if "audit_plugin" in self._mocks:
            return self._mocks["audit_plugin"]

        override = self._factory_overrides.get("audit_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def inject_mock_audit_plugin(self, mock: Any) -> None:
        self.inject_mock("audit_plugin", mock)

    def clear_mocks(self) -> None:
        """Clear all injected mocks."""
        self._mocks.clear()

    def clear_cache(self) -> None:
        """Clear cached instances."""
        self._cache.clear()
