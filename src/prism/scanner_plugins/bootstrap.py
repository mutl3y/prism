"""Plugin bootstrap coordination and registry access facade.

Centralizes plugin registry initialization, entry-point discovery, and provides
a facade for accessing the canonical plugin registry singleton without direct
imports of the registry module from composition-root layers (di.py).

Resolves O001 (DI composition root coupling), O008 (bootstrap ordering risk),
O010 (defaults conditional import authority), O015 (core/plugin interface coupling).
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any, Callable, Literal, cast

if TYPE_CHECKING:
    from prism.scanner_plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)

DEFAULT_SUPPORTED_PLATFORM_KEY = "ansible"
RESERVED_UNSUPPORTED_PLATFORM_KEYS: tuple[str, ...] = (
    "kubernetes",
    "terraform",
)
PlatformSupportState = Literal[
    "supported",
    "reserved",
    "stubbed",
    "unsupported",
]


# Module-level singleton registry reference, populated by initialize_default_registry()
_DEFAULT_REGISTRY: PluginRegistry | None = None
_DEFAULT_REGISTRY_INIT_LOCK = threading.Lock()


def get_default_plugin_registry() -> PluginRegistry:
    """Return the canonical plugin registry singleton.

    This is the single authorized facade for accessing the registry from
    outside the scanner_plugins package (e.g., from di.py, defaults.py).
    """
    if _DEFAULT_REGISTRY is None:
        return initialize_default_registry()
    return _DEFAULT_REGISTRY


def is_registry_initialized() -> bool:
    """Check whether the default plugin registry has been initialized."""
    return _DEFAULT_REGISTRY is not None


def _distinct_platform_names(
    platform_key: str,
    runtime_aliases: tuple[str, ...],
) -> tuple[str, ...]:
    names: list[str] = []
    for name in (platform_key, *runtime_aliases):
        if name and name not in names:
            names.append(name)
    return tuple(names)


def _has_any_runtime_platform_seam(
    registry: PluginRegistry,
    *,
    platform_key: str,
) -> bool:
    return any(
        platform_key in names
        for names in (
            registry.list_scan_pipeline_plugins(),
            registry.list_variable_discovery_plugins(),
            registry.list_feature_detection_plugins(),
        )
    )


def _has_complete_runtime_platform_seams(
    registry: PluginRegistry,
    *,
    platform_key: str,
) -> bool:
    return all(
        registry_getter(platform_key) is not None
        for registry_getter in (
            registry.get_scan_pipeline_plugin,
            registry.get_variable_discovery_plugin,
            registry.get_feature_detection_plugin,
        )
    )


def describe_platform_registration_state(
    registry: PluginRegistry,
    *,
    platform_key: str,
) -> str:
    """Describe whether a platform key is executable, reserved, or unknown.

    The registry stays fail-closed: reserved/stubbed platforms are visible for
    controlled onboarding but are not treated as fully supported unless runtime
    seams are explicitly registered.
    """
    has_runtime_seams = _has_any_runtime_platform_seam(
        registry,
        platform_key=platform_key,
    )
    has_complete_runtime_seams = _has_complete_runtime_platform_seams(
        registry,
        platform_key=platform_key,
    )
    if registry.is_reserved_unsupported_platform(platform_key):
        if has_complete_runtime_seams:
            return "supported"
        return "reserved_partial" if has_runtime_seams else "reserved_unsupported"
    if has_complete_runtime_seams or has_runtime_seams:
        return "supported"
    return "unregistered"


def register_platform_plugin_bundle(
    registry: PluginRegistry,
    *,
    platform_key: str,
    support_state: PlatformSupportState,
    runtime_aliases: tuple[str, ...] = (),
    scan_pipeline_plugin: type[Any] | None = None,
    readme_renderer_plugin: type[Any] | None = None,
    variable_discovery_plugin: type[Any] | None = None,
    variable_discovery_loader: tuple[str, str] | None = None,
    feature_detection_plugin: type[Any] | None = None,
    feature_detection_loader: tuple[str, str] | None = None,
) -> None:
    """Register explicit platform seams without implying unsupported capabilities.

    Unsupported or stubbed platforms are recorded as reserved, while runtime
    seams are registered only when they are explicitly provided.
    """
    if support_state not in {"supported", "reserved", "stubbed", "unsupported"}:
        raise ValueError(f"Unsupported platform support state: {support_state!r}")
    if variable_discovery_plugin is not None and variable_discovery_loader is not None:
        raise ValueError(
            "Provide either variable_discovery_plugin or "
            "variable_discovery_loader, not both"
        )
    if feature_detection_plugin is not None and feature_detection_loader is not None:
        raise ValueError(
            "Provide either feature_detection_plugin or "
            "feature_detection_loader, not both"
        )

    runtime_names = _distinct_platform_names(platform_key, runtime_aliases)

    if support_state != "supported":
        registry.register_reserved_unsupported_platform(platform_key)

    if readme_renderer_plugin is not None:
        if platform_key not in registry.list_readme_renderer_plugins():
            registry.register_readme_renderer_plugin(platform_key, readme_renderer_plugin)

    if scan_pipeline_plugin is not None:
        for name in runtime_names:
            if name not in registry.list_scan_pipeline_plugins():
                registry.register_scan_pipeline_plugin(name, scan_pipeline_plugin)

    if variable_discovery_plugin is not None:
        for name in runtime_names:
            if name not in registry.list_variable_discovery_plugins():
                registry.register_variable_discovery_plugin(name, variable_discovery_plugin)
    elif variable_discovery_loader is not None:
        module_path, class_name = variable_discovery_loader
        for name in runtime_names:
            if name not in registry.list_variable_discovery_plugins():
                registry.register_deferred_variable_discovery_plugin(
                    name,
                    module_path,
                    class_name,
                )

    if feature_detection_plugin is not None:
        for name in runtime_names:
            if name not in registry.list_feature_detection_plugins():
                registry.register_feature_detection_plugin(name, feature_detection_plugin)
    elif feature_detection_loader is not None:
        module_path, class_name = feature_detection_loader
        for name in runtime_names:
            if name not in registry.list_feature_detection_plugins():
                registry.register_deferred_feature_detection_plugin(
                    name,
                    module_path,
                    class_name,
                )


def bootstrap_plugin_registry(
    registry: PluginRegistry,
    *,
    discover_entry_points_fn: Callable[..., list[str]] | None = None,
) -> PluginRegistry:
    """Populate a registry with built-ins, reserved platform names, and discovery.

    This keeps platform onboarding seams centralized without implying support for
    reserved platforms whose implementations are still absent.
    """
    from prism.scanner_plugins.default_scan_pipeline import DefaultScanPipelinePlugin
    from prism.scanner_plugins.ansible import (
        AnsibleReadmeRendererPlugin,
        AnsibleScanPipelinePlugin,
    )
    from prism.scanner_plugins.ansible.default_policies import (
        AnsibleDefaultTaskAnnotationPolicyPlugin,
        AnsibleDefaultTaskLineParsingPolicyPlugin,
        AnsibleDefaultTaskTraversalPolicyPlugin,
        AnsibleDefaultVariableExtractorPolicyPlugin,
    )
    from prism.scanner_plugins.discovery import discover_entry_point_plugins
    from prism.scanner_plugins.parsers.comment_doc.role_notes_parser import (
        CommentDrivenDocumentationParser,
    )
    from prism.scanner_plugins.parsers.jinja import DefaultJinjaAnalysisPolicyPlugin
    from prism.scanner_plugins.parsers.yaml import DefaultYAMLParsingPolicyPlugin
    from prism.scanner_plugins.defaults import _validate_singleton_invariants

    direct_registrations: tuple[tuple[str, str, type[Any]], ...] = (
        ("comment_driven_doc", "default", CommentDrivenDocumentationParser),
        ("scan_pipeline", "default", cast(type[Any], DefaultScanPipelinePlugin)),
        (
            "extract_policy",
            "task_line_parsing",
            AnsibleDefaultTaskLineParsingPolicyPlugin,
        ),
        (
            "extract_policy",
            "task_traversal",
            AnsibleDefaultTaskTraversalPolicyPlugin,
        ),
        (
            "extract_policy",
            "variable_extractor",
            AnsibleDefaultVariableExtractorPolicyPlugin,
        ),
        (
            "extract_policy",
            "task_annotation_parsing",
            AnsibleDefaultTaskAnnotationPolicyPlugin,
        ),
        ("yaml_parsing_policy", "yaml_parsing", DefaultYAMLParsingPolicyPlugin),
        (
            "jinja_analysis_policy",
            "jinja_analysis",
            DefaultJinjaAnalysisPolicyPlugin,
        ),
    )

    direct_slot_dispatch: dict[str, tuple[str, str]] = {
        "comment_driven_doc": (
            "list_comment_driven_doc_plugins",
            "register_comment_driven_doc_plugin",
        ),
        "scan_pipeline": (
            "list_scan_pipeline_plugins",
            "register_scan_pipeline_plugin",
        ),
        "extract_policy": (
            "list_extract_policy_plugins",
            "register_extract_policy_plugin",
        ),
        "yaml_parsing_policy": (
            "list_yaml_parsing_policy_plugins",
            "register_yaml_parsing_policy_plugin",
        ),
        "jinja_analysis_policy": (
            "list_jinja_analysis_policy_plugins",
            "register_jinja_analysis_policy_plugin",
        ),
        "readme_renderer": (
            "list_readme_renderer_plugins",
            "register_readme_renderer_plugin",
        ),
    }

    for slot, name, plugin_cls in direct_registrations:
        list_method, register_method = direct_slot_dispatch[slot]
        if name not in getattr(registry, list_method)():
            getattr(registry, register_method)(name, plugin_cls)

    register_platform_plugin_bundle(
        registry,
        platform_key=DEFAULT_SUPPORTED_PLATFORM_KEY,
        support_state="supported",
        runtime_aliases=("default",),
        scan_pipeline_plugin=cast(type[Any], AnsibleScanPipelinePlugin),
        readme_renderer_plugin=AnsibleReadmeRendererPlugin,
        variable_discovery_loader=(
            "prism.scanner_plugins.ansible.variable_discovery",
            "AnsibleVariableDiscoveryPlugin",
        ),
        feature_detection_loader=(
            "prism.scanner_plugins.ansible.feature_detection",
            "AnsibleFeatureDetectionPlugin",
        ),
    )

    for platform_name in RESERVED_UNSUPPORTED_PLATFORM_KEYS:
        register_platform_plugin_bundle(
            registry,
            platform_key=platform_name,
            support_state="unsupported",
        )

    registry.set_default_platform_key(DEFAULT_SUPPORTED_PLATFORM_KEY)

    if discover_entry_points_fn is None:
        discover_entry_points_fn = discover_entry_point_plugins
    discover_entry_points_fn(registry=registry, raise_on_error=True)

    _validate_singleton_invariants()
    return registry


def initialize_default_registry() -> PluginRegistry:
    """Initialize and return the canonical plugin registry singleton.

    Populates the registry with built-in plugins and discovers entry-point
    plugins. Safe to call multiple times (idempotent); returns the existing
    registry if already initialized.

    This function is invoked lazily on the first explicit registry access.

    Returns:
        The initialized PluginRegistry singleton.
    """
    global _DEFAULT_REGISTRY

    if _DEFAULT_REGISTRY is not None:
        return _DEFAULT_REGISTRY

    with _DEFAULT_REGISTRY_INIT_LOCK:
        if _DEFAULT_REGISTRY is not None:
            return _DEFAULT_REGISTRY

        from prism.scanner_plugins.registry import (
            PluginRegistry,
            plugin_registry as canonical_registry,
        )
        from prism.scanner_plugins.discovery import discover_entry_point_plugins

        staging_registry = PluginRegistry()
        staging_registry.replace_state(canonical_registry.snapshot_state())

        # Discovery defects are control-plane defects, so registry bootstrap
        # stays fail-closed until the staged registry is fully validated.
        bootstrap_plugin_registry(
            staging_registry,
            discover_entry_points_fn=discover_entry_point_plugins,
        )

        canonical_registry.replace_state_from(staging_registry)
        _DEFAULT_REGISTRY = canonical_registry
        logger.debug(
            "Plugin registry initialized with %d scan_pipeline plugins",
            len(canonical_registry.list_scan_pipeline_plugins()),
        )

        return _DEFAULT_REGISTRY


__all__ = [
    "DEFAULT_SUPPORTED_PLATFORM_KEY",
    "PlatformSupportState",
    "RESERVED_UNSUPPORTED_PLATFORM_KEYS",
    "bootstrap_plugin_registry",
    "describe_platform_registration_state",
    "get_default_plugin_registry",
    "initialize_default_registry",
    "is_registry_initialized",
    "register_platform_plugin_bundle",
]
