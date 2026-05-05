"""Scanner plugin package ownership for the fsrc lane.

Importing this module stays side-effect free until a caller explicitly asks for
the default registry through the exported bootstrap helpers.

Bootstrap logic is centralized in scanner_plugins.bootstrap to resolve
O001/O008/O010/O015 (DI/plugin bootstrap coupling and ordering risks).
"""

from __future__ import annotations

from prism.scanner_plugins.bootstrap import (
    get_default_plugin_registry,
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

    # Custom registry bootstrap (test/migration path only)
    # Apply bootstrap logic to custom registry instead of singleton
    from prism.scanner_plugins.default_scan_pipeline import DefaultScanPipelinePlugin
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
    from prism.scanner_plugins.parsers.jinja import DefaultJinjaAnalysisPolicyPlugin
    from prism.scanner_plugins.parsers.yaml import DefaultYAMLParsingPolicyPlugin
    from prism.scanner_plugins.parsers.comment_doc.role_notes_parser import (
        CommentDrivenDocumentationParser,
    )
    from typing import cast

    _DIRECT_REGISTRATIONS = (
        ("comment_driven_doc", "default", CommentDrivenDocumentationParser),
        ("readme_renderer", "ansible", AnsibleReadmeRendererPlugin),
        ("scan_pipeline", "default", cast(type, DefaultScanPipelinePlugin)),
        ("scan_pipeline", "ansible", cast(type, AnsibleScanPipelinePlugin)),
        (
            "extract_policy",
            "task_line_parsing",
            AnsibleDefaultTaskLineParsingPolicyPlugin,
        ),
        ("extract_policy", "task_traversal", AnsibleDefaultTaskTraversalPolicyPlugin),
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
        ("jinja_analysis_policy", "jinja_analysis", DefaultJinjaAnalysisPolicyPlugin),
    )

    _DEFERRED_REGISTRATIONS = (
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

    _RESERVED_UNSUPPORTED_PLATFORMS = ("kubernetes", "terraform")

    _DIRECT_SLOT_DISPATCH = {
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

    _DEFERRED_SLOT_DISPATCH = {
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
        if name not in getattr(registry, list_method)():
            getattr(registry, register_method)(name, plugin_cls)

    for slot, name, module_path, class_name in _DEFERRED_REGISTRATIONS:
        list_method, register_method = _DEFERRED_SLOT_DISPATCH[slot]
        if name not in getattr(registry, list_method)():
            getattr(registry, register_method)(name, module_path, class_name)

    for platform_name in _RESERVED_UNSUPPORTED_PLATFORMS:
        if not registry.is_reserved_unsupported_platform(platform_name):
            registry.register_reserved_unsupported_platform(platform_name)

    registry.set_default_platform_key("ansible")
    discover_entry_point_plugins(registry=registry, raise_on_error=True)

    return registry


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
