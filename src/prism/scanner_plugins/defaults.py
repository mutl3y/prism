"""Default plugin fallbacks for fsrc scanner plugin ownership seams."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, NoReturn, Protocol, cast
from collections.abc import Mapping

from prism.errors import PrismRuntimeError
from prism.scanner_plugins.ansible.default_policies import (
    AnsibleDefaultTaskAnnotationPolicyPlugin,
    AnsibleDefaultTaskLineParsingPolicyPlugin,
    AnsibleDefaultTaskTraversalPolicyPlugin,
    AnsibleDefaultVariableExtractorPolicyPlugin,
)
from prism.scanner_plugins.parsers.yaml import DefaultYAMLParsingPolicyPlugin
from prism.scanner_plugins.parsers.jinja import DefaultJinjaAnalysisPolicyPlugin
from prism.scanner_plugins.parsers.comment_doc.role_notes_parser import (
    CommentDrivenDocumentationParser,
)
from prism.scanner_plugins.interfaces import (
    CommentDrivenDocumentationPlugin,
    ReadmeRendererPlugin,
)
from prism.scanner_data.contracts_request import (
    PreparedJinjaAnalysisPolicy,
    ScanMetadata,
    ScanOptionsDict,
    ScanPolicyBlockerFacts,
    PreparedTaskAnnotationPolicy,
    PreparedTaskLineParsingPolicy,
    PreparedTaskTraversalPolicy,
    PreparedVariableExtractorPolicy,
    PreparedYAMLParsingPolicy,
)

if TYPE_CHECKING:
    from prism.scanner_plugins.registry import PluginRegistry
    from prism.scanner_plugins.parsers.comment_doc.runbook_renderer import RunbookRow


class BlockerFactBuilder(Protocol):
    def __call__(
        self,
        *,
        scan_options: ScanOptionsDict,
        metadata: ScanMetadata,
        di: object,
    ) -> ScanPolicyBlockerFacts: ...


logger = logging.getLogger(__name__)


def _get_registry_from_di(di: object | None) -> "PluginRegistry | None":
    """Extract plugin_registry from DI container, or None.

    Shared seam for registry precedence between defaults and loader.
    Does not fall back to bootstrap singleton.
    """
    if di is None:
        return None
    return getattr(di, "plugin_registry", None)


def _resolve_registry(
    di: object | None = None, registry: "PluginRegistry | None" = None
) -> "PluginRegistry":
    """Resolve plugin registry: explicit registry > DI registry > bootstrap singleton.

    Uses scanner_plugins.bootstrap facade (O008/O010 remediation) instead of
    direct plugin_registry import to maintain explicit bootstrap phase ordering.
    """
    if registry is not None:
        return registry

    di_registry = _get_registry_from_di(di)
    if di_registry is not None:
        return di_registry

    from prism.scanner_plugins.bootstrap import get_default_plugin_registry

    return get_default_plugin_registry()


def _scan_options_from_di(di: object | None) -> ScanOptionsDict | None:
    """Return scan_options from DI when the container exposes a mapping snapshot."""
    if di is None:
        return None
    scan_options = getattr(di, "scan_options", None)
    if isinstance(scan_options, Mapping):
        return cast(ScanOptionsDict, scan_options)
    return None


def _resolve_selected_platform_key(
    *,
    di: object | None,
    registry: "PluginRegistry | None",
) -> str | None:
    """Resolve the platform key through the same scan-options chain as DI ingress."""
    scan_options = _scan_options_from_di(di)
    if scan_options is None:
        return registry.get_default_platform_key() if registry is not None else None

    explicit = scan_options.get("scan_pipeline_plugin")
    if isinstance(explicit, str) and explicit:
        return explicit

    policy_context = scan_options.get("policy_context")
    if isinstance(policy_context, Mapping):
        selection = policy_context.get("selection")
        if isinstance(selection, Mapping):
            plugin_key = selection.get("plugin")
            if isinstance(plugin_key, str) and plugin_key:
                return plugin_key

    if registry is not None:
        default_key = registry.get_default_platform_key()
        if default_key is not None:
            return default_key

    return None


def _guard_platform_specific_non_strict_fallback(
    *,
    plugin_kind: str,
    strict_mode: bool,
    fallback_plugin: Any,
    fallback_platform_key: str | None,
    di: object | None,
    registry: "PluginRegistry | None",
) -> None:
    if strict_mode or fallback_platform_key is None:
        return

    selected_platform_key = _resolve_selected_platform_key(di=di, registry=registry)
    if selected_platform_key in (None, fallback_platform_key):
        return

    raise PrismRuntimeError(
        code="malformed_plugin_shape",
        category="runtime",
        message=(
            f"Non-strict {plugin_kind} fallback would substitute "
            f"{fallback_platform_key} defaults for platform {selected_platform_key}."
        ),
        detail={
            "plugin_kind": plugin_kind,
            "selected_platform_key": selected_platform_key,
            "fallback_platform_key": fallback_platform_key,
            "fallback_plugin_type": type(fallback_plugin).__name__,
        },
    )


# ANSIBLE-FIRST PRODUCT CONSTRAINT (intentional, not an oversight)
# The six fallback singletons below (_TASK_LINE_PARSING_FALLBACK,
# _TASK_ANNOTATION_FALLBACK, _TASK_TRAVERSAL_FALLBACK,
# _VARIABLE_EXTRACTOR_FALLBACK, _YAML_PARSING_FALLBACK,
# _JINJA_ANALYSIS_FALLBACK) are Ansible-backed by design.
#
# A platform-declared default-provider seam would allow the registry to
# surface the correct fallback class for any platform (Kubernetes, Terraform,
# etc.) without hardcoding Ansible here. That seam depends on the
# ReadmeRendererPlugin protocol design (FIND-G6-06), which has not landed yet.
# Until FIND-G6-06 is resolved, Ansible is the only supported default platform
# and these singletons intentionally reflect that constraint.
#
# Singleton fallback plugin instances — module-level globals intentionally shared.
# INVARIANT: All plugin classes below must remain stateless (no mutable instance
# state, caches, or registries). If any plugin class acquires mutable state,
# replace with per-call factory functions to prevent cross-caller contamination.
# Validation of the PLUGIN_IS_STATELESS invariant is deferred to bootstrap phase
# (scanner_plugins.bootstrap.initialize_default_registry) to avoid import-time
# failures and make bootstrap order explicit.
_TASK_LINE_PARSING_FALLBACK = AnsibleDefaultTaskLineParsingPolicyPlugin()
_TASK_ANNOTATION_FALLBACK = AnsibleDefaultTaskAnnotationPolicyPlugin()
_TASK_TRAVERSAL_FALLBACK = AnsibleDefaultTaskTraversalPolicyPlugin()
_VARIABLE_EXTRACTOR_FALLBACK = AnsibleDefaultVariableExtractorPolicyPlugin()
_YAML_PARSING_FALLBACK = DefaultYAMLParsingPolicyPlugin()
_JINJA_ANALYSIS_FALLBACK = DefaultJinjaAnalysisPolicyPlugin()

_FALLBACK_SINGLETONS = [
    _TASK_LINE_PARSING_FALLBACK,
    _TASK_ANNOTATION_FALLBACK,
    _TASK_TRAVERSAL_FALLBACK,
    _VARIABLE_EXTRACTOR_FALLBACK,
    _YAML_PARSING_FALLBACK,
    _JINJA_ANALYSIS_FALLBACK,
]

_TASK_ANNOTATION_REQUIRED_CALLABLES = (
    "split_task_annotation_label",
    "split_task_target_payload",
    "annotation_payload_looks_yaml",
    "normalize_marker_prefix",
    "get_marker_line_re",
    "extract_task_annotations_for_file",
    "task_anchor",
)

# Bootstrap validation tracking
_singleton_invariants_validated = False


def _validate_singleton_invariants() -> None:
    """Validate PLUGIN_IS_STATELESS invariant for module-level fallback singletons.

    Called by scanner_plugins.bootstrap.initialize_default_registry() to defer
    validation from import-time to explicit bootstrap phase. This prevents
    import-time RuntimeError when plugin classes are missing PLUGIN_IS_STATELESS.

    Raises:
        RuntimeError: If any singleton plugin class lacks PLUGIN_IS_STATELESS = True
    """
    global _singleton_invariants_validated

    if _singleton_invariants_validated:
        logger.debug("Singleton invariants already validated; skipping re-validation")
        return

    for singleton in _FALLBACK_SINGLETONS:
        if not getattr(type(singleton), "PLUGIN_IS_STATELESS", False):
            raise RuntimeError(
                f"{type(singleton).__name__} must declare PLUGIN_IS_STATELESS = True "
                "to be used as a module-level singleton fallback"
            )

    _singleton_invariants_validated = True
    logger.debug(
        "Singleton invariants validated for %d fallback plugins",
        len(_FALLBACK_SINGLETONS),
    )


def _raise_malformed_plugin_shape_error(
    *,
    plugin_kind: str,
    plugin: Any,
    required_callables: tuple[str, ...],
    required_attributes: tuple[str, ...],
) -> None:
    missing_callables = [
        name for name in required_callables if not callable(getattr(plugin, name, None))
    ]
    missing_attributes = [
        name for name in required_attributes if getattr(plugin, name, None) is None
    ]
    raise PrismRuntimeError(
        code="malformed_plugin_shape",
        category="runtime",
        message=f"Malformed {plugin_kind} plugin shape detected.",
        detail={
            "plugin_kind": plugin_kind,
            "plugin_type": type(plugin).__name__,
            "missing_callables": missing_callables,
            "missing_attributes": missing_attributes,
        },
    )


def _fallback_or_raise_malformed_plugin_shape(
    *,
    plugin_kind: str,
    plugin: Any,
    required_callables: tuple[str, ...],
    required_attributes: tuple[str, ...],
    strict_mode: bool,
    fallback_plugin: Any,
    fallback_platform_key: str | None,
    di: object | None,
    registry: "PluginRegistry | None",
) -> Any:
    if not strict_mode:
        _guard_platform_specific_non_strict_fallback(
            plugin_kind=plugin_kind,
            strict_mode=strict_mode,
            fallback_plugin=fallback_plugin,
            fallback_platform_key=fallback_platform_key,
            di=di,
            registry=registry,
        )
        logger.warning(
            "Malformed %s plugin shape detected in non-strict mode; falling back "
            "to %s",
            plugin_kind,
            type(fallback_plugin).__name__,
        )
        return fallback_plugin

    _raise_malformed_plugin_shape_error(
        plugin_kind=plugin_kind,
        plugin=plugin,
        required_callables=required_callables,
        required_attributes=required_attributes,
    )


def _fallback_or_raise_plugin_construction_error(
    *,
    plugin_kind: str,
    plugin_class: type[Any],
    strict_mode: bool,
    fallback_plugin: Any,
    fallback_platform_key: str | None,
    di: object | None,
    registry: "PluginRegistry | None",
    exc: Exception,
) -> Any:
    if not strict_mode:
        _guard_platform_specific_non_strict_fallback(
            plugin_kind=plugin_kind,
            strict_mode=strict_mode,
            fallback_plugin=fallback_plugin,
            fallback_platform_key=fallback_platform_key,
            di=di,
            registry=registry,
        )
        logger.warning(
            "Failed to construct %s plugin in non-strict mode; falling back to %s. %s",
            plugin_kind,
            type(fallback_plugin).__name__,
            exc,
        )
        return fallback_plugin

    raise PrismRuntimeError(
        code="malformed_plugin_shape",
        category="runtime",
        message=f"Failed to construct {plugin_kind} plugin.",
        detail={
            "plugin_kind": plugin_kind,
            "plugin_class": getattr(plugin_class, "__name__", "unknown"),
            "error": str(exc),
        },
    ) from exc


def _validate_plugin_shape(
    *,
    plugin: Any,
    plugin_kind: str,
    required_callables: tuple[str, ...],
    any_of_callables: tuple[str, ...],
    required_attributes: tuple[str, ...],
    strict_mode: bool,
    fallback_plugin: Any,
    fallback_platform_key: str | None,
    di: object | None,
    registry: "PluginRegistry | None",
) -> Any:
    has_required_callables = all(
        callable(getattr(plugin, name, None)) for name in required_callables
    )
    has_any_of_callables = True
    if any_of_callables:
        has_any_of_callables = any(
            callable(getattr(plugin, name, None)) for name in any_of_callables
        )
    has_required_attributes = all(
        getattr(plugin, name, None) is not None for name in required_attributes
    )

    if has_required_callables and has_any_of_callables and has_required_attributes:
        return plugin

    return _fallback_or_raise_malformed_plugin_shape(
        plugin_kind=plugin_kind,
        plugin=plugin,
        required_callables=required_callables,
        required_attributes=required_attributes,
        strict_mode=strict_mode,
        fallback_plugin=fallback_plugin,
        fallback_platform_key=fallback_platform_key,
        di=di,
        registry=registry,
    )


def _construct_registry_plugin(
    *,
    plugin_class: type[Any],
    plugin_kind: str,
    strict_mode: bool,
    fallback_plugin: Any,
    fallback_platform_key: str | None,
    di: object | None,
    registry: "PluginRegistry | None",
) -> Any:
    try:
        plugin = plugin_class()
    # Broad: plugin_class() is third-party plugin __init__ that can raise
    # arbitrary errors; treat construction failure as an integrity defect.
    except Exception as exc:
        return _fallback_or_raise_plugin_construction_error(
            plugin_kind=plugin_kind,
            plugin_class=plugin_class,
            strict_mode=strict_mode,
            fallback_plugin=fallback_plugin,
            fallback_platform_key=fallback_platform_key,
            di=di,
            registry=registry,
            exc=exc,
        )
    return plugin


def resolve_comment_driven_documentation_plugin(
    di: object | None,
    *,
    strict_mode: bool = True,
    registry: "PluginRegistry | None" = None,
) -> CommentDrivenDocumentationPlugin:
    """Resolve plugin with precedence: DI override, registry default, then fallback."""
    registry_obj = _resolve_registry(di, registry)
    if di is not None:
        plugin_factory = getattr(di, "factory_comment_driven_doc_plugin", None)
        if callable(plugin_factory):
            plugin = plugin_factory()
            if plugin is not None:
                return _validate_plugin_shape(
                    plugin=plugin,
                    plugin_kind="comment_driven_documentation",
                    required_callables=("extract_role_notes_from_comments",),
                    any_of_callables=(),
                    required_attributes=(),
                    strict_mode=strict_mode,
                    fallback_plugin=CommentDrivenDocumentationParser(),
                    fallback_platform_key=None,
                    di=di,
                    registry=registry_obj,
                )

    registry_plugin_class = registry_obj.get_comment_driven_doc_plugin("default")
    if registry_plugin_class is not None:
        plugin = _construct_registry_plugin(
            plugin_class=registry_plugin_class,
            plugin_kind="comment_driven_documentation",
            strict_mode=strict_mode,
            fallback_plugin=CommentDrivenDocumentationParser(),
            fallback_platform_key=None,
            di=di,
            registry=registry_obj,
        )
        return _validate_plugin_shape(
            plugin=plugin,
            plugin_kind="comment_driven_documentation",
            required_callables=("extract_role_notes_from_comments",),
            any_of_callables=(),
            required_attributes=(),
            strict_mode=strict_mode,
            fallback_plugin=CommentDrivenDocumentationParser(),
            fallback_platform_key=None,
            di=di,
            registry=registry_obj,
        )

    return CommentDrivenDocumentationParser()


def _resolve_plugin_with_precedence(
    *,
    di: object | None,
    di_factory_name: str,
    registry_plugin_name: str,
    plugin_kind: str,
    required_callables: tuple[str, ...],
    any_of_callables: tuple[str, ...],
    required_attributes: tuple[str, ...],
    fallback_plugin: Any,
    strict_mode: bool,
    registry: "PluginRegistry | None" = None,
    registry_getter_name: str = "get_extract_policy_plugin",
    fallback_platform_key: str | None = None,
) -> Any:
    registry_obj = _resolve_registry(di, registry)

    if di is not None:
        plugin_factory = getattr(di, di_factory_name, None)
        if callable(plugin_factory):
            plugin = plugin_factory()
            if plugin is not None:
                return _validate_plugin_shape(
                    plugin=plugin,
                    plugin_kind=plugin_kind,
                    required_callables=required_callables,
                    any_of_callables=any_of_callables,
                    required_attributes=required_attributes,
                    strict_mode=strict_mode,
                    fallback_plugin=fallback_plugin,
                    fallback_platform_key=fallback_platform_key,
                    di=di,
                    registry=registry_obj,
                )

    registry_getter = getattr(registry_obj, registry_getter_name)
    registry_plugin_class = registry_getter(registry_plugin_name)
    if registry_plugin_class is not None:
        plugin = _construct_registry_plugin(
            plugin_class=registry_plugin_class,
            plugin_kind=plugin_kind,
            strict_mode=strict_mode,
            fallback_plugin=fallback_plugin,
            fallback_platform_key=fallback_platform_key,
            di=di,
            registry=registry_obj,
        )
        return _validate_plugin_shape(
            plugin=plugin,
            plugin_kind=plugin_kind,
            required_callables=required_callables,
            any_of_callables=any_of_callables,
            required_attributes=required_attributes,
            strict_mode=strict_mode,
            fallback_plugin=fallback_plugin,
            fallback_platform_key=fallback_platform_key,
            di=di,
            registry=registry_obj,
        )

    return fallback_plugin


def resolve_task_line_parsing_policy_plugin(
    di: object | None = None,
    *,
    strict_mode: bool = True,
    registry: "PluginRegistry | None" = None,
) -> PreparedTaskLineParsingPolicy:
    return _resolve_plugin_with_precedence(
        di=di,
        di_factory_name="factory_task_line_parsing_policy_plugin",
        registry_plugin_name="task_line_parsing",
        plugin_kind="task_line_parsing_policy",
        required_callables=("detect_task_module",),
        any_of_callables=(),
        required_attributes=(
            "TASK_INCLUDE_KEYS",
            "ROLE_INCLUDE_KEYS",
            "INCLUDE_VARS_KEYS",
            "SET_FACT_KEYS",
            "TASK_BLOCK_KEYS",
        ),
        fallback_plugin=_TASK_LINE_PARSING_FALLBACK,
        strict_mode=strict_mode,
        registry=registry,
        fallback_platform_key="ansible",
    )


def resolve_task_annotation_policy_plugin(
    di: object | None = None,
    *,
    strict_mode: bool = True,
    registry: "PluginRegistry | None" = None,
) -> PreparedTaskAnnotationPolicy:
    return _resolve_plugin_with_precedence(
        di=di,
        di_factory_name="factory_task_annotation_policy_plugin",
        registry_plugin_name="task_annotation_parsing",
        plugin_kind="task_annotation_policy",
        required_callables=_TASK_ANNOTATION_REQUIRED_CALLABLES,
        any_of_callables=(),
        required_attributes=(),
        fallback_plugin=_TASK_ANNOTATION_FALLBACK,
        strict_mode=strict_mode,
        registry=registry,
        fallback_platform_key="ansible",
    )


def resolve_task_traversal_policy_plugin(
    di: object | None = None,
    *,
    strict_mode: bool = True,
    registry: "PluginRegistry | None" = None,
) -> PreparedTaskTraversalPolicy:
    return _resolve_plugin_with_precedence(
        di=di,
        di_factory_name="factory_task_traversal_policy_plugin",
        registry_plugin_name="task_traversal",
        plugin_kind="task_traversal_policy",
        required_callables=(
            "iter_task_mappings",
            "iter_task_include_targets",
            "expand_include_target_candidates",
            "iter_role_include_targets",
            "iter_dynamic_role_include_targets",
            "collect_unconstrained_dynamic_task_includes",
            "collect_unconstrained_dynamic_role_includes",
        ),
        any_of_callables=(),
        required_attributes=(),
        fallback_plugin=_TASK_TRAVERSAL_FALLBACK,
        strict_mode=strict_mode,
        registry=registry,
        fallback_platform_key="ansible",
    )


def resolve_variable_extractor_policy_plugin(
    di: object | None = None,
    *,
    strict_mode: bool = True,
    registry: "PluginRegistry | None" = None,
) -> PreparedVariableExtractorPolicy:
    return _resolve_plugin_with_precedence(
        di=di,
        di_factory_name="factory_variable_extractor_policy_plugin",
        registry_plugin_name="variable_extractor",
        plugin_kind="variable_extractor_policy",
        required_callables=("collect_include_vars_files",),
        any_of_callables=(),
        required_attributes=(),
        fallback_plugin=_VARIABLE_EXTRACTOR_FALLBACK,
        strict_mode=strict_mode,
        registry=registry,
        fallback_platform_key="ansible",
    )


def resolve_yaml_parsing_policy_plugin(
    di: object | None = None,
    *,
    strict_mode: bool = True,
    registry: "PluginRegistry | None" = None,
) -> PreparedYAMLParsingPolicy:
    return _resolve_plugin_with_precedence(
        di=di,
        di_factory_name="factory_yaml_parsing_policy_plugin",
        registry_plugin_name="yaml_parsing",
        plugin_kind="yaml_parsing_policy",
        required_callables=("load_yaml_file",),
        any_of_callables=(),
        required_attributes=(),
        fallback_plugin=_YAML_PARSING_FALLBACK,
        strict_mode=strict_mode,
        registry=registry,
        registry_getter_name="get_yaml_parsing_policy_plugin",
    )


def resolve_jinja_analysis_policy_plugin(
    di: object | None = None,
    *,
    strict_mode: bool = True,
    registry: "PluginRegistry | None" = None,
) -> PreparedJinjaAnalysisPolicy:
    return _resolve_plugin_with_precedence(
        di=di,
        di_factory_name="factory_jinja_analysis_policy_plugin",
        registry_plugin_name="jinja_analysis",
        plugin_kind="jinja_analysis_policy",
        required_callables=("collect_undeclared_jinja_variables",),
        any_of_callables=(),
        required_attributes=(),
        fallback_plugin=_JINJA_ANALYSIS_FALLBACK,
        strict_mode=strict_mode,
        registry=registry,
        registry_getter_name="get_jinja_analysis_policy_plugin",
    )


def _raise_standalone_runtime_path_error() -> NoReturn:
    raise ValueError(
        "scanner_plugins.defaults helper flows require a canonical di context"
    )


def extract_role_notes_from_comments(
    role_path: str,
    exclude_paths: list[str] | None = None,
    marker_prefix: str = "prism",
    *,
    di: object | None = None,
) -> dict[str, list[str]]:
    if di is None:
        _raise_standalone_runtime_path_error()
    plugin = resolve_comment_driven_documentation_plugin(di)
    return plugin.extract_role_notes_from_comments(
        role_path,
        exclude_paths=exclude_paths,
        marker_prefix=marker_prefix,
    )


def collect_unconstrained_dynamic_role_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, str]]:
    del role_path, exclude_paths
    _raise_standalone_runtime_path_error()


def collect_unconstrained_dynamic_task_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, str]]:
    del role_path, exclude_paths
    _raise_standalone_runtime_path_error()


def collect_molecule_scenarios(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, object]]:
    del role_path, exclude_paths
    _raise_standalone_runtime_path_error()


def resolve_blocker_fact_builder() -> BlockerFactBuilder:
    """Return the canonical blocker-fact builder using the runtime protocol."""
    from prism.scanner_plugins.audit.blocker_fact_evaluator import (
        build_scan_policy_blocker_facts,
    )

    def normalize_scan_metadata(metadata: ScanMetadata) -> dict[str, Any]:
        normalized_metadata: dict[str, Any] = {}
        for key, value in metadata.items():
            normalized_metadata[key] = value
        return normalized_metadata

    def build_blocker_facts(
        *,
        scan_options: ScanOptionsDict,
        metadata: ScanMetadata,
        di: object,
    ) -> ScanPolicyBlockerFacts:
        return build_scan_policy_blocker_facts(
            scan_options=scan_options,
            metadata=normalize_scan_metadata(metadata),
            di=di,
        )

    return build_blocker_facts


def resolve_runbook_rows() -> Callable[[Mapping[str, Any] | None], list["RunbookRow"]]:
    """Return build_runbook_rows from the canonical runbook renderer seam."""
    from prism.scanner_plugins.parsers.comment_doc.runbook_renderer import (
        build_runbook_rows,
    )

    return build_runbook_rows


def resolve_render_runbook() -> (
    Callable[[str, Mapping[str, Any] | None, str | None], str]
):
    """Return render_runbook from the canonical runbook renderer seam."""
    from prism.scanner_plugins.parsers.comment_doc.runbook_renderer import (
        render_runbook,
    )

    return render_runbook


def resolve_render_runbook_csv() -> Callable[[Mapping[str, Any] | None], str]:
    """Return render_runbook_csv from the canonical runbook renderer seam."""
    from prism.scanner_plugins.parsers.comment_doc.runbook_renderer import (
        render_runbook_csv,
    )

    return render_runbook_csv


def resolve_readme_renderer_plugin(
    platform_key: str,
    *,
    registry: "PluginRegistry | None" = None,
) -> ReadmeRendererPlugin:
    """Resolve readme renderer plugin class for the given platform key."""
    registry_obj = _resolve_registry(None, registry)
    plugin_class = registry_obj.get_readme_renderer_plugin(platform_key)
    if plugin_class is None:
        raise ValueError(
            f"No readme_renderer plugin registered for platform '{platform_key}'"
        )
    return plugin_class()


__all__ = [
    "collect_molecule_scenarios",
    "collect_unconstrained_dynamic_role_includes",
    "collect_unconstrained_dynamic_task_includes",
    "extract_role_notes_from_comments",
    "resolve_blocker_fact_builder",
    "resolve_comment_driven_documentation_plugin",
    "resolve_readme_renderer_plugin",
    "resolve_render_runbook",
    "resolve_render_runbook_csv",
    "resolve_runbook_rows",
    "resolve_task_annotation_policy_plugin",
    "resolve_jinja_analysis_policy_plugin",
    "resolve_task_line_parsing_policy_plugin",
    "resolve_task_traversal_policy_plugin",
    "resolve_variable_extractor_policy_plugin",
    "resolve_yaml_parsing_policy_plugin",
]
