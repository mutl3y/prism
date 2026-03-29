"""Canonical scan request normalization and options shaping helpers."""

from __future__ import annotations


def resolve_scan_request_for_runtime(
    *,
    detailed_catalog: bool,
    runbook_output: str | None,
    runbook_csv_output: str | None,
) -> bool:
    """Enable task catalog collection when standalone runbook outputs are requested."""
    if runbook_output or runbook_csv_output:
        return True
    return detailed_catalog


def build_run_scan_options(
    *,
    role_path: str,
    role_name_override: str | None,
    readme_config_path: str | None,
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
) -> dict:
    """Build normalized scan options consumed by scan orchestration helpers."""
    return build_run_scan_options_canonical(
        role_path=role_path,
        role_name_override=role_name_override,
        readme_config_path=readme_config_path,
        include_vars_main=include_vars_main,
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
        fail_on_unconstrained_dynamic_includes=(fail_on_unconstrained_dynamic_includes),
        fail_on_yaml_like_task_annotations=(fail_on_yaml_like_task_annotations),
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
    )


def build_run_scan_options_canonical(
    *,
    role_path: str,
    role_name_override: str | None,
    readme_config_path: str | None,
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
) -> dict:
    """Canonical scan options map builder for scanner runtime path."""
    return {
        "role_path": role_path,
        "role_name_override": role_name_override,
        "readme_config_path": readme_config_path,
        "include_vars_main": include_vars_main,
        "exclude_path_patterns": exclude_path_patterns,
        "detailed_catalog": detailed_catalog,
        "include_task_parameters": include_task_parameters,
        "include_task_runbooks": include_task_runbooks,
        "inline_task_runbooks": inline_task_runbooks,
        "include_collection_checks": include_collection_checks,
        "keep_unknown_style_sections": keep_unknown_style_sections,
        "adopt_heading_mode": adopt_heading_mode,
        "vars_seed_paths": vars_seed_paths,
        "style_readme_path": style_readme_path,
        "style_source_path": style_source_path,
        "style_guide_skeleton": style_guide_skeleton,
        "compare_role_path": compare_role_path,
        "fail_on_unconstrained_dynamic_includes": (
            fail_on_unconstrained_dynamic_includes
        ),
        "fail_on_yaml_like_task_annotations": (fail_on_yaml_like_task_annotations),
        "ignore_unresolved_internal_underscore_references": (
            ignore_unresolved_internal_underscore_references
        ),
    }
