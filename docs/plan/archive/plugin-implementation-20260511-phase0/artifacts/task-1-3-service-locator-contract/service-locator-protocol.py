"""ServiceLocator Protocol Definition

This module defines the public interface for ServiceLocator, the class responsible
for creating and caching service instances in the scanner orchestrator.

Key Responsibilities:
- Coordinate six service factories (EventBus, ScannerContext, VariableDiscovery, etc.)
- Manage service caching with thread-safe access
- Support testing via mocking and factory overrides
- Handle deferred imports for circular dependency prevention
- Coordinate with DIContainer for state management

Thread Safety:
All factory methods are GIL-safe through explicit threading.RLock() coordination with
the parent DIContainer. Callers do not need to manage locks directly.
"""

from typing import Protocol, Callable, TypeVar, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from prism.scanner_core.events import EventBus
    from prism.scanner_core.scanner_context import ScannerContext
    from prism.scanner_core.variable_discovery import VariableDiscovery
    from prism.scanner_core.feature_detector import FeatureDetector
    from prism.scanner_data.builders import VariableRowBuilder
    from prism.scanner_core.protocols_runtime import BlockerFactBuilder


T = TypeVar("T")


class ServiceLocatorProtocol(Protocol):
    """Protocol for service location and creation in the scanner orchestrator.

    A ServiceLocator is responsible for:
    1. Creating/retrieving cached service instances
    2. Supporting factory overrides (for testing)
    3. Supporting mocks (for unit tests)
    4. Coordinating cache invalidation with DIContainer
    5. Managing thread-safe access to all services

    All factory methods are reentrant and GIL-safe. Multiple threads may call
    these methods simultaneously without explicit locking.
    """

    def factory_event_bus(self) -> "EventBus":
        """Return the per-container EventBus singleton.

        The EventBus is created once during DIContainer initialization and cached.
        It is not invalidated by replace_scan_options().

        Returns:
            EventBus: The container's singleton event bus instance.

        Raises:
            PrismRuntimeError: If EventBus creation fails (should not occur in normal flow).

        Thread Safety:
            Always GIL-safe. Safe to call concurrently from multiple threads.
            Returns the same instance across calls.

        Caching:
            Singleton per container. Never invalidated.

        Mock Support:
            ✅ Supported via inject_mock("event_bus", mock_instance)
        """
        ...

    def factory_scanner_context(self) -> "ScannerContext":
        """Create or return cached ScannerContext with runtime wiring.

        ScannerContext is created once per container and cached. It depends on:
        - scanner_context_wiring dict (from DIContainer)
        - scan_options (snapshot from DIContainer)
        - role_path (from DIContainer)

        The ScannerContext is NOT invalidated by replace_scan_options() because
        it is created at runtime via the wiring function which controls the
        invalidation boundary.

        Returns:
            ScannerContext: The container's scanner context instance.

        Raises:
            RuntimeError: If scanner_context_wiring is not configured.
            PrismRuntimeError: If ScannerContext creation fails.

        Thread Safety:
            GIL-safe via container's _cache_lock. Multiple threads can call this
            without explicit synchronization.

        Caching:
            Created once per container and cached. NOT invalidated by replace_scan_options().

        Mock Support:
            ✅ Supported via inject_mock("scanner_context", mock_instance)

        Override Support:
            ✅ Supported via factory override "scanner_context_factory"
        """
        ...

    def factory_variable_discovery(self) -> "VariableDiscovery":
        """Create or return cached VariableDiscovery with policy injection.

        VariableDiscovery is created once per container and cached. It depends on:
        - scan_options (snapshot)
        - role_path
        - Deferred import of VariableDiscovery class (breaks circular dependency)

        VariableDiscovery imports from scanner_extract, which imports di_helpers.
        The deferred import in the factory method prevents import-time circular deps.

        This is INVALIDATED by replace_scan_options() because the policy context
        affects variable discovery behavior.

        Returns:
            VariableDiscovery: The container's cached variable discovery instance.

        Raises:
            PrismRuntimeError: If VariableDiscovery creation fails.
            ImportError: If deferred import cannot be resolved (should not occur).

        Thread Safety:
            GIL-safe via container's _cache_lock. Reentrant.

        Caching:
            Created once per container and cached.
            ✅ INVALIDATED by replace_scan_options() - is in _SCAN_OPTION_DEPENDENT_CACHE_KEYS

        Mock Support:
            ✅ Supported via inject_mock("variable_discovery", mock_instance)

        Override Support:
            ✅ Supported via factory override "variable_discovery_factory"

        Deferred Import:
            ✅ Uses _create_variable_discovery() helper to import VariableDiscovery
               only when first called, preventing circular import at module load time
        """
        ...

    def factory_feature_detector(self) -> "FeatureDetector":
        """Create or return cached FeatureDetector with task catalog access.

        FeatureDetector is created once per container and cached. It depends on:
        - scan_options (snapshot)
        - role_path
        - Deferred import of FeatureDetector class (breaks circular dependency)

        FeatureDetector imports collect_task_handler_catalog from scanner_extract,
        creating a potential circular dependency. The deferred import in the factory
        method prevents this at module load time.

        This is INVALIDATED by replace_scan_options() because feature detection
        behavior depends on the policy context.

        Returns:
            FeatureDetector: The container's cached feature detector instance.

        Raises:
            PrismRuntimeError: If FeatureDetector creation fails.
            ImportError: If deferred import cannot be resolved (should not occur).

        Thread Safety:
            GIL-safe via container's _cache_lock. Reentrant.

        Caching:
            Created once per container and cached.
            ✅ INVALIDATED by replace_scan_options() - is in _SCAN_OPTION_DEPENDENT_CACHE_KEYS

        Mock Support:
            ✅ Supported via inject_mock("feature_detector", mock_instance)

        Override Support:
            ✅ Supported via factory override "feature_detector_factory"

        Deferred Import:
            ✅ Uses _create_feature_detector() helper to import FeatureDetector
               only when first called, preventing circular import at module load time
        """
        ...

    def factory_variable_row_builder(self) -> "VariableRowBuilder":
        """Create or return cached VariableRowBuilder for row construction.

        VariableRowBuilder is a lightweight utility for assembling variable rows.
        It is created once per container and cached. It has no dependencies on
        scan_options or policy context, so it is NOT invalidated by replace_scan_options().

        Returns:
            VariableRowBuilder: The container's cached row builder instance.

        Raises:
            PrismRuntimeError: If VariableRowBuilder creation fails (should not occur).

        Thread Safety:
            GIL-safe via container's _cache_lock.

        Caching:
            Created once per container and cached.
            ❌ NOT invalidated by replace_scan_options() - has no policy dependency

        Mock Support:
            ❌ Not typically mocked (lightweight utility class)

        Override Support:
            ❌ Not supported (limited use case)
        """
        ...

    def factory_blocker_fact_builder(self) -> "BlockerFactBuilder":
        """Return the blocker-fact builder callable (plugin-layer owned).

        BlockerFactBuilder is a callable (Callable[[...], BlockerFact]) that
        constructs blocker facts during scanner runtime. It is either:
        1. Injected via blocker_fact_builder_fn in DIContainer.__init__()
        2. Or resolved via scanner_plugins.defaults.resolve_blocker_fact_builder()

        This is a simple dispatch - no complex creation logic. It is created once
        per container and cached.

        Returns:
            BlockerFactBuilder: The callable for building blocker facts.

        Raises:
            ImportError: If fallback import from scanner_plugins.defaults fails.
            ValueError: If no blocker fact builder can be resolved.

        Thread Safety:
            GIL-safe via container's _cache_lock.

        Caching:
            Retrieved/created once and cached.
            ❌ NOT invalidated by replace_scan_options() - determined at container init

        Mock Support:
            ❌ Not typically mocked

        Override Support:
            ✅ Supported via factory override "blocker_fact_builder_factory"

        Import Handling:
            Fallback import from scanner_plugins.defaults if not injected.
            No deferred import needed (no circular dependency risk).
        """
        ...


