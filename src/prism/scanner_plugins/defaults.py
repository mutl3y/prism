"""Default plugin fallbacks for fsrc scanner plugin ownership seams."""

from __future__ import annotations

from typing import Any

from prism.errors import PrismRuntimeError
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
from prism.scanner_plugins.parsers.yaml import YAMLParsingPolicyPlugin
from prism.scanner_plugins.parsers.jinja import JinjaAnalysisPolicyPlugin
from prism.scanner_plugins.parsers.comment_doc.role_notes_parser import (
    CommentDrivenDocumentationParser,
)
from prism.scanner_plugins.interfaces import CommentDrivenDocumentationPlugin
from prism.scanner_plugins.registry import plugin_registry


def _resolve_registry(di: object | None = None, registry: Any | None = None):
    if registry is not None:
        return registry

    if di is not None:
        di_registry = getattr(di, "plugin_registry", None)
        if di_registry is not None:
            return di_registry
    return plugin_registry


# Singleton fallback plugin instances — module-level globals intentionally shared.
# INVARIANT: All plugin classes below must remain stateless (no mutable instance
# state, caches, or registries). If any plugin class acquires mutable state,
# replace with per-call factory functions to prevent cross-caller contamination.
_TASK_LINE_PARSING_FALLBACK = DefaultTaskLineParsingPolicyPlugin()
_TASK_ANNOTATION_FALLBACK = DefaultTaskAnnotationPolicyPlugin()
_TASK_TRAVERSAL_FALLBACK = DefaultTaskTraversalPolicyPlugin()
_VARIABLE_EXTRACTOR_FALLBACK = DefaultVariableExtractorPolicyPlugin()
_YAML_PARSING_FALLBACK = YAMLParsingPolicyPlugin()
_JINJA_ANALYSIS_FALLBACK = JinjaAnalysisPolicyPlugin()


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
        return fallback_plugin
    return plugin


def resolve_comment_driven_documentation_plugin(
    di: object | None,
    *,
    strict_mode: bool = True,
    registry: Any | None = None,
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
    registry: Any | None = None,
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
    registry: Any | None = None,
) -> Any:
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
    registry: Any | None = None,
) -> Any:
    return _resolve_plugin_with_precedence(
        di=di,
        di_factory_name="factory_task_annotation_policy_plugin",
        registry_plugin_name="task_annotation_parsing",
        plugin_kind="task_annotation_policy",
        required_callables=(),
        any_of_callables=(
            "split_task_annotation_label",
            "extract_task_annotations_for_file",
        ),
        required_attributes=(),
        fallback_plugin=_TASK_ANNOTATION_FALLBACK,
        strict_mode=strict_mode,
        registry=registry,
    )


def resolve_task_traversal_policy_plugin(
    di: object | None = None,
    *,
    strict_mode: bool = True,
    registry: Any | None = None,
) -> Any:
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
    registry: Any | None = None,
) -> Any:
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
    registry: Any | None = None,
) -> Any:
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
    registry: Any | None = None,
) -> Any:
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
    from prism.scanner_data.standalone_di import make_standalone_di

    return make_standalone_di(role_path, exclude_paths)


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
    from prism.scanner_extract.task_file_traversal import (
        collect_unconstrained_dynamic_role_includes as _impl,
    )

    di = _make_standalone_di(role_path, exclude_paths)
    return _impl(role_path, exclude_paths, di=di)


def collect_unconstrained_dynamic_task_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, str]]:
    from prism.scanner_extract.task_file_traversal import (
        collect_unconstrained_dynamic_task_includes as _impl,
    )

    di = _make_standalone_di(role_path, exclude_paths)
    return _impl(role_path, exclude_paths, di=di)


def collect_molecule_scenarios(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, object]]:
    from prism.scanner_extract.task_catalog_assembly import collect_molecule_scenarios

    di = _make_standalone_di(role_path, exclude_paths)
    return collect_molecule_scenarios(role_path, exclude_paths, di=di)


__all__ = [
    "collect_molecule_scenarios",
    "collect_unconstrained_dynamic_role_includes",
    "collect_unconstrained_dynamic_task_includes",
    "extract_role_notes_from_comments",
    "resolve_comment_driven_documentation_plugin",
    "resolve_task_annotation_policy_plugin",
    "resolve_jinja_analysis_policy_plugin",
    "resolve_task_line_parsing_policy_plugin",
    "resolve_task_traversal_policy_plugin",
    "resolve_variable_extractor_policy_plugin",
    "resolve_yaml_parsing_policy_plugin",
]
