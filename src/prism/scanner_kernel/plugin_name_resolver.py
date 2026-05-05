"""Plugin name resolution and preflight invocation helpers."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Protocol, TypedDict

from prism.errors import PrismRuntimeError
from prism.scanner_data import ScanMetadata, ScanOptionsDict


class ScanPipelinePlugin(Protocol):
    def process_scan_pipeline(
        self,
        *,
        scan_options: ScanOptionsDict,
        scan_context: ScanMetadata,
    ) -> ScanMetadata: ...


class ScanPipelinePluginFactory(Protocol):
    def __call__(self) -> ScanPipelinePlugin: ...


class ScanPipelineRegistry(Protocol):
    def get_scan_pipeline_plugin(
        self,
        name: str,
    ) -> ScanPipelinePluginFactory | None: ...

    def list_scan_pipeline_plugins(self) -> list[str]: ...

    def get_default_platform_key(self) -> str | None: ...


class ScanPipelineRouting(TypedDict, total=False):
    mode: str
    selected_plugin: str
    selection_order: list[str]
    failure_mode: str


@dataclass(frozen=True, slots=True)
class RoutePreflightRuntimeCarrier:
    """Explicit carrier for selected route, preflight result, and runtime metadata."""

    plugin_name: str
    preflight_context: ScanMetadata
    routing: ScanPipelineRouting
    plugin_factory: ScanPipelinePluginFactory | None = None


def resolve_scan_pipeline_plugin_class(
    *,
    registry: ScanPipelineRegistry,
    plugin_name: str,
) -> ScanPipelinePluginFactory | None:
    """Resolve a scan-pipeline plugin class from a registry."""
    return registry.get_scan_pipeline_plugin(plugin_name)


def execute_scan_pipeline_plugin(
    *,
    plugin_class: ScanPipelinePluginFactory,
    scan_options: ScanOptionsDict,
    scan_context: ScanMetadata,
) -> ScanMetadata:
    """Instantiate and execute a scan-pipeline plugin."""
    plugin_instance = plugin_class()
    return plugin_instance.process_scan_pipeline(
        scan_options=copy.copy(scan_options),
        scan_context=copy.copy(scan_context),
    )


def _resolve_default_scan_pipeline_plugin_name(registry: ScanPipelineRegistry) -> str:
    list_plugins = getattr(registry, "list_scan_pipeline_plugins", None)
    get_plugin = getattr(registry, "get_scan_pipeline_plugin", None)
    get_default_platform_key = getattr(registry, "get_default_platform_key", None)

    registered: list[str] = []
    if callable(list_plugins):
        registered = [
            name for name in list_plugins() if isinstance(name, str) and name.strip()
        ]

    if "default" in registered:
        return "default"

    if callable(get_default_platform_key):
        default_name = get_default_platform_key()
        if isinstance(default_name, str) and default_name.strip():
            plugin_name = default_name.strip()
            if callable(get_plugin) and get_plugin(plugin_name) is not None:
                return plugin_name

    if len(registered) == 1:
        return registered[0]

    if registered:
        return sorted(registered)[0]

    raise PrismRuntimeError(
        code="scan_pipeline_default_unavailable",
        category="runtime",
        message="no explicit scan-pipeline plugin default is registered",
        detail={"registry_type": type(registry).__name__},
    )


def _resolve_policy_context_scan_pipeline_plugin_name(
    scan_options: ScanOptionsDict,
) -> str | None:
    policy_context = scan_options.get("policy_context")
    if not isinstance(policy_context, dict):
        return None

    selection_context = policy_context.get("selection")
    if not isinstance(selection_context, dict):
        return None

    plugin_name = selection_context.get("plugin")
    if not isinstance(plugin_name, str) or not plugin_name.strip():
        return None

    return plugin_name.strip()


def resolve_scan_pipeline_plugin_name(
    *,
    scan_options: ScanOptionsDict,
    registry: ScanPipelineRegistry | None = None,
) -> str:
    """Resolve the scan-pipeline plugin selector from canonical scan options."""
    configured = scan_options.get("scan_pipeline_plugin")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()

    configured_from_policy = _resolve_policy_context_scan_pipeline_plugin_name(
        scan_options
    )
    if configured_from_policy is not None:
        return configured_from_policy

    platform = scan_options.get("platform")
    if isinstance(platform, str) and platform.strip():
        return platform.strip()

    if registry is None:
        raise ValueError("registry must be provided for plugin name resolution")
    return _resolve_default_scan_pipeline_plugin_name(registry)
