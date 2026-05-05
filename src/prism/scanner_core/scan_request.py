"""Minimal scan-request option normalization for fsrc scanner context."""

from __future__ import annotations

import copy
from typing import TypeGuard

from prism.scanner_data.contracts_request import (
    PreparedPolicyBundle,
    ScanOptionsDict,
    ScanPolicyContext,
    ScanPolicyWarning,
)
from prism.scanner_data.scan_options_schema import validate_scan_options


def _is_scan_policy_context(value: object) -> TypeGuard[ScanPolicyContext]:
    return isinstance(value, dict)


def _copy_scan_policy_context(policy_context: ScanPolicyContext) -> ScanPolicyContext:
    """Preserve the ScanPolicyContext TypedDict contract across shallow copies."""
    return ScanPolicyContext(**policy_context)


def _normalize_policy_context(
    policy_context: ScanPolicyContext | None,
) -> tuple[ScanPolicyContext | None, list[ScanPolicyWarning]]:
    if not _is_scan_policy_context(policy_context):
        return None, []
    return _copy_scan_policy_context(policy_context), []


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
    policy_context: ScanPolicyContext | None = None,
    prepared_policy_bundle: PreparedPolicyBundle | None = None,
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
        options["prepared_policy_bundle"] = copy.copy(prepared_policy_bundle)

    if policy_warnings:
        options["scan_policy_warnings"] = list(policy_warnings)

    validate_scan_options(options)
    return options