class ServiceLocator:
    """Concrete implementation of ServiceLocatorProtocol.

    ServiceLocator delegates to DIContainer for:
    - Mock injection/retrieval
    - Factory override coordination
    - Cache management and locking
    - scan_options snapshot access
    - State access (role_path, registry, wiring, etc.)

    ServiceLocator owns:
    - The 6 service factory methods
    - Deferred import helpers for circular dependency breaking
    - Thread-safe caching semantics

    Initialization:
        The ServiceLocator is NOT instantiated directly. It is created and owned
        by DIContainer during DIContainer.__init__().

        di = DIContainer(role_path, scan_options, ...)
        # ServiceLocator is created internally and accessible as di._service_locator

    Public Access:
        Code accesses ServiceLocator methods through DIContainer facade:
            service = di.factory_variable_discovery()  # delegates to service_locator

        Direct ServiceLocator access is not recommended in user code.
    """

    def __init__(self, di: Any) -> None:
        """Initialize ServiceLocator with reference to parent DIContainer.

        Args:
            di: The parent DIContainer instance. ServiceLocator delegates state
                management, caching, and coordination to this container.
        """
        self._di = di

    def factory_event_bus(self) -> "EventBus":
        """Return the per-container EventBus singleton."""
        return self._di._event_bus

    def factory_scanner_context(self) -> "ScannerContext":
        """Create ScannerContext only when runtime seam wiring is provided."""
        from typing import cast

        scanner_context_cls = self._di._scanner_context_wiring.get(
            "scanner_context_cls"
        )
        prepare_scan_context_fn = self._di._scanner_context_wiring.get(
            "prepare_scan_context_fn"
        )
        if scanner_context_cls is None or prepare_scan_context_fn is None:
            raise RuntimeError(
                "factory_scanner_context is disabled: scanner_context_wiring is "
                "not configured. ScannerContext requires prepare_scan_context_fn "
                "runtime seam injection."
            )

        scanner_context_kwargs: dict[str, Any] = {
            "di": self._di,
            "role_path": self._di._role_path,
            "scan_options": self._di._snapshot_scan_options(),
            "prepare_scan_context_fn": prepare_scan_context_fn,
        }

        scanner_context_factory = cast(
            "Callable[..., ScannerContext]",
            scanner_context_cls,
        )
        return scanner_context_factory(**scanner_context_kwargs)

    def factory_variable_discovery(self) -> "VariableDiscovery":
        """Create or return cached VariableDiscovery."""
        if "variable_discovery" in self._di._mocks:
            return self._di._mocks["variable_discovery"]

        override_result = self._di._call_factory_override("variable_discovery_factory")
        if override_result is not None:
            return override_result

        key = "variable_discovery"
        with self._di._cache_lock:
            if key not in self._di._cache:
                self._di._cache[key] = _create_variable_discovery(
                    self._di,
                    self._di._role_path,
                    self._di._snapshot_scan_options(),
                )

        return self._di._cache[key]

    def factory_feature_detector(self) -> "FeatureDetector":
        """Create or return cached FeatureDetector."""
        key = "feature_detector"
        if "feature_detector" in self._di._mocks:
            return self._di._mocks["feature_detector"]

        override_result = self._di._call_factory_override("feature_detector_factory")
        if override_result is not None:
            return override_result

        with self._di._cache_lock:
            if key not in self._di._cache:
                self._di._cache[key] = _create_feature_detector(
                    self._di,
                    self._di._role_path,
                    self._di._snapshot_scan_options(),
                )

        return self._di._cache[key]

    def factory_variable_row_builder(self) -> "VariableRowBuilder":
        """Create cached VariableRowBuilder for row construction helpers."""
        from prism.scanner_data.builders import VariableRowBuilder

        key = "variable_row_builder"
        with self._di._cache_lock:
            if key not in self._di._cache:
                self._di._cache[key] = VariableRowBuilder()
        return self._di._cache[key]

    def factory_blocker_fact_builder(self) -> "BlockerFactBuilder":
        """Return the blocker-fact builder callable (plugin-layer owned)."""
        key = "blocker_fact_builder"
        with self._di._cache_lock:
            if key not in self._di._cache:
                if self._di._blocker_fact_builder_fn is not None:
                    fn = self._di._blocker_fact_builder_fn
                else:
                    from prism.scanner_plugins.defaults import (
                        resolve_blocker_fact_builder,
                    )

                    fn = resolve_blocker_fact_builder()
                self._di._cache[key] = fn
        return self._di._cache[key]


