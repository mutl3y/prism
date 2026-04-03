"""Package-owned repo-scan implementation for the public API facade."""

from __future__ import annotations

from prism.errors import FailurePolicy
from prism.scanner_data.contracts_errors import RepoScanResult, RoleScanResult


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
    scan_role_fn,
    build_repo_intake_components_fn,
    prepare_repo_scan_inputs_fn,
    fetch_repo_directory_names_fn,
    repo_path_looks_like_role_fn,
    fetch_repo_file_fn,
    clone_repo_fn,
    build_sparse_clone_paths_fn,
    build_lightweight_sparse_clone_paths_fn,
    resolve_style_readme_candidate_fn,
    run_repo_scan_fn,
    repo_scan_workspace_fn,
    resolve_repo_scan_target_fn,
    checkout_repo_lightweight_style_readme_fn,
    checkout_repo_scan_role_fn,
    repo_name_from_url_fn,
    normalize_repo_scan_payload_fn,
    resolve_repo_scan_scanner_report_relpath_fn,
) -> RepoScanResult:
    def _scan_repo_role(
        role_path: str,
        effective_style_readme_path: str | None,
        role_name_override: str,
    ) -> RoleScanResult:
        return scan_role_fn(
            role_path,
            compare_role_path=compare_role_path,
            style_readme_path=effective_style_readme_path,
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
            include_collection_checks=include_collection_checks,
            include_task_parameters=include_task_parameters,
            include_task_runbooks=include_task_runbooks,
            inline_task_runbooks=inline_task_runbooks,
            failure_policy=failure_policy,
        )

    repo_intake_components = build_repo_intake_components_fn(
        prepare_repo_scan_inputs_fn=prepare_repo_scan_inputs_fn,
        fetch_repo_directory_names_fn=fetch_repo_directory_names_fn,
        repo_path_looks_like_role_fn=repo_path_looks_like_role_fn,
        fetch_repo_file_fn=fetch_repo_file_fn,
        clone_repo_fn=clone_repo_fn,
        build_sparse_clone_paths_fn=build_sparse_clone_paths_fn,
        build_lightweight_sparse_clone_paths_fn=build_lightweight_sparse_clone_paths_fn,
        resolve_style_readme_candidate_fn=resolve_style_readme_candidate_fn,
    )

    run_result = run_repo_scan_fn(
        repo_url=repo_url,
        repo_role_path=repo_role_path,
        repo_style_readme_path=repo_style_readme_path,
        style_readme_path=style_readme_path,
        repo_ref=repo_ref,
        repo_timeout=repo_timeout,
        lightweight_readme_only=lightweight_readme_only,
        create_style_guide=False,
        style_source_path=style_source_path,
        scan_fn=_scan_repo_role,
        repo_scan_workspace_fn=repo_scan_workspace_fn,
        resolve_repo_scan_target_fn=resolve_repo_scan_target_fn,
        checkout_repo_lightweight_style_readme_fn=checkout_repo_lightweight_style_readme_fn,
        checkout_repo_scan_role_fn=checkout_repo_scan_role_fn,
        repo_intake_components=repo_intake_components,
        repo_name_from_url_fn=repo_name_from_url_fn,
    )

    payload = run_result.scan_output
    normalized_repo_style_readme_path = (
        run_result.checkout.resolved_repo_style_readme_path
    )
    if repo_style_readme_path:
        normalized_repo_style_readme_path = repo_style_readme_path
    normalized = normalize_repo_scan_payload_fn(
        payload,
        repo_style_readme_path=normalized_repo_style_readme_path,
        scanner_report_relpath=resolve_repo_scan_scanner_report_relpath_fn(
            concise_readme=concise_readme,
            scanner_report_output=scanner_report_output,
            primary_output_path="scan.json",
        ),
    )
    if isinstance(normalized, dict):
        return normalized
    return payload
