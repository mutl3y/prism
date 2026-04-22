"""Package-owned collection-scan implementation for the fsrc public API facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from prism.scanner_data import CollectionScanResult


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
    scan_role_fn: Callable[..., Any],
    build_collection_identity_fn: Callable[..., Any],
    aggregate_collection_dependencies_fn: Callable[..., Any],
    scan_collection_plugins_fn: Callable[..., Any],
    render_collection_role_readme_fn: Callable[..., Any],
    write_collection_runbook_artifacts_fn: Callable[..., Any],
    build_collection_role_entry_fn: Callable[..., Any],
    build_collection_failure_record_fn: Callable[..., Any],
    build_collection_scan_result_fn: Callable[..., Any],
    collection_role_content_recoverable_errors: tuple[type[Exception], ...],
    collection_role_runtime_recoverable_errors: tuple[type[Exception], ...],
) -> CollectionScanResult:
    collection_root = Path(collection_path).resolve()
    if not collection_root.is_dir():
        raise FileNotFoundError(f"collection path not found: {collection_path}")

    roles_root = collection_root / "roles"
    galaxy_path = collection_root / "galaxy.yml"
    if not galaxy_path.is_file() or not roles_root.is_dir():
        raise FileNotFoundError(
            "collection root must include galaxy.yml and roles/ directory"
        )

    collection_identity = build_collection_identity_fn(collection_root)

    if (runbook_output_dir or runbook_csv_output_dir) and not detailed_catalog:
        detailed_catalog = True

    recoverable_scan_errors = (
        collection_role_content_recoverable_errors
        + collection_role_runtime_recoverable_errors
    )
    recoverable_artifact_errors = recoverable_scan_errors
    roles_payload: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for role_dir in sorted(path for path in roles_root.iterdir() if path.is_dir()):
        try:
            role_payload = scan_role_fn(
                str(role_dir),
                compare_role_path=compare_role_path,
                style_readme_path=style_readme_path,
                role_name_override=role_dir.name,
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
                detailed_catalog=detailed_catalog,
                include_collection_checks=include_collection_checks,
                include_task_parameters=include_task_parameters,
                include_task_runbooks=include_task_runbooks,
                inline_task_runbooks=inline_task_runbooks,
            )
        except recoverable_scan_errors as exc:
            failures.append(
                build_collection_failure_record_fn(
                    role_dir=role_dir,
                    exc=exc,
                    include_traceback=include_traceback,
                )
            )
            continue

        try:
            rendered_readme = None
            if include_rendered_readme:
                rendered_readme = render_collection_role_readme_fn(
                    role_name=role_dir.name,
                    payload=role_payload,
                )

            if runbook_output_dir or runbook_csv_output_dir:
                write_collection_runbook_artifacts_fn(
                    role_name=role_dir.name,
                    metadata=(role_payload.get("metadata") or {}),
                    runbook_output_dir=runbook_output_dir,
                    runbook_csv_output_dir=runbook_csv_output_dir,
                )
        except recoverable_artifact_errors as exc:
            failures.append(
                build_collection_failure_record_fn(
                    role_dir=role_dir,
                    exc=exc,
                    include_traceback=include_traceback,
                )
            )
            continue

        roles_payload.append(
            build_collection_role_entry_fn(
                role_dir=role_dir,
                payload=role_payload,
                rendered_readme=rendered_readme,
            )
        )

    dependencies = aggregate_collection_dependencies_fn(collection_root)
    plugin_catalog = scan_collection_plugins_fn(collection_root)

    return build_collection_scan_result_fn(
        collection_root=collection_root,
        collection_identity=collection_identity,
        dependencies=dependencies,
        plugin_catalog=plugin_catalog,
        roles=roles_payload,
        failures=failures,
    )
