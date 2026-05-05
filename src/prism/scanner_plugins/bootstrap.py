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
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from prism.scanner_plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


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
        from prism.scanner_plugins.default_scan_pipeline import (
            DefaultScanPipelinePlugin,
        )
        from prism.scanner_plugins.ansible import (
            AnsibleScanPipelinePlugin,
            AnsibleReadmeRendererPlugin,
        )
        from prism.scanner_plugins.ansible.default_policies import (
            AnsibleDefaultTaskAnnotationPolicyPlugin,
            AnsibleDefaultTaskLineParsingPolicyPlugin,
            AnsibleDefaultTaskTraversalPolicyPlugin,
            AnsibleDefaultVariableExtractorPolicyPlugin,
        )
        from prism.scanner_plugins.parsers.jinja import (
            DefaultJinjaAnalysisPolicyPlugin,
        )
        from prism.scanner_plugins.parsers.yaml import DefaultYAMLParsingPolicyPlugin
        from prism.scanner_plugins.parsers.comment_doc.role_notes_parser import (
            CommentDrivenDocumentationParser,
        )
        from prism.scanner_plugins.discovery import discover_entry_point_plugins

        staging_registry = PluginRegistry()
        staging_registry.replace_state(canonical_registry.snapshot_state())

        # Built-in plugin registration tables (extracted from __init__.py)
        _DIRECT_REGISTRATIONS: tuple[tuple[str, str, type], ...] = (
            ("comment_driven_doc", "default", CommentDrivenDocumentationParser),
            ("readme_renderer", "ansible", AnsibleReadmeRendererPlugin),
            ("scan_pipeline", "default", cast(type, DefaultScanPipelinePlugin)),
            ("scan_pipeline", "ansible", cast(type, AnsibleScanPipelinePlugin)),
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

        _DEFERRED_REGISTRATIONS: tuple[tuple[str, str, str, str], ...] = (
            (
                "variable_discovery",
                "ansible",
                "prism.scanner_plugins.ansible.variable_discovery",
                "AnsibleVariableDiscoveryPlugin",
            ),
            (
                "variable_discovery",
                "default",
                "prism.scanner_plugins.ansible.variable_discovery",
                "AnsibleVariableDiscoveryPlugin",
            ),
            (
                "feature_detection",
                "ansible",
                "prism.scanner_plugins.ansible.feature_detection",
                "AnsibleFeatureDetectionPlugin",
            ),
            (
                "feature_detection",
                "default",
                "prism.scanner_plugins.ansible.feature_detection",
                "AnsibleFeatureDetectionPlugin",
            ),
        )

        _RESERVED_UNSUPPORTED_PLATFORMS: tuple[str, ...] = (
            "kubernetes",
            "terraform",
        )

        _DIRECT_SLOT_DISPATCH: dict[str, tuple[str, str]] = {
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

        _DEFERRED_SLOT_DISPATCH: dict[str, tuple[str, str]] = {
            "variable_discovery": (
                "list_variable_discovery_plugins",
                "register_deferred_variable_discovery_plugin",
            ),
            "feature_detection": (
                "list_feature_detection_plugins",
                "register_deferred_feature_detection_plugin",
            ),
        }

        for slot, name, plugin_cls in _DIRECT_REGISTRATIONS:
            list_method, register_method = _DIRECT_SLOT_DISPATCH[slot]
            if name not in getattr(staging_registry, list_method)():
                getattr(staging_registry, register_method)(name, plugin_cls)

        for slot, name, module_path, class_name in _DEFERRED_REGISTRATIONS:
            list_method, register_method = _DEFERRED_SLOT_DISPATCH[slot]
            if name not in getattr(staging_registry, list_method)():
                getattr(staging_registry, register_method)(
                    name,
                    module_path,
                    class_name,
                )

        for platform_name in _RESERVED_UNSUPPORTED_PLATFORMS:
            if not staging_registry.is_reserved_unsupported_platform(platform_name):
                staging_registry.register_reserved_unsupported_platform(platform_name)

        staging_registry.set_default_platform_key("ansible")

        # Discovery defects are control-plane defects, so registry bootstrap
        # stays fail-closed until the staged registry is fully validated.
        discover_entry_point_plugins(
            registry=staging_registry,
            raise_on_error=True,
        )

        # Validate fallback singleton invariants after registry is populated
        # (deferred from defaults.py import-time to explicit bootstrap phase)
        from prism.scanner_plugins.defaults import _validate_singleton_invariants

        _validate_singleton_invariants()

        canonical_registry.replace_state_from(staging_registry)
        _DEFAULT_REGISTRY = canonical_registry
        logger.debug(
            "Plugin registry initialized with %d scan_pipeline plugins",
            len(canonical_registry.list_scan_pipeline_plugins()),
        )

        return _DEFAULT_REGISTRY


__all__ = [
    "get_default_plugin_registry",
    "initialize_default_registry",
    "is_registry_initialized",
]
