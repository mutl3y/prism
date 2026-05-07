"""Plugin seams facade for scanner_readme layer.

This module provides the canonical import path for README renderer plugin
abstractions and resolver functions. All scanner_readme modules import from
this facade instead of directly from scanner_plugins, maintaining layer
isolation and enabling future plugin architecture changes without rippling
through the scanner_readme domain.
"""

from __future__ import annotations

from prism.scanner_plugins.interfaces import ReadmeRendererPlugin
from prism.scanner_plugins import PluginRegistry

__all__ = [
    "ReadmeRendererPlugin",
    "resolve_readme_renderer_plugin",
]


def resolve_readme_renderer_plugin(
    platform_key: str,
    *,
    registry: "PluginRegistry | None" = None,
) -> ReadmeRendererPlugin:
    """Resolve readme renderer plugin class for the given platform key.

    Args:
        platform_key: Platform identifier (e.g., 'ansible', 'kubernetes').
        registry: Optional explicit PluginRegistry override.

    Returns:
        Instantiated ReadmeRendererPlugin for the specified platform.

    Raises:
        ValueError: If no renderer plugin is registered for platform_key.
    """
    from prism.scanner_plugins.defaults import (
        resolve_readme_renderer_plugin as _resolve,
    )

    return _resolve(platform_key, registry=registry)
