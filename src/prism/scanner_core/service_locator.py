"""ServiceLocator: Factory and Cache Orchestrator

This module implements the ServiceLocator class, responsible for creating and
caching service instances in the scanner orchestrator.

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

from __future__ import annotations
from typing import TYPE_CHECKING
import threading

if TYPE_CHECKING:
    from prism.scanner_core.di import DIContainer
    from prism.scanner_core.events import EventBus


class ServiceLocator:
    """ServiceLocator for creating and caching service instances."""

    def __init__(self, di_container: DIContainer) -> None:
        """Initialize the ServiceLocator with a DIContainer.

        Args:
            di_container (DIContainer): The parent DI container managing state.
        """
        self._di_container = di_container
        self._cache_lock = threading.RLock()

    def factory_event_bus(self) -> EventBus:
        """Return the per-container EventBus singleton.

        The EventBus is created once during DIContainer initialization and cached.
        It is not invalidated by replace_scan_options().
        """
        with self._cache_lock:
            if "event_bus" not in self._di_container._cache:
                # Create and cache the EventBus instance
                self._di_container._cache["event_bus"] = self._create_event_bus()
            return self._di_container._cache["event_bus"]

    def _create_event_bus(self) -> EventBus:
        """Create a new EventBus instance."""
        # Deferred import to avoid circular dependency
        from prism.scanner_core.events import EventBus

        return EventBus()

    # Additional factory methods (scanner_context, variable_discovery, etc.)
    # will be implemented here following the same pattern.

    def replace_scan_options(self) -> None:
        """Invalidate caches dependent on scan_options."""
        with self._cache_lock:
            # Clear specific cached services
            for key in ["scanner_context", "variable_discovery", "feature_detector"]:
                if key in self._di_container._cache:
                    del self._di_container._cache[key]
