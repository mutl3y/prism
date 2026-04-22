"""Package-owned non-collection implementation for the fsrc public API facade."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, cast

from prism.errors import FailurePolicy, PrismRuntimeError
from prism.scanner_data.payload_helpers import normalize_scan_role_payload_shape
from prism.scanner_core.di import DIContainer
from prism.scanner_core.feature_detector import FeatureDetector
from prism.scanner_core.scan_request import build_run_scan_options_canonical
from prism.scanner_core.scanner_context import (
    ScannerContext,
    build_non_collection_run_scan_execution_request,
)
from prism.scanner_core.variable_discovery import VariableDiscovery
from prism.scanner_data import RepoScanResult, RoleScanResult
from prism.scanner_kernel.orchestrator import (
    RoutePreflightRuntimeCarrier,
    orchestrate_scan_payload_with_selected_plugin,
    route_scan_payload_orchestration,
)
from prism.scanner_plugins import DEFAULT_PLUGIN_REGISTRY
from prism.scanner_plugins.bundle_resolver import ensure_prepared_policy_bundle
from prism.scanner_plugins.defaults import resolve_comment_driven_documentation_plugin

_repo_scan_facade: Any | None = None


def _resolve_repo_scan_facade() -> Any:
    global _repo_scan_facade
    if _repo_scan_facade is None:
        _repo_scan_facade = importlib.import_module(
            "prism.repo_services"
        ).repo_scan_facade
    return _repo_scan_facade


def _validate_role_path(role_path: str) -> str:
    normalized_role_path = role_path.strip() if isinstance(role_path, str) else ""
    if not normalized_role_path:
        raise PrismRuntimeError(
            code="role_path_invalid",
            category="validation",
            message="role_path must be a non-empty string.",
            detail={"field": "role_path"},
        )

    role_root = Path(normalized_role_path)
    if not role_root.exists():
        raise PrismRuntimeError(
            code="role_path_not_found",
            category="validation",
            message=f"role_path does not exist: {normalized_role_path}",
            detail={"role_path": normalized_role_path},
        )
    if not role_root.is_dir():
        raise PrismRuntimeError(
            code="role_path_not_directory",
            category="validation",
            message=f"role_path must be a directory: {normalized_role_path}",
            detail={"role_path": normalized_role_path},
        )
    return normalized_role_path


def _extract_role_description(role_root: Path, role_name: str) -> str:
    readme_path = role_root / "README.md"
    if readme_path.is_file():
        try:
            readme_text = readme_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            readme_text = ""
        for line in readme_text.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped
    return f"Auto-generated scan summary for {role_name}."


def run_scan(
    role_path: str,
    *,
    role_name_override: str | None = None,
    readme_config_path: str | None = None,
    policy_config_path: str | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    exclude_path_patterns: list[str] | None = None,
    detailed_catalog: bool = False,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    include_collection_checks: bool = True,
    keep_unknown_style_sections: bool = True,
    adopt_heading_mode: str | None = None,
    vars_seed_paths: list[str] | None = None,
    style_readme_path: str | None = None,
    style_source_path: str | None = None,
    style_guide_skeleton: bool = False,
    compare_role_path: str | None = None,
    fail_on_unconstrained_dynamic_includes: bool | None = None,
    fail_on_yaml_like_task_annotations: bool | None = None,
    ignore_unresolved_internal_underscore_references: bool | None = None,
    policy_context: dict[str, object] | None = None,
    strict_phase_failures: bool = True,
    scan_pipeline_plugin: str | None = None,
    validate_role_path_fn=_validate_role_path,
    extract_role_description_fn=_extract_role_description,
    build_run_scan_options_canonical_fn=build_run_scan_options_canonical,
    route_scan_payload_orchestration_fn=route_scan_payload_orchestration,
    orchestrate_scan_payload_with_selected_plugin_fn=(
        orchestrate_scan_payload_with_selected_plugin
    ),
    di_container_cls=DIContainer,
    feature_detector_cls=FeatureDetector,
    scanner_context_cls=ScannerContext,
    variable_discovery_cls=VariableDiscovery,
    resolve_comment_driven_documentation_plugin_fn=(
        resolve_comment_driven_documentation_plugin
    ),
    default_plugin_registry=DEFAULT_PLUGIN_REGISTRY,
) -> dict[str, object]:
    """Run the non-collection scanner orchestration and return a payload."""
    execution_request = build_non_collection_run_scan_execution_request(
        role_path=role_path,
        role_name_override=role_name_override,
        readme_config_path=readme_config_path,
        policy_config_path=policy_config_path,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_vars_main=include_vars_main,
        include_scanner_report_link=include_scanner_report_link,
        exclude_path_patterns=exclude_path_patterns,
        detailed_catalog=detailed_catalog,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        include_collection_checks=include_collection_checks,
        keep_unknown_style_sections=keep_unknown_style_sections,
        adopt_heading_mode=adopt_heading_mode,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        style_guide_skeleton=style_guide_skeleton,
        compare_role_path=compare_role_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        policy_context=policy_context,
        strict_phase_failures=strict_phase_failures,
        scan_pipeline_plugin=scan_pipeline_plugin,
        validate_role_path_fn=validate_role_path_fn,
        extract_role_description_fn=extract_role_description_fn,
        build_run_scan_options_canonical_fn=build_run_scan_options_canonical_fn,
        di_container_cls=di_container_cls,
        feature_detector_cls=feature_detector_cls,
        scanner_context_cls=scanner_context_cls,
        variable_discovery_cls=variable_discovery_cls,
        resolve_comment_driven_documentation_plugin_fn=(
            resolve_comment_driven_documentation_plugin_fn
        ),
        default_plugin_registry=default_plugin_registry,
        ensure_prepared_policy_bundle_fn=ensure_prepared_policy_bundle,
    )

    def _kernel_orchestrator(
        *,
        role_path: str,
        scan_options: dict[str, Any],
        route_preflight_runtime: RoutePreflightRuntimeCarrier | None = None,
    ) -> dict[str, Any]:
        del role_path
        return orchestrate_scan_payload_with_selected_plugin_fn(
            build_payload_fn=execution_request.build_payload_fn,
            scan_options=dict(execution_request.scan_options, **scan_options),
            strict_mode=execution_request.strict_mode,
            route_preflight_runtime=route_preflight_runtime,
            registry=execution_request.runtime_registry,
        )

    return route_scan_payload_orchestration_fn(
        role_path=execution_request.role_path,
        scan_options=execution_request.scan_options,
        kernel_orchestrator_fn=_kernel_orchestrator,
        registry=execution_request.runtime_registry,
    )


def scan_role(
    role_path: str,
    *,
    compare_role_path: str | None = None,
    style_readme_path: str | None = None,
    role_name_override: str | None = None,
    vars_seed_paths: list[str] | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    readme_config_path: str | None = None,
    adopt_heading_mode: str | None = None,
    style_guide_skeleton: bool = False,
    keep_unknown_style_sections: bool = True,
    exclude_path_patterns: list[str] | None = None,
    style_source_path: str | None = None,
    policy_config_path: str | None = None,
    fail_on_unconstrained_dynamic_includes: bool | None = None,
    fail_on_yaml_like_task_annotations: bool | None = None,
    ignore_unresolved_internal_underscore_references: bool | None = None,
    detailed_catalog: bool = False,
    include_collection_checks: bool = False,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    failure_policy: FailurePolicy | None = None,
    run_scan_fn=run_scan,
) -> RoleScanResult:
    """Package-owned role scan seam for the fsrc public facade."""
    strict_phase_failures = True
    if failure_policy is not None:
        strict_phase_failures = bool(failure_policy.strict)

    result = run_scan_fn(
        role_path,
        role_name_override=role_name_override,
        readme_config_path=readme_config_path,
        policy_config_path=policy_config_path,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_vars_main=include_vars_main,
        include_scanner_report_link=include_scanner_report_link,
        exclude_path_patterns=exclude_path_patterns,
        detailed_catalog=detailed_catalog,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        include_collection_checks=include_collection_checks,
        keep_unknown_style_sections=keep_unknown_style_sections,
        adopt_heading_mode=adopt_heading_mode,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        style_guide_skeleton=style_guide_skeleton,
        compare_role_path=compare_role_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        strict_phase_failures=strict_phase_failures,
    )
    return cast(RoleScanResult, normalize_scan_role_payload_shape(result))


def scan_repo(
    repo_url: str,
    *,
    repo_ref: str | None = None,
    repo_role_path: str = ".",
    repo_timeout: int = 60,
    repo_style_readme_path: str | None = None,
    compare_role_path: str | None = None,
    style_readme_path: str | None = None,
    vars_seed_paths: list[str] | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    readme_config_path: str | None = None,
    adopt_heading_mode: str | None = None,
    style_guide_skeleton: bool = False,
    keep_unknown_style_sections: bool = True,
    exclude_path_patterns: list[str] | None = None,
    style_source_path: str | None = None,
    policy_config_path: str | None = None,
    fail_on_unconstrained_dynamic_includes: bool | None = None,
    fail_on_yaml_like_task_annotations: bool | None = None,
    ignore_unresolved_internal_underscore_references: bool | None = None,
    lightweight_readme_only: bool = False,
    include_collection_checks: bool = False,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    failure_policy: FailurePolicy | None = None,
    scan_role_fn=scan_role,
    resolve_repo_scan_facade_fn=_resolve_repo_scan_facade,
) -> RepoScanResult:
    """Package-owned repo scan seam for the fsrc public facade."""
    return resolve_repo_scan_facade_fn().run_repo_scan(
        repo_url=repo_url,
        repo_role_path=repo_role_path,
        repo_style_readme_path=repo_style_readme_path,
        style_readme_path=style_readme_path,
        repo_ref=repo_ref,
        repo_timeout=repo_timeout,
        lightweight_readme_only=lightweight_readme_only,
        scan_role_fn=lambda role_path, **scan_kwargs: scan_role_fn(
            role_path,
            compare_role_path=compare_role_path,
            style_readme_path=(
                scan_kwargs.get("style_readme_path")
                if isinstance(scan_kwargs.get("style_readme_path"), str)
                else style_readme_path
            ),
            role_name_override=(
                scan_kwargs.get("role_name_override")
                if isinstance(scan_kwargs.get("role_name_override"), str)
                else None
            ),
            vars_seed_paths=vars_seed_paths,
            concise_readme=concise_readme,
            scanner_report_output=scanner_report_output,
            include_vars_main=include_vars_main,
            include_scanner_report_link=include_scanner_report_link,
            readme_config_path=readme_config_path,
            adopt_heading_mode=adopt_heading_mode,
            style_guide_skeleton=style_guide_skeleton,
            keep_unknown_style_sections=keep_unknown_style_sections,
            exclude_path_patterns=exclude_path_patterns,
            style_source_path=style_source_path,
            policy_config_path=policy_config_path,
            fail_on_unconstrained_dynamic_includes=(
                fail_on_unconstrained_dynamic_includes
            ),
            fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
            ignore_unresolved_internal_underscore_references=(
                ignore_unresolved_internal_underscore_references
            ),
            include_collection_checks=include_collection_checks,
            include_task_parameters=include_task_parameters,
            include_task_runbooks=include_task_runbooks,
            inline_task_runbooks=inline_task_runbooks,
            failure_policy=failure_policy,
        ),
    )
