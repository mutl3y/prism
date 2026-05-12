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
from inspect import Parameter, signature
from typing import TYPE_CHECKING, Any, Callable, Mapping, Protocol, cast

from prism.scanner_core.events import EventBus, EventListener, get_default_listeners
from prism.scanner_core.di_helpers import factory_override_key
from prism.scanner_data.contracts_request import ScanOptionsDict
from prism.scanner_data.builders import VariableRowBuilder
from prism.errors import PrismRuntimeError
from prism.scanner_core.plugin_resolver import PluginResolver
from prism.scanner_core.service_locator import ServiceLocator

if TYPE_CHECKING:
    from prism.scanner_core.feature_detector import FeatureDetector
    from prism.scanner_core.scan_cache import ScanCacheBackend
    from prism.scanner_core.scanner_context import ScannerContext
    from prism.scanner_core.variable_discovery import VariableDiscovery
    from prism.scanner_core.policy_manager import PolicyManager
    from prism.scanner_core.policy_registry import FallbackPolicyRegistry
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


class _PlatformKeyRegistry(Protocol):
    """Minimal registry surface required for platform-key resolution."""

    def get_default_platform_key(self) -> str | None: ...


def _clone_container_structure(value: object) -> object:
    """Clone container nodes while preserving opaque object identity."""
    if isinstance(value, dict):
        return {key: _clone_container_structure(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_container_structure(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_clone_container_structure(item) for item in value)
    if isinstance(value, set):
        return {_clone_container_structure(item) for item in value}
    if isinstance(value, frozenset):
        return frozenset(_clone_container_structure(item) for item in value)
    return value


def clone_scan_options(scan_options: Mapping[str, object]) -> ScanOptionsDict:
    """Return a container-only snapshot of scan options for runtime consumers.

    Constructs ScanOptionsDict explicitly instead of using blind cast() to preserve
    TypedDict semantics and enable runtime validation.
    """
    result: ScanOptionsDict = {}  # type: ignore[typeddict-item]
    for key, value in scan_options.items():
        result[key] = _clone_container_structure(value)  # type: ignore[literal-required]
    return result


def _snapshot_request_scan_options(
    scan_options: Mapping[str, object],
) -> ScanOptionsDict:
    """Snapshot request scan options without rewriting caller-provided values."""
    return clone_scan_options(scan_options)


_SCAN_OPTION_DEPENDENT_CACHE_KEYS = frozenset(
    {
        "feature_detector",
        "variable_discovery",
    }
)


def _create_variable_discovery(
    di: DIContainer,
    role_path: str,
    scan_options: ScanOptionsDict,
) -> VariableDiscovery:
    """Import VariableDiscovery only at the DI composition seam."""
    from prism.scanner_core.variable_discovery import VariableDiscovery

    return VariableDiscovery(di, role_path, scan_options)


def _create_feature_detector(
    di: DIContainer,
    role_path: str,
    scan_options: ScanOptionsDict,
) -> FeatureDetector:
    """Import FeatureDetector only at the DI composition seam."""
    from prism.scanner_core.feature_detector import FeatureDetector

    return FeatureDetector(di, role_path, scan_options)


def resolve_platform_key(
    scan_options: ScanOptionsDict,
    registry: _PlatformKeyRegistry | None = None,
) -> str:
    """Resolve platform key: scan_pipeline_plugin > policy_context > platform > registry default."""
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
        platform = scan_options.get("platform")
        if isinstance(platform, str) and platform:
            return platform
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
    constructor_signature = signature(plugin_class)
    accepts_di = any(
        parameter.kind is Parameter.VAR_KEYWORD or name == "di"
        for name, parameter in constructor_signature.parameters.items()
    )
    if not accepts_di:
        raise PrismRuntimeError(
            code="malformed_plugin_shape",
            category="runtime",
            message=f"Malformed {plugin_kind} plugin shape detected.",
            detail={
                "plugin_kind": plugin_kind,
                "platform_key": platform_key,
                "plugin_class": getattr(plugin_class, "__name__", "unknown"),
                "missing_callables": [],
                "missing_attributes": ["di"],
            },
        )
    try:
        return plugin_class(di=di)
    except PrismRuntimeError:
        raise
    except TypeError as exc:
        raise PrismRuntimeError(
            code="malformed_plugin_shape",
            category="runtime",
            message=f"Malformed {plugin_kind} plugin shape detected.",
            detail={
                "plugin_kind": plugin_kind,
                "platform_key": platform_key,
                "plugin_class": getattr(plugin_class, "__name__", "unknown"),
                "error": str(exc),
                "failure_type": type(exc).__name__,
            },
        ) from exc


class DIContainer:
    """Lightweight DI container for scanner orchestrators."""

    def __init__(
        self,
        role_path: str,
        scan_options: ScanOptionsDict,
        *,
        registry: PluginRegistry | None = None,
        platform_key: str | None = None,
        scanner_context_wiring: dict[str, object] | None = None,
        factory_overrides: dict[str, "DIFactoryOverride"] | None = None,
        event_listeners: list[EventListener] | None = None,
        inherit_default_event_listeners: bool = False,
        cache_backend: ScanCacheBackend | None = None,
        blocker_fact_builder_fn: "BlockerFactBuilder | None" = None,
    ) -> None:
        """Initialize container with role path and scan options."""
        if not role_path:
            raise ValueError("role_path must not be empty")
        if scan_options is None:
            raise ValueError("scan_options must not be None")

        self._role_path = role_path
        self._scan_options = _snapshot_request_scan_options(scan_options)
        self._registry: PluginRegistry | None = registry
        self._platform_key = platform_key
        self._cache: dict[str, Any] = {}
        self._cache_lock = threading.RLock()
        self._mocks: dict[str, Any] = {}
        self._scanner_context_wiring = scanner_context_wiring or {}
        self._factory_overrides = factory_overrides or {}
        self._inherit_default_event_listeners = inherit_default_event_listeners
        self.cache_backend: ScanCacheBackend | None = cache_backend
        self._blocker_fact_builder_fn = blocker_fact_builder_fn
        ambient_default_listeners = (
            list(get_default_listeners()) if inherit_default_event_listeners else []
        )
        effective_listeners = (
            list(event_listeners)
            if event_listeners is not None
            # Capture the current ambient snapshot once so later registrations do
            # not mutate this container's per-instance event bus.
            else ambient_default_listeners
        )
        self._event_bus = EventBus(listeners=effective_listeners)

        self._plugin_resolver = PluginResolver(self)
        self._service_locator = ServiceLocator(self)

        # Pre-populate event bus cache so ServiceLocator returns the same instance
        self._cache["event_bus"] = self._event_bus

    @property
    def scan_options(self) -> ScanOptionsDict:
        return self._snapshot_scan_options()

    def replace_scan_options(self, new_scan_options: ScanOptionsDict) -> None:
        """Replace scan_options and invalidate dependent caches.

        Args:
            new_scan_options: New scan options to replace the current ones.
        """
        with self._cache_lock:
            self._scan_options = _snapshot_request_scan_options(new_scan_options)
            self._invalidate_scan_option_dependent_cache_locked()
        self._service_locator.replace_scan_options()

    def _snapshot_scan_options(self) -> ScanOptionsDict:
        with self._cache_lock:
            snapshot = clone_scan_options(self._scan_options)
            # Preserve historical behavior: DI-owned role_path overrides only
            # when callers provided role_path in scan_options.
            if "role_path" in snapshot:
                snapshot["role_path"] = self._role_path
            return snapshot

    def _invalidate_scan_option_dependent_cache_locked(self) -> None:
        for key in _SCAN_OPTION_DEPENDENT_CACHE_KEYS:
            self._cache.pop(key, None)

    @property
    def plugin_registry(self) -> PluginRegistry | None:
        return self._registry

    @property
    def scanner_context_wiring(self) -> dict[str, object]:
        return self._scanner_context_wiring

    @property
    def factory_overrides(self) -> dict[str, "DIFactoryOverride"]:
        return self._factory_overrides

    @property
    def platform_key(self) -> str | None:
        return self._platform_key

    @property
    def inherit_default_event_listeners(self) -> bool:
        return self._inherit_default_event_listeners

    def _call_factory_override(self, name: str) -> object | None:
        override = self._factory_overrides.get(name)
        if override is None:
            return None
        try:
            result = override(self, self._role_path, self._snapshot_scan_options())
            return result
        except Exception as exc:
            raise PrismRuntimeError(
                code="di_factory_override_failed",
                category="dependency-injection",
                message=f"Factory override '{name}' raised {type(exc).__name__}",
                detail={
                    "override_name": name,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            ) from exc

    def factory_event_bus(self) -> EventBus:
        """Return the per-container :class:`EventBus`."""
        return self._service_locator.factory_event_bus()

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
            "scan_options": self._snapshot_scan_options(),
            "prepare_scan_context_fn": prepare_scan_context_fn,
        }

        scanner_context_factory = cast(
            "Callable[..., ScannerContext]",
            scanner_context_cls,
        )
        return scanner_context_factory(**scanner_context_kwargs)

    def factory_variable_discovery(self) -> VariableDiscovery:
        """Create or return cached VariableDiscovery.

        Note: Import is deferred to break circular dependency.
        VariableDiscovery may import from scanner_extract which imports di_helpers.
        """
        if "variable_discovery" in self._mocks:
            return self._mocks["variable_discovery"]

        override_result = self._call_factory_override(
            factory_override_key("variable_discovery")
        )
        if override_result is not None:
            return cast("VariableDiscovery", override_result)

        key = "variable_discovery"
        with self._cache_lock:
            if key not in self._cache:
                self._cache[key] = _create_variable_discovery(
                    self,
                    self._role_path,
                    self._snapshot_scan_options(),
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

        override_result = self._call_factory_override(
            factory_override_key("feature_detector")
        )
        if override_result is not None:
            return cast("FeatureDetector", override_result)

        with self._cache_lock:
            if key not in self._cache:
                self._cache[key] = _create_feature_detector(
                    self,
                    self._role_path,
                    self._snapshot_scan_options(),
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

    def factory_variable_discovery_plugin(self) -> "VariableDiscoveryPlugin":
        if "variable_discovery_plugin" in self._mocks:
            return self._mocks["variable_discovery_plugin"]
        override_result = self._call_factory_override(
            factory_override_key("variable_discovery_plugin")
        )
        if override_result is not None:
            return cast("VariableDiscoveryPlugin", override_result)
        return self._plugin_resolver.factory_variable_discovery_plugin()

    def factory_feature_detection_plugin(self) -> "FeatureDetectionPlugin":
        if "feature_detection_plugin" in self._mocks:
            return self._mocks["feature_detection_plugin"]
        override_result = self._call_factory_override(
            factory_override_key("feature_detection_plugin")
        )
        if override_result is not None:
            return cast("FeatureDetectionPlugin", override_result)
        return self._plugin_resolver.factory_feature_detection_plugin()

    def register_platform_plugin_bundle(
        self,
        *,
        platform_key: str,
        support_state: str,
        runtime_aliases: tuple[str, ...] = (),
        default_providers: Mapping[str, Callable[[], Any]] | None = None,
        scan_pipeline_plugin: type[Any] | None = None,
        readme_renderer_plugin: type[Any] | None = None,
        variable_discovery_plugin: type[Any] | None = None,
        variable_discovery_loader: tuple[str, str] | None = None,
        feature_detection_plugin: type[Any] | None = None,
        feature_detection_loader: tuple[str, str] | None = None,
    ) -> None:
        from prism.scanner_plugins.bootstrap import register_platform_plugin_bundle

        register_platform_plugin_bundle(
            self._get_registry(),
            platform_key=platform_key,
            support_state=cast(Any, support_state),
            runtime_aliases=runtime_aliases,
            default_providers=default_providers,
            scan_pipeline_plugin=scan_pipeline_plugin,
            readme_renderer_plugin=readme_renderer_plugin,
            variable_discovery_plugin=variable_discovery_plugin,
            variable_discovery_loader=variable_discovery_loader,
            feature_detection_plugin=feature_detection_plugin,
            feature_detection_loader=feature_detection_loader,
        )

    def factory_comment_driven_doc_plugin(
        self,
    ) -> "CommentDrivenDocumentationPlugin | None":
        if "comment_driven_doc_plugin" in self._mocks:
            return self._mocks["comment_driven_doc_plugin"]
        override_result = self._call_factory_override(
            "comment_driven_doc_plugin_factory"
        )
        if override_result is not None:
            return cast("CommentDrivenDocumentationPlugin | None", override_result)
        return self._plugin_resolver.factory_comment_driven_doc_plugin()

    def factory_task_annotation_policy_plugin(
        self,
    ) -> "PreparedTaskAnnotationPolicy | None":
        if "task_annotation_policy_plugin" in self._mocks:
            return self._mocks["task_annotation_policy_plugin"]
        override_result = self._call_factory_override(
            "task_annotation_policy_plugin_factory"
        )
        if override_result is not None:
            return cast("PreparedTaskAnnotationPolicy | None", override_result)
        return self._plugin_resolver.factory_task_annotation_policy_plugin()

    def factory_task_line_parsing_policy_plugin(
        self,
    ) -> "PreparedTaskLineParsingPolicy | None":
        if "task_line_parsing_policy_plugin" in self._mocks:
            return self._mocks["task_line_parsing_policy_plugin"]
        override_result = self._call_factory_override(
            "task_line_parsing_policy_plugin_factory"
        )
        if override_result is not None:
            return cast("PreparedTaskLineParsingPolicy | None", override_result)
        return self._plugin_resolver.factory_task_line_parsing_policy_plugin()

    def factory_task_traversal_policy_plugin(
        self,
    ) -> "PreparedTaskTraversalPolicy | None":
        if "task_traversal_policy_plugin" in self._mocks:
            return self._mocks["task_traversal_policy_plugin"]
        override_result = self._call_factory_override(
            "task_traversal_policy_plugin_factory"
        )
        if override_result is not None:
            return cast("PreparedTaskTraversalPolicy | None", override_result)
        return self._plugin_resolver.factory_task_traversal_policy_plugin()

    def factory_variable_extractor_policy_plugin(
        self,
    ) -> "PreparedVariableExtractorPolicy | None":
        if "variable_extractor_policy_plugin" in self._mocks:
            return self._mocks["variable_extractor_policy_plugin"]
        override_result = self._call_factory_override(
            "variable_extractor_policy_plugin_factory"
        )
        if override_result is not None:
            return cast("PreparedVariableExtractorPolicy | None", override_result)
        return self._plugin_resolver.factory_variable_extractor_policy_plugin()

    def factory_yaml_parsing_policy_plugin(self) -> "YAMLParsingPolicyPlugin | None":
        if "yaml_parsing_policy_plugin" in self._mocks:
            return self._mocks["yaml_parsing_policy_plugin"]
        override_result = self._call_factory_override(
            "yaml_parsing_policy_plugin_factory"
        )
        if override_result is not None:
            return cast("YAMLParsingPolicyPlugin | None", override_result)
        return self._plugin_resolver.factory_yaml_parsing_policy_plugin()

    def factory_jinja_analysis_policy_plugin(
        self,
    ) -> "JinjaAnalysisPolicyPlugin | None":
        if "jinja_analysis_policy_plugin" in self._mocks:
            return self._mocks["jinja_analysis_policy_plugin"]
        override_result = self._call_factory_override(
            "jinja_analysis_policy_plugin_factory"
        )
        if override_result is not None:
            return cast("JinjaAnalysisPolicyPlugin | None", override_result)
        return self._plugin_resolver.factory_jinja_analysis_policy_plugin()

    def factory_audit_plugin(self) -> "VariableDiscoveryPlugin | None":
        if "audit_plugin" in self._mocks:
            return self._mocks["audit_plugin"]
        override_result = self._call_factory_override("audit_plugin_factory")
        if override_result is not None:
            return cast("VariableDiscoveryPlugin | None", override_result)
        return self._plugin_resolver.factory_audit_plugin()

    def factory_policy_registry(self) -> "FallbackPolicyRegistry":
        """Create or return cached FallbackPolicyRegistry.

        Phase 0: Stub factory for module structure.
        Wave 1+: Will initialize with plugin registry and default policies.
        """
        if "policy_registry" in self._mocks:
            return self._mocks["policy_registry"]

        override_result = self._call_factory_override("policy_registry_factory")
        if override_result is not None:
            return cast("FallbackPolicyRegistry", override_result)

        key = "policy_registry"
        with self._cache_lock:
            if key not in self._cache:
                from prism.scanner_core.policy_registry import FallbackPolicyRegistry

                self._cache[key] = FallbackPolicyRegistry()
        return self._cache[key]

    def factory_policy_manager(self) -> "PolicyManager":
        """Create or return cached PolicyManager.

        Phase 0: Stub factory for module structure.
        Wave 1+: Will coordinate policy resolution from DI registry.
        """
        if "policy_manager" in self._mocks:
            return self._mocks["policy_manager"]

        override_result = self._call_factory_override("policy_manager_factory")
        if override_result is not None:
            return cast("PolicyManager", override_result)

        key = "policy_manager"
        with self._cache_lock:
            if key not in self._cache:
                from prism.scanner_core.policy_manager import PolicyManager

                registry = self.factory_policy_registry()
                self._cache[key] = PolicyManager(registry=registry)
        return self._cache[key]

    @property
    def policy_manager(self) -> "PolicyManager":
        """Access the PolicyManager via property (Task 3.1).

        Wave 3: Provides convenient access to the cached PolicyManager instance
        through a property instead of requiring factory_policy_manager() calls.

        Returns:
            The cached PolicyManager instance.
        """
        return self.factory_policy_manager()

    @property
    def policy_registry(self) -> "FallbackPolicyRegistry":
        """Access the FallbackPolicyRegistry via property (Task 3.1).

        Wave 3: Provides convenient access to the cached FallbackPolicyRegistry instance
        through a property instead of requiring factory_policy_registry() calls.

        Returns:
            The cached FallbackPolicyRegistry instance.
        """
        return self.factory_policy_registry()

    def inject_mock(self, name: str, mock: Any) -> None:
        """Inject a mock for testing. Name must match a factory key."""
        self._mocks[name] = mock

    def clear_mocks(self) -> None:
        """Clear all injected mocks."""
        self._mocks.clear()

    def clear_cache(self) -> None:
        """Clear cached instances."""
        with self._cache_lock:
            self._cache.clear()


# ============================================================================
# Wave 4: Module-Level Consolidation Functions
# ============================================================================
# These functions provide a single source of truth for policy manager and
# registry access. All code should prefer:
#   - di.policy_manager (property, preferred)
#   - ensure_policy_manager(di) (module function, backward compat)
#   - di.factory_policy_manager() (legacy factory, still supported)
#
# Caching Strategy (Lazy, Cached):
# - First access: Creates instance via factory method
# - Subsequent accesses: Returns cached instance from _cache dict
# - Cache invalidation: Manual clear_cache() call required
# - Thread safety: Guarded by _cache_lock (threading.RLock)
# - Per-container: Each DIContainer has isolated _cache and _cache_lock


def ensure_policy_manager(di: DIContainer) -> "PolicyManager":
    """Access PolicyManager through module-level function (Wave 4 consolidation).

    Convenience function for backward compatibility. All callers should prefer
    di.policy_manager property for direct access.

    This function:
    - Delegates to DIContainer.policy_manager property
    - Returns cached instance (same object on multiple calls)
    - Thread-safe (guarded by container's _cache_lock)
    - Fails closed if DIContainer not initialized

    Args:
        di: DIContainer instance.

    Returns:
        The cached PolicyManager instance.

    Raises:
        ValueError: If DIContainer not properly initialized.

    Example:
        >>> di = DIContainer("role_path", scan_options)
        >>> manager = ensure_policy_manager(di)
        >>> # is equivalent to:
        >>> manager = di.policy_manager
    """
    return di.policy_manager


def ensure_policy_registry(di: DIContainer) -> "FallbackPolicyRegistry":
    """Access FallbackPolicyRegistry through module-level function (Wave 4 consolidation).

    Convenience function for backward compatibility. All callers should prefer
    di.policy_registry property for direct access.

    This function:
    - Delegates to DIContainer.policy_registry property
    - Returns cached instance (same object on multiple calls)
    - Thread-safe (guarded by container's _cache_lock)
    - Fails closed if DIContainer not initialized

    Args:
        di: DIContainer instance.

    Returns:
        The cached FallbackPolicyRegistry instance.

    Raises:
        ValueError: If DIContainer not properly initialized.

    Example:
        >>> di = DIContainer("role_path", scan_options)
        >>> registry = ensure_policy_registry(di)
        >>> # is equivalent to:
        >>> registry = di.policy_registry
    """
    return di.policy_registry
