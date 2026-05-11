"""Minimal scan-request option normalization for fsrc scanner context."""

from __future__ import annotations

import copy
import logging
from typing import TypeGuard

from prism.scanner_data.contracts_request import (
    PreparedPolicyBundle,
    ScanOptionsDict,
    ScanPolicyContext,
    ScanPolicyWarning,
)
from prism.scanner_data.scan_options_schema import validate_scan_options
from prism.errors import PrismRuntimeError

logger = logging.getLogger(__name__)


def _is_scan_policy_context(value: object) -> TypeGuard[ScanPolicyContext]:
    return isinstance(value, dict)


def _copy_scan_policy_context(policy_context: ScanPolicyContext) -> ScanPolicyContext:
    """Deep copy ScanPolicyContext to prevent cross-request mutations of nested structures."""
    return copy.deepcopy(policy_context)  # type: ignore[return-value]


def _strict_bool_or_none(value: bool | None, field_name: str) -> bool | None:
    """Validate that value is exactly bool or None, reject truthy coercion.

    Args:
        value: Value to validate
        field_name: Field name for error messages

    Returns:
        The value if it's bool or None

    Raises:
        PrismRuntimeError: If value is not bool or None
    """
    if value is None or isinstance(value, bool):
        return value
    raise PrismRuntimeError(
        code="scan_options_validation_boolean_type",
        category="validation",
        message=f"'{field_name}' must be bool or None, got {type(value).__name__}.",
        detail={
            "field": field_name,
            "actual_type": type(value).__name__,
            "hint": "Truthy coercion like bool('false') is not allowed. Use actual bool type.",
        },
    )


def _normalize_policy_context(
    policy_context: ScanPolicyContext | None,
) -> tuple[ScanPolicyContext | None, list[ScanPolicyWarning]]:
    """Normalize policy context, with explicit error diagnostics.

    Args:
        policy_context: Raw policy context dict or None

    Returns:
        Tuple of (normalized_context, warnings). If policy_context is not
        a dict, returns (None, [warning]). If policy_context is provided but not
        a valid dict, logs a diagnostic warning before returning None.

    Raises:
        No exception is raised to maintain backward compatibility, but a
        ScanPolicyWarning is recorded for strict-mode validation.
    """
    if policy_context is None:
        return None, []

    if not _is_scan_policy_context(policy_context):
        warning_msg = (
            f"policy_context was provided but is not a dict; ignoring. "
            f"Expected dict, got {type(policy_context).__name__}. "
            f"This usually indicates a caller error and may cause incorrect scan behavior."
        )
        logger.warning(warning_msg)
        return None, [
            ScanPolicyWarning(code="policy_context_type_mismatch", message=warning_msg)
        ]

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
    """Return canonical option map for scanner-context execution.

    Args:
        role_path: Path to the Ansible role
        policy_context: Optional scan policy context (dict). If provided but not
            a valid dict, a warning is logged and None is used.
        prepared_policy_bundle: Optional prepared policy bundle
        ... (other args as before) ...

    Returns:
        ScanOptionsDict with all options normalized and validated

    Raises:
        ValueError: If role_path is empty or invalid, or if validation fails
    """
    if not isinstance(role_path, str) or not role_path.strip():
        raise ValueError("'role_path' must be a non-empty string")

    normalized_policy_context, policy_warnings = _normalize_policy_context(
        policy_context
    )

    # Validate boolean fields: require actual bool type, reject truthy coercion
    # Lists are deep-copied to prevent cross-request mutable state leakage
    options: ScanOptionsDict = {
        "role_path": role_path,
        "role_name_override": role_name_override,
        "readme_config_path": readme_config_path,
        "policy_config_path": policy_config_path,
        "include_vars_main": bool(include_vars_main),
        "exclude_path_patterns": (
            copy.deepcopy(exclude_path_patterns)
            if exclude_path_patterns is not None
            else None
        ),
        "detailed_catalog": bool(detailed_catalog),
        "include_task_parameters": bool(include_task_parameters),
        "include_task_runbooks": bool(include_task_runbooks),
        "inline_task_runbooks": bool(inline_task_runbooks),
        "include_collection_checks": bool(include_collection_checks),
        "keep_unknown_style_sections": bool(keep_unknown_style_sections),
        "adopt_heading_mode": adopt_heading_mode,
        "vars_seed_paths": (
            copy.deepcopy(vars_seed_paths) if vars_seed_paths is not None else None
        ),
        "style_readme_path": style_readme_path,
        "style_source_path": style_source_path,
        "style_guide_skeleton": bool(style_guide_skeleton),
        "compare_role_path": compare_role_path,
        "fail_on_unconstrained_dynamic_includes": _strict_bool_or_none(
            fail_on_unconstrained_dynamic_includes,
            "fail_on_unconstrained_dynamic_includes",
        ),
        "fail_on_yaml_like_task_annotations": _strict_bool_or_none(
            fail_on_yaml_like_task_annotations, "fail_on_yaml_like_task_annotations"
        ),
        "ignore_unresolved_internal_underscore_references": _strict_bool_or_none(
            ignore_unresolved_internal_underscore_references,
            "ignore_unresolved_internal_underscore_references",
        ),
        "policy_context": normalized_policy_context,
    }

    # Validate and deep-copy prepared_policy_bundle
    if prepared_policy_bundle is not None:
        if not isinstance(prepared_policy_bundle, dict):
            raise PrismRuntimeError(
                code="scan_options_validation_prepared_policy_type",
                category="validation",
                message=f"'prepared_policy_bundle' must be dict or None, got {type(prepared_policy_bundle).__name__}.",
                detail={
                    "actual_type": type(prepared_policy_bundle).__name__,
                    "hint": "Invalid policy bundles are not silently dropped.",
                },
            )
        options["prepared_policy_bundle"] = copy.deepcopy(prepared_policy_bundle)

    if policy_warnings:
        options["scan_policy_warnings"] = list(policy_warnings)

    try:
        validate_scan_options(options)
    except (ValueError, TypeError) as exc:
        logger.error(
            "Validation failed for scan options: %s. role_path=%r, policy_context=%r",
            exc,
            role_path,
            normalized_policy_context,
            exc_info=True,
        )
        raise

    return options
