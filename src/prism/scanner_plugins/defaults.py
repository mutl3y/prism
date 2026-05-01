"""Default plugin fallbacks for fsrc scanner plugin ownership seams."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable
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
    PreparedTaskAnnotationPolicy,
    PreparedTaskLineParsingPolicy,
    PreparedTaskTraversalPolicy,
    PreparedVariableExtractorPolicy,
    PreparedYAMLParsingPolicy,
)

if TYPE_CHECKING:
    from prism.scanner_plugins.registry import PluginRegistry
    from prism.scanner_plugins.parsers.comment_doc.runbook_renderer import RunbookRow

logger = logging.getLogger(__name__)


def _resolve_registry(
    di: object | None = None, registry: "PluginRegistry | None" = None
) -> "PluginRegistry":
    """Resolve plugin registry: explicit registry > DI registry > bootstrap singleton.

    Uses scanner_plugins.bootstrap facade (O008/O010 remediation) instead of
    direct plugin_registry import to maintain explicit bootstrap phase ordering.
    """
    if registry is not None:
        return registry

    if di is not None:
        di_registry = getattr(di, "plugin_registry", None)
        if di_registry is not None:
            return di_registry

    from prism.scanner_plugins.bootstrap import get_default_plugin_registry

    return get_default_plugin_registry()


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


def _validate_plugin_shape(
    *,
    plugin: Any,
    plugin_kind: str,
    required_callables: tuple[str, ...],
    any_of_callables: tuple[str, ...],
    required_attributes: tuple[str, ...],
    strict_mode: bool,
    fallback_plugin: Any,
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

    if strict_mode:
        _raise_malformed_plugin_shape_error(
            plugin_kind=plugin_kind,
            plugin=plugin,
            required_callables=required_callables,
            required_attributes=required_attributes,
        )
    return fallback_plugin


def _construct_registry_plugin(
    *,
    plugin_class: type[Any],
    plugin_kind: str,
    strict_mode: bool,
    fallback_plugin: Any,
) -> Any:
    try:
        plugin = plugin_class()
    # Broad: plugin_class() is third-party plugin __init__ that can raise
    # arbitrary errors; raised in strict mode, falls back otherwise.
    except Exception as exc:
        if strict_mode:
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
        logger.warning(
            "Failed to construct %s plugin (class=%s); falling back to default. error=%s",
            plugin_kind,
            getattr(plugin_class, "__name__", "unknown"),
            type(exc).__name__,
        )
        return fallback_plugin
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
                )

    registry_plugin_class = registry_obj.get_comment_driven_doc_plugin("default")
    if registry_plugin_class is not None:
        plugin = _construct_registry_plugin(
            plugin_class=registry_plugin_class,
            plugin_kind="comment_driven_documentation",
            strict_mode=strict_mode,
            fallback_plugin=CommentDrivenDocumentationParser(),
        )
        return _validate_plugin_shape(
            plugin=plugin,
            plugin_kind="comment_driven_documentation",
            required_callables=("extract_role_notes_from_comments",),
            any_of_callables=(),
            required_attributes=(),
            strict_mode=strict_mode,
            fallback_plugin=CommentDrivenDocumentationParser(),
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
                )

    registry_getter = getattr(registry_obj, registry_getter_name)
    registry_plugin_class = registry_getter(registry_plugin_name)
    if registry_plugin_class is not None:
        plugin = _construct_registry_plugin(
            plugin_class=registry_plugin_class,
            plugin_kind=plugin_kind,
            strict_mode=strict_mode,
            fallback_plugin=fallback_plugin,
        )
        return _validate_plugin_shape(
            plugin=plugin,
            plugin_kind=plugin_kind,
            required_callables=required_callables,
            any_of_callables=any_of_callables,
            required_attributes=required_attributes,
            strict_mode=strict_mode,
            fallback_plugin=fallback_plugin,
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


def _make_standalone_di(role_path: str, exclude_paths=None):
    import types

    from prism.scanner_plugins.bundle_resolver import ensure_prepared_policy_bundle

    options: dict = {
        "role_path": role_path,
        "exclude_path_patterns": exclude_paths,
    }
    ensure_prepared_policy_bundle(scan_options=options, di=None)
    di = types.SimpleNamespace()
    di.scan_options = options
    di.plugin_registry = None
    return di


def extract_role_notes_from_comments(
    role_path: str,
    exclude_paths: list[str] | None = None,
    marker_prefix: str = "prism",
    *,
    di: object | None = None,
) -> dict[str, list[str]]:
    standalone = _make_standalone_di(role_path, exclude_paths) if di is None else di
    plugin = resolve_comment_driven_documentation_plugin(standalone)
    return plugin.extract_role_notes_from_comments(
        role_path,
        exclude_paths=exclude_paths,
        marker_prefix=marker_prefix,
    )


def collect_unconstrained_dynamic_role_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, str]]:
    from prism.scanner_plugins.ansible.extract_utils import (
        collect_unconstrained_dynamic_role_includes as _impl,
    )

    di = _make_standalone_di(role_path, exclude_paths)
    return _impl(role_path, exclude_paths, di=di)


def collect_unconstrained_dynamic_task_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, str]]:
    from prism.scanner_plugins.ansible.extract_utils import (
        collect_unconstrained_dynamic_task_includes as _impl,
    )

    di = _make_standalone_di(role_path, exclude_paths)
    return _impl(role_path, exclude_paths, di=di)


def collect_molecule_scenarios(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, object]]:
    from prism.scanner_plugins.ansible.extract_utils import (
        collect_molecule_scenarios,
    )

    di = _make_standalone_di(role_path, exclude_paths)
    return collect_molecule_scenarios(role_path, exclude_paths, di=di)


def resolve_blocker_fact_builder() -> Callable[..., Any]:
    """Return the canonical blocker-fact builder callable from the audit module.

    Returns a callable matching BlockerFactBuilder Protocol shape, but typed
    as Callable[..., Any] to avoid triggering structural type mismatch between
    the concrete function signature (metadata: dict[str, Any]) and the Protocol
    expectation (metadata: ScanMetadata).
    """
    from prism.scanner_plugins.audit.blocker_fact_evaluator import (
        build_scan_policy_blocker_facts,
    )

    return build_scan_policy_blocker_facts


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
