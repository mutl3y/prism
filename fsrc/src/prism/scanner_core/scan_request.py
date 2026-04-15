"""Minimal scan-request option normalization for fsrc scanner context."""

from __future__ import annotations

from typing import Any

from prism.scanner_data.contracts_request import PreparedPolicyBundle
from prism.scanner_data.contracts_request import ScanOptionsDict
from prism.scanner_plugins.defaults import resolve_jinja_analysis_policy_plugin
from prism.scanner_plugins.defaults import resolve_task_line_parsing_policy_plugin


_DEPRECATED_MARKER_ALIAS_CODE = "deprecated_policy_context_alias"


def _build_marker_alias_warning(alias_key: str) -> dict[str, object]:
    return {
        "code": _DEPRECATED_MARKER_ALIAS_CODE,
        "message": "Deprecated marker-prefix policy alias used.",
        "detail": {"alias_key": alias_key},
    }


def _normalize_policy_context(
    policy_context: dict[str, object] | None,
) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    if not isinstance(policy_context, dict):
        return None, []

    normalized: dict[str, object] = dict(policy_context)
    warnings: list[dict[str, object]] = []

    selected_prefix: str | None = None
    comment_doc = normalized.get("comment_doc")
    if isinstance(comment_doc, dict):
        comment_doc_context = dict(comment_doc)
        normalized["comment_doc"] = comment_doc_context

        marker_context = comment_doc_context.get("marker")
        if isinstance(marker_context, dict):
            marker_mapping = dict(marker_context)
            comment_doc_context["marker"] = marker_mapping
            canonical_prefix = marker_mapping.get("prefix")
            if isinstance(canonical_prefix, str):
                selected_prefix = canonical_prefix

        if selected_prefix is None:
            nested_alias_prefix = comment_doc_context.get("marker_prefix")
            if isinstance(nested_alias_prefix, str):
                selected_prefix = nested_alias_prefix
                warnings.append(
                    _build_marker_alias_warning(
                        "policy_context.comment_doc.marker_prefix"
                    )
                )

        if selected_prefix is None:
            marker_alias_value = comment_doc_context.get("marker")
            if isinstance(marker_alias_value, str):
                selected_prefix = marker_alias_value
                warnings.append(
                    _build_marker_alias_warning("policy_context.comment_doc.marker")
                )

    if selected_prefix is None:
        flat_alias_prefix = normalized.get("comment_doc_marker_prefix")
        if isinstance(flat_alias_prefix, str):
            selected_prefix = flat_alias_prefix
            warnings.append(
                _build_marker_alias_warning("policy_context.comment_doc_marker_prefix")
            )

    if isinstance(selected_prefix, str):
        comment_doc_context = normalized.get("comment_doc")
        if not isinstance(comment_doc_context, dict):
            comment_doc_context = {}
            normalized["comment_doc"] = comment_doc_context

        marker_context = comment_doc_context.get("marker")
        if not isinstance(marker_context, dict):
            marker_context = {}
            comment_doc_context["marker"] = marker_context
        marker_context["prefix"] = selected_prefix

    return normalized, warnings


def ensure_prepared_policy_bundle(
    *,
    scan_options: dict[str, Any],
    di: object | None,
) -> PreparedPolicyBundle:
    existing_bundle = scan_options.get("prepared_policy_bundle")
    bundle: dict[str, Any] = (
        dict(existing_bundle) if isinstance(existing_bundle, dict) else {}
    )

    if bundle.get("task_line_parsing") is None:
        bundle["task_line_parsing"] = resolve_task_line_parsing_policy_plugin(di)
    if bundle.get("jinja_analysis") is None:
        bundle["jinja_analysis"] = resolve_jinja_analysis_policy_plugin(di)

    scan_options["prepared_policy_bundle"] = bundle
    return bundle


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
        "ignore_unresolved_internal_underscore_references": ignore_unresolved_internal_underscore_references,
        "policy_context": normalized_policy_context,
    }

    if isinstance(prepared_policy_bundle, dict):
        options["prepared_policy_bundle"] = dict(prepared_policy_bundle)

    if policy_warnings:
        options["scan_policy_warnings"] = list(policy_warnings)

    return options
