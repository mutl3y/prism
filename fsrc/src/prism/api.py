"""Minimal API entrypoint for the fsrc Prism package lane."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any
import traceback

from prism.api_layer import non_collection as api_non_collection
from prism.errors import PrismRuntimeError, ROLE_SCAN_RUNTIME_ERROR, to_failure_detail
from prism.errors import FailurePolicy
from prism.scanner_data import CollectionScanResult, RepoScanResult, RoleScanResult


API_PUBLIC_ENTRYPOINTS: tuple[str, ...] = ("scan_collection", "scan_role", "scan_repo")
API_RETAINED_COMPATIBILITY_SEAMS: tuple[str, ...] = ("run_scan",)

_repo_scan_facade: Any | None = None

__all__ = ["scan_collection", "scan_repo", "scan_role"]


def _resolve_repo_scan_facade() -> Any:
    global _repo_scan_facade
    if _repo_scan_facade is None:
        _repo_scan_facade = importlib.import_module(
            "prism.repo_services"
        ).repo_scan_facade
    return _repo_scan_facade


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
) -> dict[str, object]:
    """Run the non-collection scanner orchestration through the package seam."""
    return api_non_collection.run_scan(
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
        policy_context=policy_context,
        strict_phase_failures=strict_phase_failures,
        scan_pipeline_plugin=scan_pipeline_plugin,
    )


def scan_collection(
    collection_path: str,
    *,
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
    include_rendered_readme: bool = False,
    detailed_catalog: bool = False,
    include_collection_checks: bool = False,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    runbook_output_dir: str | None = None,
    runbook_csv_output_dir: str | None = None,
    include_traceback: bool = False,
) -> CollectionScanResult:
    """Scan every role under a collection's roles/ folder and return a payload."""
    del concise_readme
    del scanner_report_output
    del include_scanner_report_link
    del policy_config_path
    del include_rendered_readme
    del runbook_output_dir
    del runbook_csv_output_dir

    normalized_collection_path = (
        collection_path.strip() if isinstance(collection_path, str) else ""
    )
    if not normalized_collection_path:
        raise PrismRuntimeError(
            code="collection_path_invalid",
            category="validation",
            message="collection_path must be a non-empty string.",
            detail={"field": "collection_path"},
        )

    collection_root = Path(normalized_collection_path)
    if not collection_root.exists() or not collection_root.is_dir():
        raise PrismRuntimeError(
            code="collection_path_not_found",
            category="validation",
            message=f"collection_path must be an existing directory: {normalized_collection_path}",
            detail={"collection_path": normalized_collection_path},
        )

    roles_root = collection_root / "roles"
    if not roles_root.exists() or not roles_root.is_dir():
        raise PrismRuntimeError(
            code="collection_roles_dir_missing",
            category="validation",
            message=f"collection roles directory is missing: {roles_root}",
            detail={"roles_path": str(roles_root)},
        )

    roles_payload: list[dict[str, object]] = []
    scan_errors: list[dict[str, Any]] = []
    scanned_count = 0

    for role_dir in sorted(path for path in roles_root.iterdir() if path.is_dir()):
        scanned_count += 1
        try:
            role_payload = scan_role(
                str(role_dir),
                compare_role_path=compare_role_path,
                style_readme_path=style_readme_path,
                vars_seed_paths=vars_seed_paths,
                include_vars_main=include_vars_main,
                readme_config_path=readme_config_path,
                adopt_heading_mode=adopt_heading_mode,
                style_guide_skeleton=style_guide_skeleton,
                keep_unknown_style_sections=keep_unknown_style_sections,
                exclude_path_patterns=exclude_path_patterns,
                style_source_path=style_source_path,
                fail_on_unconstrained_dynamic_includes=(
                    fail_on_unconstrained_dynamic_includes
                ),
                fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
                ignore_unresolved_internal_underscore_references=(
                    ignore_unresolved_internal_underscore_references
                ),
                detailed_catalog=detailed_catalog,
                include_collection_checks=include_collection_checks,
                include_task_parameters=include_task_parameters,
                include_task_runbooks=include_task_runbooks,
                inline_task_runbooks=inline_task_runbooks,
            )
            roles_payload.append(
                {
                    "role": role_dir.name,
                    "role_path": str(role_dir),
                    "payload": role_payload,
                    "rendered_readme": str(role_payload.get("output") or ""),
                }
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - contract path exercised in CLI parity tests
            failure_detail = to_failure_detail(
                code=ROLE_SCAN_RUNTIME_ERROR,
                message=f"Role scan failed for {role_dir.name}: {exc}",
                source=f"collection_role:{role_dir.name}",
                cause=exc,
                traceback_text=(traceback.format_exc() if include_traceback else None),
            )
            scan_errors.append(failure_detail)
            roles_payload.append(
                {
                    "role": role_dir.name,
                    "role_path": str(role_dir),
                    "payload": {},
                    "failure": failure_detail,
                }
            )

    metadata: dict[str, object] = {
        "scan_degraded": bool(scan_errors),
        "scan_errors": scan_errors,
    }
    return {
        "collection_name": collection_root.name,
        "collection_path": str(collection_root),
        "roles": roles_payload,
        "summary": {
            "roles_total": scanned_count,
            "roles_failed": len(scan_errors),
            "roles_succeeded": scanned_count - len(scan_errors),
        },
        "metadata": metadata,
    }


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
) -> RoleScanResult:
    """Objective-critical role scan facade for fsrc API consumers."""
    return api_non_collection.scan_role(
        role_path,
        compare_role_path=compare_role_path,
        style_readme_path=style_readme_path,
        role_name_override=role_name_override,
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
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        detailed_catalog=detailed_catalog,
        include_collection_checks=include_collection_checks,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        failure_policy=failure_policy,
        run_scan_fn=run_scan,
    )


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
) -> RepoScanResult:
    """Objective-critical repo scan facade for fsrc API consumers."""
    return api_non_collection.scan_repo(
        repo_url,
        repo_ref=repo_ref,
        repo_role_path=repo_role_path,
        repo_timeout=repo_timeout,
        repo_style_readme_path=repo_style_readme_path,
        compare_role_path=compare_role_path,
        style_readme_path=style_readme_path,
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
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        lightweight_readme_only=lightweight_readme_only,
        include_collection_checks=include_collection_checks,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        failure_policy=failure_policy,
        scan_role_fn=scan_role,
        resolve_repo_scan_facade_fn=_resolve_repo_scan_facade,
    )
