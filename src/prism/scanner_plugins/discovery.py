"""Entry-points-based plugin discovery for scanner extensibility.

External packages can register Prism scanner plugins by declaring entry
points in the ``prism.scanner_plugins`` group. Each entry point must resolve
to a callable that accepts a :class:`PluginRegistry` and registers one or
more plugin classes onto it.

Example (in an external package's pyproject.toml)::

    [project.entry-points."prism.scanner_plugins"]
    my_plugin = "my_pkg.plugins:register"

where ``my_pkg.plugins.register`` is::

    def register(registry):
        registry.register_scan_pipeline_plugin("my", MyScanPipelinePlugin)
"""

from __future__ import annotations

import logging
from importlib.metadata import EntryPoint, entry_points
from typing import Callable, Iterable

from prism.scanner_plugins.registry import (
    PluginAPIVersionMismatch,
    PluginRegistry,
    plugin_registry as canonical_plugin_registry,
)


PRISM_PLUGIN_ENTRY_POINT_GROUP = "prism.scanner_plugins"


logger = logging.getLogger(__name__)


class EntryPointPluginLoadError(RuntimeError):
    """Raised when an entry-point plugin cannot be loaded or registered."""


def _iter_entry_points(group: str) -> Iterable[EntryPoint]:
    return entry_points(group=group)


def discover_entry_point_plugins(
    *,
    group: str = PRISM_PLUGIN_ENTRY_POINT_GROUP,
    registry: PluginRegistry | None = None,
    raise_on_error: bool = False,
    iter_entry_points_fn: Callable[[str], Iterable[EntryPoint]] | None = None,
) -> list[str]:
    """Discover and register plugins exposed via entry points.

    Returns the list of entry-point names that were successfully registered.
    On error: logs a warning by default, or raises EntryPointPluginLoadError
    when ``raise_on_error`` is True. PluginAPIVersionMismatch is always
    re-raised since it indicates an incompatible plugin.
    """
    target_registry = registry or canonical_plugin_registry
    iter_fn = iter_entry_points_fn or _iter_entry_points
    registered: list[str] = []

    for ep in iter_fn(group):
        try:
            register_callable = ep.load()
        except Exception as exc:  # pragma: no cover - exercised via injection
            if raise_on_error:
                raise EntryPointPluginLoadError(
                    f"failed to load entry point '{ep.name}': {exc}"
                ) from exc
            logger.warning(
                "Failed to load Prism plugin entry point '%s': %s", ep.name, exc
            )
            continue

        if not callable(register_callable):
            message = (
                f"entry point '{ep.name}' must resolve to a callable "
                f"(got {type(register_callable).__name__})"
            )
            if raise_on_error:
                raise EntryPointPluginLoadError(message)
            logger.warning("%s", message)
            continue

        try:
            register_callable(target_registry)
        except PluginAPIVersionMismatch:
            raise
        except Exception as exc:
            if raise_on_error:
                raise EntryPointPluginLoadError(
                    f"entry point '{ep.name}' raised during registration: {exc}"
                ) from exc
            logger.warning(
                "Prism plugin entry point '%s' raised during registration: %s",
                ep.name,
                exc,
            )
            continue

        registered.append(ep.name)

    return registered


__all__ = [
    "PRISM_PLUGIN_ENTRY_POINT_GROUP",
    "EntryPointPluginLoadError",
    "discover_entry_point_plugins",
]
