"""Hand-crafted Dependency Injection container for scanner orchestrators.

Bootstrap Order & Circular Import Prevention
--------------------------------------------
This module uses deferred imports in factory methods to break circular dependencies:
- TYPE_CHECKING imports provide type hints without runtime loading
- Factory methods import concrete classes only when first invoked
- This pattern allows FeatureDetector/VariableDiscovery to import from scanner_extract
  without creating import-time circular dependencies

DI Access Contract
------------------
Code accessing DIContainer attributes should use scanner_core.di_helpers.DIProtocol
for explicit type checking instead of hasattr/getattr duck typing.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, Mapping

from prism.scanner_core.events import EventBus, EventListener, get_default_listeners
from prism.scanner_data.builders import VariableRowBuilder
from prism.errors import PrismRuntimeError

if TYPE_CHECKING:
    from prism.scanner_core.feature_detector import FeatureDetector
    from prism.scanner_core.scan_cache import ScanCacheBackend
    from prism.scanner_core.scanner_context import ScannerContext
    from prism.scanner_core.variable_discovery import VariableDiscovery
    from prism.scanner_core.protocols_runtime import (
        BlockerFactBuilder,
        DIFactoryOverride,
    )
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
    from prism.scanner_plugins.registry import PluginRegistry


def _create_variable_discovery(
    di: DIContainer,
    role_path: str,
    scan_options: dict[str, Any],
) -> VariableDiscovery:
    """Import VariableDiscovery only at the DI composition seam."""
    from prism.scanner_core.variable_discovery import VariableDiscovery

    return VariableDiscovery(di, role_path, scan_options)


def _create_feature_detector(
    di: DIContainer,
    role_path: str,
    scan_options: dict[str, Any],
) -> FeatureDetector:
    """Import FeatureDetector only at the DI composition seam."""
    from prism.scanner_core.feature_detector import FeatureDetector

    return FeatureDetector(di, role_path, scan_options)


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


def _construct_runtime_plugin(
    plugin_class: type[Any],
    *,
    plugin_kind: str,
    platform_key: str,
    di: "DIContainer",
) -> Any:
    """Construct a registry-returned runtime plugin through the DI seam.

    Registry validation should reject classes that do not accept ``di=...``, but
    DI still fails closed here so custom registries or manual test doubles cannot
    reopen the constructor-shape bypass with a raw ``TypeError``.
    """
    try:
        return plugin_class(di=di)
    except TypeError as exc:
        raise PrismRuntimeError(
            code="malformed_plugin_shape",
            category="runtime",
            message=f"Failed to construct {plugin_kind} plugin.",
            detail={
                "plugin_kind": plugin_kind,
                "platform_key": platform_key,
                "plugin_class": getattr(plugin_class, "__name__", "unknown"),
                "error": str(exc),
            },
        ) from exc


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
        factory_overrides: dict[str, "DIFactoryOverride"] | None = None,
        event_listeners: list[EventListener] | None = None,
        cache_backend: ScanCacheBackend | None = None,
        blocker_fact_builder_fn: "BlockerFactBuilder | None" = None,
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
        self._cache_lock = threading.Lock()
        self._mocks: dict[str, Any] = {}
        self._scanner_context_wiring = scanner_context_wiring or {}
        self._factory_overrides = factory_overrides or {}
        self.cache_backend: ScanCacheBackend | None = cache_backend
        self._blocker_fact_builder_fn = blocker_fact_builder_fn
        effective_listeners = (
            list(event_listeners)
            if event_listeners is not None
            else list(get_default_listeners())
        )
        self._event_bus = EventBus(listeners=effective_listeners)

    @property
    def scan_options(self) -> dict[str, Any]:
        return self._scan_options

    @property
    def plugin_registry(self) -> PluginRegistry | None:
        return self._registry

    def factory_event_bus(self) -> EventBus:
        """Return the per-container :class:`EventBus`."""
        return self._event_bus

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

        scanner_context_kwargs: dict[str, Any] = {
            "di": self,
            "role_path": self._role_path,
            "scan_options": self._scan_options,
            "prepare_scan_context_fn": prepare_scan_context_fn,
        }

        return scanner_context_cls(**scanner_context_kwargs)

    def factory_variable_discovery(self) -> VariableDiscovery:
        """Create or return cached VariableDiscovery.

        Note: Import is deferred to break circular dependency.
        VariableDiscovery may import from scanner_extract which imports di_helpers.
        """
        if "variable_discovery" in self._mocks:
            return self._mocks["variable_discovery"]

        override = self._factory_overrides.get("variable_discovery_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)

        key = "variable_discovery"
        with self._cache_lock:
            if key not in self._cache:
                self._cache[key] = _create_variable_discovery(
                    self,
                    self._role_path,
                    self._scan_options,
                )

        return self._cache[key]

    def factory_feature_detector(self) -> FeatureDetector:
        """Create or return cached FeatureDetector.

        Note: Import is deferred to break circular dependency.
        FeatureDetector imports collect_task_handler_catalog from scanner_extract.
        """
        key = "feature_detector"
        if "feature_detector" in self._mocks:
            return self._mocks["feature_detector"]

        override = self._factory_overrides.get("feature_detector_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)

        with self._cache_lock:
            if key not in self._cache:
                self._cache[key] = _create_feature_detector(
                    self,
                    self._role_path,
                    self._scan_options,
                )

        return self._cache[key]

    def factory_variable_row_builder(self) -> VariableRowBuilder:
        """Create cached VariableRowBuilder for row construction helpers."""
        key = "variable_row_builder"
        with self._cache_lock:
            if key not in self._cache:
                self._cache[key] = VariableRowBuilder()
        return self._cache[key]

    def factory_blocker_fact_builder(self) -> "BlockerFactBuilder":
        """Return the blocker-fact builder callable (plugin-layer owned)."""
        key = "blocker_fact_builder"
        with self._cache_lock:
            if key not in self._cache:
                if self._blocker_fact_builder_fn is not None:
                    fn = self._blocker_fact_builder_fn
                else:
                    from prism.scanner_plugins.defaults import (
                        resolve_blocker_fact_builder,
                    )

                    fn = resolve_blocker_fact_builder()
                self._cache[key] = fn
        return self._cache[key]

    def _get_registry(self) -> "PluginRegistry":
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
        return _construct_runtime_plugin(
            plugin_cls,
            plugin_kind="variable_discovery",
            platform_key=platform_key,
            di=self,
        )

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
        return _construct_runtime_plugin(
            plugin_cls,
            plugin_kind="feature_detection",
            platform_key=platform_key,
            di=self,
        )

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

    def factory_audit_plugin(self) -> Any | None:
        """Return the injected audit plugin, or None if audit is not configured (opt-in)."""
        if "audit_plugin" in self._mocks:
            return self._mocks["audit_plugin"]

        override = self._factory_overrides.get("audit_plugin_factory")
        if override is not None:
            return override(self, self._role_path, self._scan_options)
        return None

    def clear_mocks(self) -> None:
        """Clear all injected mocks."""
        self._mocks.clear()

    def clear_cache(self) -> None:
        """Clear cached instances."""
        self._cache.clear()
