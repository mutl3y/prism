"""Plugin resolution layer for DIContainer decomposition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prism.errors import PrismRuntimeError

if TYPE_CHECKING:
    from prism.scanner_core.di import DIContainer
    from prism.scanner_plugins.interfaces import (
        CommentDrivenDocumentationPlugin,
        FeatureDetectionPlugin,
        JinjaAnalysisPolicyPlugin,
        VariableDiscoveryPlugin,
        YAMLParsingPolicyPlugin,
    )
    from prism.scanner_data.contracts_request import (
        PreparedTaskAnnotationPolicy,
        PreparedTaskLineParsingPolicy,
        PreparedTaskTraversalPolicy,
        PreparedVariableExtractorPolicy,
    )
    from prism.scanner_plugins.registry import PluginRegistry


class PluginResolver:
    """Resolve plugins from registry or DI wiring (via delegated overrides).

    PluginResolver is stateless and delegates mock/override decision-making
    back to DIContainer. All plugin factory methods:
    - Check for mocks in DIContainer._mocks first
    - Check for overrides in DIContainer._factory_overrides second
    - Execute resolver logic (registry lookup, optional returns) third

    This pattern keeps orchestration centralized in DIContainer while moving
    the resolver implementation logic into a dedicated class.
    """

    def __init__(self, di: "DIContainer") -> None:
        """Initialize resolver with reference to container.

        Args:
            di: DIContainer reference for accessing mocks, overrides, registry, platform_key
        """
        self._di = di

    def _get_registry(self) -> "PluginRegistry":
        """Return the injected plugin registry or raise."""
        if self._di.plugin_registry is None:
            raise PrismRuntimeError(
                code="missing_plugin_registry",
                category="dependency-injection",
                message="No plugin registry provided to DIContainer",
                detail={
                    "required_for": "plugin resolution",
                },
            )
        return self._di.plugin_registry

    def _resolve_platform_key(self) -> str:
        """Return pre-resolved platform key or delegate to module-level resolver."""
        from prism.scanner_core.di import resolve_platform_key

        if self._di.platform_key is not None:
            return self._di.platform_key
        return resolve_platform_key(self._di.scan_options, self._di.plugin_registry)

    def factory_variable_discovery_plugin(self) -> "VariableDiscoveryPlugin":
        """Resolve variable-discovery plugin via registry; fail-closed if unregistered.

        Mock and override checks happen in DIContainer; this method executes
        resolver logic only.
        """
        from prism.scanner_core.di import _construct_runtime_plugin

        platform_key = self._resolve_platform_key()
        registry = self._get_registry()
        plugin_cls = registry.get_variable_discovery_plugin(platform_key)
        if plugin_cls is None:
            raise PrismRuntimeError(
                code="unregistered_plugin",
                category="plugin-resolution",
                message="No variable_discovery plugin registered for platform.",
                detail={
                    "plugin_kind": "variable_discovery",
                    "platform_key": platform_key,
                    "remediation": "Ensure scanner_plugins bootstrap has run.",
                },
            )
        return _construct_runtime_plugin(
            plugin_cls,
            plugin_kind="variable_discovery",
            platform_key=platform_key,
            di=self._di,
        )

    def factory_feature_detection_plugin(self) -> "FeatureDetectionPlugin":
        """Resolve feature-detection plugin via registry; fail-closed if unregistered.

        Mock and override checks happen in DIContainer; this method executes
        resolver logic only.
        """
        from prism.scanner_core.di import _construct_runtime_plugin

        platform_key = self._resolve_platform_key()
        registry = self._get_registry()
        plugin_cls = registry.get_feature_detection_plugin(platform_key)
        if plugin_cls is None:
            raise PrismRuntimeError(
                code="unregistered_plugin",
                category="plugin-resolution",
                message="No feature_detection plugin registered for platform.",
                detail={
                    "plugin_kind": "feature_detection",
                    "platform_key": platform_key,
                    "remediation": "Ensure scanner_plugins bootstrap has run.",
                },
            )
        return _construct_runtime_plugin(
            plugin_cls,
            plugin_kind="feature_detection",
            platform_key=platform_key,
            di=self._di,
        )

    def factory_comment_driven_doc_plugin(
        self,
    ) -> "CommentDrivenDocumentationPlugin | None":
        """Resolve optional comment-driven documentation plugin from DI wiring.

        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_task_annotation_policy_plugin(
        self,
    ) -> "PreparedTaskAnnotationPolicy | None":
        """Resolve optional task-annotation policy plugin from DI wiring.

        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_task_line_parsing_policy_plugin(
        self,
    ) -> "PreparedTaskLineParsingPolicy | None":
        """Resolve optional task-line parsing policy plugin from DI wiring.

        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_task_traversal_policy_plugin(
        self,
    ) -> "PreparedTaskTraversalPolicy | None":
        """Resolve optional task-traversal policy plugin from DI wiring.

        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_variable_extractor_policy_plugin(
        self,
    ) -> "PreparedVariableExtractorPolicy | None":
        """Resolve optional variable-extractor policy plugin from DI wiring.

        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_yaml_parsing_policy_plugin(self) -> "YAMLParsingPolicyPlugin | None":
        """Resolve optional YAML parsing policy plugin from DI wiring.

        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_jinja_analysis_policy_plugin(
        self,
    ) -> "JinjaAnalysisPolicyPlugin | None":
        """Resolve optional Jinja analysis policy plugin from DI wiring.

        Mock and override checks happen in DIContainer.
        """
        return None

    def factory_audit_plugin(self) -> "VariableDiscoveryPlugin | None":
        """Return the injected audit plugin, or None if audit is not configured (opt-in).

        Mock and override checks happen in DIContainer.
        """
        return None
