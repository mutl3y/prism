"""Thin facade for API-layer access to scanner_plugins functionality.

This module provides a controlled boundary between the API layer and the plugin
layer, preventing direct scanner_plugins imports from spreading across top-level
API/CLI modules.

Most functions in this module are simple pass-through wrappers. The scan-pipeline
registry isolation helpers are the one owned adapter seam here because the API
entrypoint needs a protected registry view without becoming a composition root.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias, cast, runtime_checkable

if TYPE_CHECKING:
    from prism.scanner_config.audit_rules import AuditReport, AuditRule
    from prism.scanner_data.contracts_request import (
        PreparedPolicyBundle,
        PreparedYAMLParsingPolicy,
    )
    from prism.scanner_plugins.interfaces import (
        CommentDrivenDocumentationPlugin,
        ExtractPolicyPlugin,
        FeatureDetectionPlugin,
        JinjaAnalysisPolicyPlugin,
        OutputOrchestrationPlugin,
        ReadmeRendererPlugin,
        ScanPipelinePreflightContext,
        VariableDiscoveryPlugin,
        YAMLParsingPolicyPlugin,
    )
    from prism.scanner_plugins.registry import PluginRegistry


@runtime_checkable
class _HasScanOptions(Protocol):
    """Minimal DI interface for scan_options access."""

    scan_options: dict[str, object]


class ScanPipelinePluginFactory(Protocol):
    """Factory contract for scan-pipeline plugin construction."""

    def __call__(self) -> _ProcessScanPipelinePlugin: ...


class ScanPipelineRuntimeRegistry(Protocol):
    """Registry surface needed by API run_scan orchestration."""

    def get_scan_pipeline_plugin(
        self, name: str
    ) -> ScanPipelinePluginFactoryLike | None: ...

    def list_scan_pipeline_plugins(self) -> list[str]: ...

    def get_default_platform_key(self) -> str | None: ...

    def get_variable_discovery_plugin(
        self,
        name: str,
    ) -> type[VariableDiscoveryPlugin] | None: ...

    def get_feature_detection_plugin(
        self,
        name: str,
    ) -> type[FeatureDetectionPlugin] | None: ...

    def get_output_orchestration_plugin(
        self,
        name: str,
    ) -> type[OutputOrchestrationPlugin] | None: ...

    def get_comment_driven_doc_plugin(
        self,
        name: str,
    ) -> type[CommentDrivenDocumentationPlugin] | None: ...

    def get_extract_policy_plugin(
        self,
        name: str,
    ) -> type[ExtractPolicyPlugin] | None: ...

    def get_yaml_parsing_policy_plugin(
        self,
        name: str,
    ) -> type[YAMLParsingPolicyPlugin] | None: ...

    def get_jinja_analysis_policy_plugin(
        self,
        name: str,
    ) -> type[JinjaAnalysisPolicyPlugin] | None: ...

    def get_readme_renderer_plugin(
        self,
        name: str,
    ) -> type[ReadmeRendererPlugin] | None: ...

    def list_variable_discovery_plugins(self) -> list[str]: ...

    def list_feature_detection_plugins(self) -> list[str]: ...

    def list_output_orchestration_plugins(self) -> list[str]: ...

    def list_comment_driven_doc_plugins(self) -> list[str]: ...

    def list_extract_policy_plugins(self) -> list[str]: ...

    def list_yaml_parsing_policy_plugins(self) -> list[str]: ...

    def list_jinja_analysis_policy_plugins(self) -> list[str]: ...

    def list_readme_renderer_plugins(self) -> dict[str, type[ReadmeRendererPlugin]]: ...


class _ProcessScanPipelinePlugin(Protocol):
    def process_scan_pipeline(
        self,
        scan_options: dict[str, Any],
        scan_context: dict[str, Any],
    ) -> ScanPipelinePreflightContext: ...


class _OrchestratingScanPipelinePlugin(_ProcessScanPipelinePlugin, Protocol):
    def orchestrate_scan_payload(
        self,
        *,
        payload: dict[str, object],
        scan_options: dict[str, object],
        strict_mode: bool,
        preflight_context: dict[str, object] | None = None,
    ) -> dict[str, object]: ...


ScanPipelinePluginFactoryLike: TypeAlias = (
    "type[_ProcessScanPipelinePlugin] | ScanPipelinePluginFactory"
)


def _wrap_scan_pipeline_plugin_factory(
    plugin_factory: ScanPipelinePluginFactoryLike,
) -> ScanPipelinePluginFactory:
    if hasattr(plugin_factory, "orchestrate_scan_payload"):
        orchestrating_plugin_factory = cast(
            "type[_OrchestratingScanPipelinePlugin]",
            plugin_factory,
        )

        class _OrchestratingScanPipelinePluginIsolationWrapper:
            def __init__(self) -> None:
                self._inner = orchestrating_plugin_factory()

            def orchestrate_scan_payload(
                self,
                *,
                payload: dict[str, Any],
                scan_options: dict[str, Any],
                strict_mode: bool,
                preflight_context: dict[str, Any] | None = None,
            ) -> dict[str, Any]:
                return self._inner.orchestrate_scan_payload(
                    payload=payload,
                    scan_options=scan_options,
                    strict_mode=strict_mode,
                    preflight_context=preflight_context,
                )

            def process_scan_pipeline(
                self,
                scan_options: dict[str, Any],
                scan_context: dict[str, Any],
            ) -> ScanPipelinePreflightContext:
                return self._inner.process_scan_pipeline(
                    scan_options=scan_options,
                    scan_context=copy.deepcopy(scan_context),
                )

        def _orchestrating_factory() -> _ProcessScanPipelinePlugin:
            return _OrchestratingScanPipelinePluginIsolationWrapper()

        return _orchestrating_factory

    process_plugin_factory = cast("type[_ProcessScanPipelinePlugin]", plugin_factory)

    class _ScanPipelinePluginIsolationWrapper:
        def __init__(self) -> None:
            self._inner = process_plugin_factory()

        def process_scan_pipeline(
            self,
            scan_options: dict[str, Any],
            scan_context: dict[str, Any],
        ) -> ScanPipelinePreflightContext:
            return self._inner.process_scan_pipeline(
                scan_options=scan_options,
                scan_context=copy.deepcopy(scan_context),
            )

    def _process_factory() -> _ProcessScanPipelinePlugin:
        return _ScanPipelinePluginIsolationWrapper()

    return _process_factory


def isolate_scan_pipeline_registry(
    registry: ScanPipelineRuntimeRegistry,
) -> ScanPipelineRuntimeRegistry:
    """Return a registry view that isolates scan_context mutation per plugin call."""

    class _IsolatedScanPipelineRegistry:
        def __init__(self, inner: ScanPipelineRuntimeRegistry) -> None:
            self._inner = inner

        def get_scan_pipeline_plugin(
            self,
            name: str,
        ) -> ScanPipelinePluginFactory | None:
            plugin_factory = self._inner.get_scan_pipeline_plugin(name)
            if plugin_factory is None:
                return None
            return _wrap_scan_pipeline_plugin_factory(plugin_factory)

        def list_scan_pipeline_plugins(self) -> list[str]:
            return self._inner.list_scan_pipeline_plugins()

        def get_default_platform_key(self) -> str | None:
            return self._inner.get_default_platform_key()

        def get_variable_discovery_plugin(
            self,
            name: str,
        ) -> type[VariableDiscoveryPlugin] | None:
            return self._inner.get_variable_discovery_plugin(name)

        def get_feature_detection_plugin(
            self,
            name: str,
        ) -> type[FeatureDetectionPlugin] | None:
            return self._inner.get_feature_detection_plugin(name)

        def get_output_orchestration_plugin(
            self,
            name: str,
        ) -> type[OutputOrchestrationPlugin] | None:
            return self._inner.get_output_orchestration_plugin(name)

        def get_comment_driven_doc_plugin(
            self,
            name: str,
        ) -> type[CommentDrivenDocumentationPlugin] | None:
            return self._inner.get_comment_driven_doc_plugin(name)

        def get_extract_policy_plugin(
            self,
            name: str,
        ) -> type[ExtractPolicyPlugin] | None:
            return self._inner.get_extract_policy_plugin(name)

        def get_yaml_parsing_policy_plugin(
            self,
            name: str,
        ) -> type[YAMLParsingPolicyPlugin] | None:
            return self._inner.get_yaml_parsing_policy_plugin(name)

        def get_jinja_analysis_policy_plugin(
            self,
            name: str,
        ) -> type[JinjaAnalysisPolicyPlugin] | None:
            return self._inner.get_jinja_analysis_policy_plugin(name)

        def get_readme_renderer_plugin(
            self,
            name: str,
        ) -> type[ReadmeRendererPlugin] | None:
            return self._inner.get_readme_renderer_plugin(name)

        def list_variable_discovery_plugins(self) -> list[str]:
            return self._inner.list_variable_discovery_plugins()

        def list_feature_detection_plugins(self) -> list[str]:
            return self._inner.list_feature_detection_plugins()

        def list_output_orchestration_plugins(self) -> list[str]:
            return self._inner.list_output_orchestration_plugins()

        def list_comment_driven_doc_plugins(self) -> list[str]:
            return self._inner.list_comment_driven_doc_plugins()

        def list_extract_policy_plugins(self) -> list[str]:
            return self._inner.list_extract_policy_plugins()

        def list_yaml_parsing_policy_plugins(self) -> list[str]:
            return self._inner.list_yaml_parsing_policy_plugins()

        def list_jinja_analysis_policy_plugins(self) -> list[str]:
            return self._inner.list_jinja_analysis_policy_plugins()

        def list_readme_renderer_plugins(
            self,
        ) -> dict[str, type[ReadmeRendererPlugin]]:
            return self._inner.list_readme_renderer_plugins()

    return _IsolatedScanPipelineRegistry(registry)


def get_default_scan_pipeline_registry() -> ScanPipelineRuntimeRegistry:
    """Return the default registry wrapped with scan-pipeline isolation."""

    return isolate_scan_pipeline_registry(get_default_plugin_registry())


def get_default_plugin_registry() -> PluginRegistry:
    """Return the default plugin registry instance.

    This is a pass-through to scanner_plugins.DEFAULT_PLUGIN_REGISTRY.
    """
    from prism.scanner_plugins.bootstrap import get_default_plugin_registry as _get

    return _get()


def ensure_prepared_policy_bundle(
    *,
    scan_options: dict[str, object],
    di: _HasScanOptions | object,
) -> PreparedPolicyBundle:
    """Ensure prepared policy bundle is available from scan_options.

    This is a pass-through to scanner_plugins.bundle_resolver.ensure_prepared_policy_bundle.
    """
    from prism.scanner_plugins.bundle_resolver import (
        ensure_prepared_policy_bundle as _ensure_prepared_policy_bundle,
    )

    return _ensure_prepared_policy_bundle(scan_options=scan_options, di=di)


def resolve_comment_driven_documentation_plugin(
    di: object,
) -> CommentDrivenDocumentationPlugin:
    """Resolve the comment-driven documentation plugin from DI.

    This is a pass-through to scanner_plugins.defaults.resolve_comment_driven_documentation_plugin.
    """
    from prism.scanner_plugins.defaults import (
        resolve_comment_driven_documentation_plugin as _resolve_plugin,
    )

    return _resolve_plugin(di)


def load_audit_rules_from_file(rules_path: str) -> list[AuditRule]:
    """Load audit rules from a file path.

    This is a pass-through to scanner_plugins.audit.load_audit_rules_from_file.
    """
    from prism.scanner_plugins.audit.loader import load_audit_rules_from_file as _load

    return _load(rules_path)


def run_audit(payload: dict[str, object], rules: list[AuditRule]) -> AuditReport:
    """Run audit rules against a scan payload.

    This is a pass-through to scanner_plugins.audit.run_audit.
    """
    from prism.scanner_plugins.audit.runner import run_audit as _run_audit

    return _run_audit(payload, rules)


def resolve_yaml_parsing_policy_plugin(
    di: object | None = None,
    *,
    strict_mode: bool = True,
    registry: PluginRegistry | None = None,
) -> PreparedYAMLParsingPolicy:
    """Resolve the YAML parsing policy plugin from DI or registry.

    This is a pass-through to scanner_plugins.defaults.resolve_yaml_parsing_policy_plugin.
    """
    from prism.scanner_plugins.defaults import (
        resolve_yaml_parsing_policy_plugin as _resolve_plugin,
    )

    return _resolve_plugin(di, strict_mode=strict_mode, registry=registry)
