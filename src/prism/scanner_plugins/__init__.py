"""Scanner plugin package ownership for the fsrc lane.

Importing this module stays side-effect free until a caller explicitly asks for
the default registry through the exported bootstrap helpers.

Bootstrap logic is centralized in scanner_plugins.bootstrap to resolve
O001/O008/O010/O015 (DI/plugin bootstrap coupling and ordering risks).
"""

from __future__ import annotations

from prism.scanner_plugins.bootstrap import (
    get_default_plugin_registry,
    initialize_registry,
    initialize_default_registry,
)
from prism.scanner_plugins.registry import (
    PRISM_PLUGIN_API_VERSION,
    PluginAPIVersionMismatch,
    validate_plugin_api_version,
)
from prism.scanner_plugins.discovery import (
    PRISM_PLUGIN_ENTRY_POINT_GROUP,
    EntryPointPluginLoadError,
    discover_entry_point_plugins,
)
from prism.scanner_plugins.interfaces import ScanPipelinePlugin


def bootstrap_default_plugins(registry=None):
    """Deprecated wrapper for backward compatibility.

    New code should call scanner_plugins.bootstrap.initialize_default_registry()
    directly. This wrapper delegates to the centralized bootstrap module.

    When registry=None, returns the canonical singleton. When registry is provided,
    performs a one-time bootstrap on that custom registry (does not update singleton).

    Args:
        registry: Optional registry override (bootstrapped independently)

    Returns:
        The initialized PluginRegistry (singleton or custom)
    """
    if registry is None:
        return initialize_default_registry()
    return initialize_registry(registry)


__all__ = [
    "EntryPointPluginLoadError",
    "PRISM_PLUGIN_API_VERSION",
    "PRISM_PLUGIN_ENTRY_POINT_GROUP",
    "PluginAPIVersionMismatch",
    "ScanPipelinePlugin",
    "bootstrap_default_plugins",
    "discover_entry_point_plugins",
    "get_default_plugin_registry",
    "initialize_default_registry",
    "interfaces",
    "registry",
    "validate_plugin_api_version",
]