# ============================================================================
# Deferred Import Helpers (used by ServiceLocator factory methods)
# ============================================================================


def _create_variable_discovery(
    di: Any,
    role_path: str,
    scan_options: dict[str, object],
) -> "VariableDiscovery":
    """Import VariableDiscovery only at the DI composition seam.

    This deferred import breaks the circular dependency:
        scanner_core.di → scanner_core.variable_discovery
                       → scanner_extract (imports di_helpers)
                       → scanner_core.di_helpers (imports di)

    By deferring the import to runtime (first factory call), we allow
    all modules to load successfully in order.
    """
    from prism.scanner_core.variable_discovery import VariableDiscovery

    return VariableDiscovery(di=di, role_path=role_path, scan_options=scan_options)


def _create_feature_detector(
    di: Any,
    role_path: str,
    scan_options: dict[str, object],
) -> "FeatureDetector":
    """Import FeatureDetector only at the DI composition seam.

    This deferred import breaks the circular dependency:
        scanner_core.di → scanner_core.feature_detector
                       → scanner_extract (imports di_helpers)
                       → scanner_core.di_helpers (imports di)

    By deferring the import to runtime (first factory call), we allow
    all modules to load successfully in order.
    """
    from prism.scanner_core.feature_detector import FeatureDetector

    return FeatureDetector(di=di, role_path=role_path, scan_options=scan_options)
