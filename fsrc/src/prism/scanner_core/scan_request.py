"""Minimal scan-request option normalization for fsrc scanner context."""

from __future__ import annotations

from typing import Any, cast

from prism.scanner_data.contracts_request import PreparedPolicyBundle
from prism.scanner_data.contracts_request import ScanOptionsDict
from prism.scanner_plugins.defaults import resolve_jinja_analysis_policy_plugin
from prism.scanner_plugins.defaults import resolve_task_annotation_policy_plugin
from prism.scanner_plugins.defaults import resolve_task_line_parsing_policy_plugin
from prism.scanner_plugins.defaults import resolve_task_traversal_policy_plugin
from prism.scanner_plugins.defaults import resolve_variable_extractor_policy_plugin
from prism.scanner_plugins.defaults import resolve_yaml_parsing_policy_plugin


_TASK_LINE_REQUIRED_ATTRIBUTES = (
    "TASK_INCLUDE_KEYS",
    "ROLE_INCLUDE_KEYS",
    "INCLUDE_VARS_KEYS",
    "SET_FACT_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_META_KEYS",
)


def _normalize_marker_policy_context(
    normalized: dict[str, object],
) -> list[dict[str, object]]:
    comment_doc = normalized.get("comment_doc")
    if not isinstance(comment_doc, dict):
        return []

    comment_doc_context = dict(comment_doc)
    marker_context = comment_doc_context.get("marker")
    if isinstance(marker_context, dict):
        comment_doc_context["marker"] = dict(marker_context)

    normalized["comment_doc"] = comment_doc_context
    return []


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


def _normalize_policy_context(
    policy_context: dict[str, object] | None,
) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    if not isinstance(policy_context, dict):
        return None, []

    normalized: dict[str, object] = dict(policy_context)
    warnings = _normalize_marker_policy_context(normalized)

    return normalized, warnings


def _project_canonical_marker_prefix(
    policy_context: dict[str, object] | None,
) -> str | None:
    if not isinstance(policy_context, dict):
        return None

    comment_doc_context = policy_context.get("comment_doc")
    if not isinstance(comment_doc_context, dict):
        return None

    marker_context = comment_doc_context.get("marker")
    if not isinstance(marker_context, dict):
        return None

    prefix = marker_context.get("prefix")
    if not isinstance(prefix, str):
        return None

    return prefix


def _resolve_canonical_ignore_underscore_references(
    *,
    ignore_unresolved_internal_underscore_references: bool | None,
    policy_context: dict[str, object] | None,
) -> bool | None:
    if isinstance(ignore_unresolved_internal_underscore_references, bool):
        return ignore_unresolved_internal_underscore_references

    if not isinstance(policy_context, dict):
        return None

    include_underscore_prefixed_references = policy_context.get(
        "include_underscore_prefixed_references"
    )
    if isinstance(include_underscore_prefixed_references, bool):
        return not include_underscore_prefixed_references

    return None


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
        marker_prefix = scan_options.get("comment_doc_marker_prefix")
        if isinstance(marker_prefix, str):
            bundle["comment_doc_marker_prefix"] = marker_prefix
        else:
            from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
                DEFAULT_DOC_MARKER_PREFIX,
            )

            bundle["comment_doc_marker_prefix"] = DEFAULT_DOC_MARKER_PREFIX

    _validate_prepared_policy_bundle(bundle)

    scan_options["prepared_policy_bundle"] = bundle
    return cast(PreparedPolicyBundle, bundle)


def build_run_scan_options_canonical(
    *,
    role_path: str,
    role_name_override: str | None,
    readme_config_path: str | None,
    policy_config_path: str | None = None,
    include_vars_main: bool,
    exclude_path_patterns: list[str] | None,
    detailed_catalog: bool,
    include_task_parameters: bool,
    include_task_runbooks: bool,
    inline_task_runbooks: bool,
    include_collection_checks: bool,
    keep_unknown_style_sections: bool,
    adopt_heading_mode: str | None,
    vars_seed_paths: list[str] | None,
    style_readme_path: str | None,
    style_source_path: str | None,
    style_guide_skeleton: bool,
    compare_role_path: str | None,
    fail_on_unconstrained_dynamic_includes: bool | None,
    fail_on_yaml_like_task_annotations: bool | None,
    ignore_unresolved_internal_underscore_references: bool | None,
    policy_context: dict[str, object] | None = None,
    prepared_policy_bundle: PreparedPolicyBundle | dict[str, Any] | None = None,
) -> ScanOptionsDict:
    """Return canonical option map for scanner-context execution."""
    if not isinstance(role_path, str) or not role_path.strip():
        raise ValueError("'role_path' must be a non-empty string")

    normalized_policy_context, policy_warnings = _normalize_policy_context(
        policy_context
    )
    canonical_ignore_underscore_references = (
        _resolve_canonical_ignore_underscore_references(
            ignore_unresolved_internal_underscore_references=(
                ignore_unresolved_internal_underscore_references
            ),
            policy_context=normalized_policy_context,
        )
    )
    canonical_marker_prefix = _project_canonical_marker_prefix(
        normalized_policy_context
    )

    options: ScanOptionsDict = {
        "role_path": role_path,
        "role_name_override": role_name_override,
        "readme_config_path": readme_config_path,
        "policy_config_path": policy_config_path,
        "include_vars_main": bool(include_vars_main),
        "exclude_path_patterns": exclude_path_patterns,
        "detailed_catalog": bool(detailed_catalog),
        "include_task_parameters": bool(include_task_parameters),
        "include_task_runbooks": bool(include_task_runbooks),
        "inline_task_runbooks": bool(inline_task_runbooks),
        "include_collection_checks": bool(include_collection_checks),
        "keep_unknown_style_sections": bool(keep_unknown_style_sections),
        "adopt_heading_mode": adopt_heading_mode,
        "vars_seed_paths": vars_seed_paths,
        "style_readme_path": style_readme_path,
        "style_source_path": style_source_path,
        "style_guide_skeleton": bool(style_guide_skeleton),
        "compare_role_path": compare_role_path,
        "fail_on_unconstrained_dynamic_includes": fail_on_unconstrained_dynamic_includes,
        "fail_on_yaml_like_task_annotations": fail_on_yaml_like_task_annotations,
        "ignore_unresolved_internal_underscore_references": canonical_ignore_underscore_references,
        "policy_context": normalized_policy_context,
    }

    if isinstance(canonical_marker_prefix, str):
        options["comment_doc_marker_prefix"] = canonical_marker_prefix

    if isinstance(prepared_policy_bundle, dict):
        options["prepared_policy_bundle"] = dict(prepared_policy_bundle)

    if policy_warnings:
        options["scan_policy_warnings"] = list(policy_warnings)

    return options
