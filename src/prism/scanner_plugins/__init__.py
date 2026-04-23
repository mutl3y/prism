"""Scanner plugin package ownership for the fsrc lane.

Importing this module bootstraps required defaults onto the canonical plugin
registry singleton and exposes that same singleton via DEFAULT_PLUGIN_REGISTRY.
"""

from __future__ import annotations

from typing import cast

from prism.scanner_plugins.policies import DefaultScanPipelinePlugin
from prism.scanner_plugins.ansible import AnsibleScanPipelinePlugin
from prism.scanner_plugins.policies import (
    DefaultTaskAnnotationPolicyPlugin,
)
from prism.scanner_plugins.policies import (
    DefaultTaskLineParsingPolicyPlugin,
)
from prism.scanner_plugins.policies import (
    DefaultTaskTraversalPolicyPlugin,
)
from prism.scanner_plugins.policies import (
    DefaultVariableExtractorPolicyPlugin,
)
from prism.scanner_plugins.parsers.jinja import JinjaAnalysisPolicyPlugin
from prism.scanner_plugins.parsers.yaml import YAMLParsingPolicyPlugin
from prism.scanner_plugins.parsers.comment_doc.role_notes_parser import (
    CommentDrivenDocumentationParser,
)
from prism.scanner_plugins.registry import PluginRegistry
from prism.scanner_plugins.registry import plugin_registry as canonical_plugin_registry
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


def bootstrap_default_plugins(registry: PluginRegistry | None = None) -> PluginRegistry:
    """Register baseline fsrc plugin ownership seams into the plugin registry."""

    active_registry = registry or canonical_plugin_registry

    if "default" not in active_registry.list_comment_driven_doc_plugins():
        active_registry.register_comment_driven_doc_plugin(
            "default",
            CommentDrivenDocumentationParser,
        )

    if "default" not in active_registry.list_scan_pipeline_plugins():
        active_registry.register_scan_pipeline_plugin(
            "default",
            cast(type[ScanPipelinePlugin], DefaultScanPipelinePlugin),
        )
    if "ansible" not in active_registry.list_scan_pipeline_plugins():
        active_registry.register_scan_pipeline_plugin(
            "ansible",
            cast(type[ScanPipelinePlugin], AnsibleScanPipelinePlugin),
        )
    if "task_line_parsing" not in active_registry.list_extract_policy_plugins():
        active_registry.register_extract_policy_plugin(
            "task_line_parsing",
            DefaultTaskLineParsingPolicyPlugin,
        )

    if "task_traversal" not in active_registry.list_extract_policy_plugins():
        active_registry.register_extract_policy_plugin(
            "task_traversal",
            DefaultTaskTraversalPolicyPlugin,
        )

    if "variable_extractor" not in active_registry.list_extract_policy_plugins():
        active_registry.register_extract_policy_plugin(
            "variable_extractor",
            DefaultVariableExtractorPolicyPlugin,
        )

    if "task_annotation_parsing" not in active_registry.list_extract_policy_plugins():
        active_registry.register_extract_policy_plugin(
            "task_annotation_parsing",
            DefaultTaskAnnotationPolicyPlugin,
        )

    if "yaml_parsing" not in active_registry.list_yaml_parsing_policy_plugins():
        active_registry.register_yaml_parsing_policy_plugin(
            "yaml_parsing",
            YAMLParsingPolicyPlugin,
        )

    if "jinja_analysis" not in active_registry.list_jinja_analysis_policy_plugins():
        active_registry.register_jinja_analysis_policy_plugin(
            "jinja_analysis",
            JinjaAnalysisPolicyPlugin,
        )

    if "ansible" not in active_registry.list_variable_discovery_plugins():
        active_registry.register_deferred_variable_discovery_plugin(
            "ansible",
            "prism.scanner_plugins.ansible.variable_discovery",
            "AnsibleVariableDiscoveryPlugin",
        )

    if "default" not in active_registry.list_variable_discovery_plugins():
        active_registry.register_deferred_variable_discovery_plugin(
            "default",
            "prism.scanner_plugins.ansible.variable_discovery",
            "AnsibleVariableDiscoveryPlugin",
        )

    if "ansible" not in active_registry.list_feature_detection_plugins():
        active_registry.register_deferred_feature_detection_plugin(
            "ansible",
            "prism.scanner_plugins.ansible.feature_detection",
            "AnsibleFeatureDetectionPlugin",
        )

    if "default" not in active_registry.list_feature_detection_plugins():
        active_registry.register_deferred_feature_detection_plugin(
            "default",
            "prism.scanner_plugins.ansible.feature_detection",
            "AnsibleFeatureDetectionPlugin",
        )

    for platform_name in ("kubernetes", "terraform"):
        if not active_registry.is_reserved_unsupported_platform(platform_name):
            active_registry.register_reserved_unsupported_platform(platform_name)

    # Auto-discover externally distributed plugins via entry points. Failures
    # are logged (not raised) so a broken third-party plugin cannot block
    # built-in scanner usage. PluginAPIVersionMismatch still propagates.
    discover_entry_point_plugins(registry=active_registry)

    return active_registry


DEFAULT_PLUGIN_REGISTRY = bootstrap_default_plugins()

__all__ = [
    "DEFAULT_PLUGIN_REGISTRY",
    "EntryPointPluginLoadError",
    "PRISM_PLUGIN_API_VERSION",
    "PRISM_PLUGIN_ENTRY_POINT_GROUP",
    "PluginAPIVersionMismatch",
    "bootstrap_default_plugins",
    "discover_entry_point_plugins",
    "interfaces",
    "registry",
    "validate_plugin_api_version",
]
