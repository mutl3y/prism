"""Bundle resolver: assembles PreparedPolicyBundle by resolving plugin defaults."""

from __future__ import annotations

from typing import Any, cast

from prism.scanner_data.contracts_request import PreparedPolicyBundle
from prism.scanner_plugins.defaults import resolve_jinja_analysis_policy_plugin
from prism.scanner_plugins.defaults import resolve_task_annotation_policy_plugin
from prism.scanner_plugins.defaults import resolve_task_line_parsing_policy_plugin
from prism.scanner_plugins.defaults import resolve_task_traversal_policy_plugin
from prism.scanner_plugins.defaults import resolve_variable_extractor_policy_plugin
from prism.scanner_plugins.defaults import resolve_yaml_parsing_policy_plugin
from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
    DEFAULT_DOC_MARKER_PREFIX,
    normalize_marker_prefix,
)


_TASK_LINE_REQUIRED_ATTRIBUTES = (
    "TASK_INCLUDE_KEYS",
    "ROLE_INCLUDE_KEYS",
    "INCLUDE_VARS_KEYS",
    "SET_FACT_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_META_KEYS",
)


def _validate_task_line_policy(plugin: object) -> None:
    if not callable(getattr(plugin, "detect_task_module", None)):
        raise ValueError(
            "prepared_policy_bundle.task_line_parsing must provide detect_task_module"
        )

    missing_attributes = [
        name
        for name in _TASK_LINE_REQUIRED_ATTRIBUTES
        if getattr(plugin, name, None) is None
    ]
    if missing_attributes:
        raise ValueError(
            "prepared_policy_bundle.task_line_parsing is missing required attributes: "
            + ", ".join(missing_attributes)
        )


def _validate_jinja_analysis_policy(plugin: object) -> None:
    if not callable(getattr(plugin, "collect_undeclared_jinja_variables", None)):
        raise ValueError(
            "prepared_policy_bundle.jinja_analysis must provide collect_undeclared_jinja_variables"
        )


def _validate_prepared_policy_bundle(bundle: dict[str, Any]) -> None:
    task_line_policy = bundle.get("task_line_parsing")
    if task_line_policy is not None:
        _validate_task_line_policy(task_line_policy)

    jinja_analysis_policy = bundle.get("jinja_analysis")
    if jinja_analysis_policy is not None:
        _validate_jinja_analysis_policy(jinja_analysis_policy)


def _resolve_underscore_reference_preference(
    scan_options: dict[str, Any],
    bundle: dict[str, Any],
) -> None:
    """Resolve ignore_unresolved_internal_underscore_references from explicit arg + policy_context."""
    explicit = scan_options.get("ignore_unresolved_internal_underscore_references")
    if isinstance(explicit, bool):
        bundle["ignore_unresolved_internal_underscore_references"] = explicit
        scan_options["ignore_unresolved_internal_underscore_references"] = explicit
        return

    policy_context = scan_options.get("policy_context")
    if isinstance(policy_context, dict):
        include_underscore = policy_context.get(
            "include_underscore_prefixed_references"
        )
        if isinstance(include_underscore, bool):
            resolved = not include_underscore
            bundle["ignore_unresolved_internal_underscore_references"] = resolved
            scan_options["ignore_unresolved_internal_underscore_references"] = resolved
            return

    bundle["ignore_unresolved_internal_underscore_references"] = None


def ensure_prepared_policy_bundle(
    *,
    scan_options: dict[str, Any],
    di: object | None,
) -> PreparedPolicyBundle:
    existing_bundle = scan_options.get("prepared_policy_bundle")
    if existing_bundle is not None and not isinstance(existing_bundle, dict):
        raise ValueError("prepared_policy_bundle must be a dict when provided")

    bundle: dict[str, Any] = (
        dict(existing_bundle) if isinstance(existing_bundle, dict) else {}
    )
    strict_mode = bool(scan_options.get("strict_phase_failures", True))

    if bundle.get("task_line_parsing") is None:
        bundle["task_line_parsing"] = resolve_task_line_parsing_policy_plugin(
            di,
            strict_mode=strict_mode,
        )
    if bundle.get("task_annotation_parsing") is None:
        bundle["task_annotation_parsing"] = resolve_task_annotation_policy_plugin(
            di,
            strict_mode=strict_mode,
        )
    if bundle.get("task_traversal") is None:
        bundle["task_traversal"] = resolve_task_traversal_policy_plugin(
            di,
            strict_mode=strict_mode,
        )
    if bundle.get("yaml_parsing") is None:
        bundle["yaml_parsing"] = resolve_yaml_parsing_policy_plugin(
            di,
            strict_mode=strict_mode,
        )
    if bundle.get("jinja_analysis") is None:
        bundle["jinja_analysis"] = resolve_jinja_analysis_policy_plugin(
            di,
            strict_mode=strict_mode,
        )
    if bundle.get("variable_extractor") is None:
        bundle["variable_extractor"] = resolve_variable_extractor_policy_plugin(
            di,
            strict_mode=strict_mode,
        )

    if bundle.get("comment_doc_marker_prefix") is None:
        raw_prefix = scan_options.get("comment_doc_marker_prefix")
        if not isinstance(raw_prefix, str):
            policy_context = scan_options.get("policy_context")
            if isinstance(policy_context, dict):
                cd = policy_context.get("comment_doc")
                if isinstance(cd, dict):
                    mk = cd.get("marker")
                    if isinstance(mk, dict):
                        p = mk.get("prefix")
                        if isinstance(p, str):
                            raw_prefix = p
        if isinstance(raw_prefix, str):
            bundle["comment_doc_marker_prefix"] = normalize_marker_prefix(raw_prefix)
        else:
            bundle["comment_doc_marker_prefix"] = DEFAULT_DOC_MARKER_PREFIX

    _resolve_underscore_reference_preference(scan_options, bundle)

    _validate_prepared_policy_bundle(bundle)

    scan_options["prepared_policy_bundle"] = bundle
    return cast(PreparedPolicyBundle, bundle)
