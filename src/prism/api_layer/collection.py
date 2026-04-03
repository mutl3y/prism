"""Package-owned collection-scan implementation for the public API facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prism.scanner_analysis.collection_dependencies import (
    aggregate_collection_dependencies,
)
from prism.scanner_data.contracts_errors import CollectionScanResult


def normalize_repo_style_guide_path(
    payload: dict[str, Any] | str,
    repo_style_readme_path: str | None,
) -> dict[str, Any] | str:
    """Compatibility shim preserving legacy style-guide-path normalization calls."""
    if not isinstance(payload, dict):
        return payload

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return payload

    if not repo_style_readme_path:
        return payload

    style_guide = metadata.get("style_guide")
    if not isinstance(style_guide, dict):
        return payload

    normalized_payload = dict(payload)
    normalized_metadata = dict(metadata)
    normalized_style_guide = dict(style_guide)
    normalized_style_guide["path"] = repo_style_readme_path
    normalized_metadata["style_guide"] = normalized_style_guide
    normalized_payload["metadata"] = normalized_metadata
    return normalized_payload


def aggregate_collection_dependencies_payload(
    collection_root: Path,
) -> dict[str, Any]:
    """Delegate to the canonical collection_dependencies module."""
    return aggregate_collection_dependencies(collection_root)


def render_collection_role_readme(
    *,
    payload: dict[str, Any],
    role_name: str,
    render_readme_fn,
) -> str:
    return render_readme_fn(
        output="README.md",
        role_name=str(payload.get("role_name") or role_name),
        description=str(payload.get("description") or ""),
        variables=(payload.get("variables") or {}),
        requirements=(payload.get("requirements") or []),
        default_filters=(payload.get("default_filters") or []),
        metadata=(payload.get("metadata") or {}),
        write=False,
    )


def write_collection_role_runbook_artifacts_payload(
    *,
    role_name: str,
    payload: dict[str, Any],
    runbook_output_dir: str | None,
    runbook_csv_output_dir: str | None,
    write_collection_runbook_artifacts_fn,
    render_runbook_fn,
    render_runbook_csv_fn,
) -> None:
    write_collection_runbook_artifacts_fn(
        role_name=role_name,
        metadata=(payload.get("metadata") or {}),
        runbook_output_dir=runbook_output_dir,
        runbook_csv_output_dir=runbook_csv_output_dir,
        render_runbook_fn=render_runbook_fn,
        render_runbook_csv_fn=render_runbook_csv_fn,
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
    load_yaml_document_fn,
    scan_role_fn,
    render_collection_role_readme_fn,
    write_collection_role_runbook_artifacts_fn,
    build_failure_record_fn,
    aggregate_collection_dependencies_fn,
    scan_collection_plugins_fn,
    collection_role_content_recoverable_errors: tuple[type[Exception], ...],
) -> CollectionScanResult:
    if (runbook_output_dir or runbook_csv_output_dir) and not detailed_catalog:
        detailed_catalog = True
    root = Path(collection_path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"collection path not found: {collection_path}")

    galaxy_path = root / "galaxy.yml"
    roles_dir = root / "roles"
    if not galaxy_path.is_file() or not roles_dir.is_dir():
        raise FileNotFoundError(
            "collection root must include galaxy.yml and roles/ directory"
        )

    galaxy_doc = load_yaml_document_fn(galaxy_path)
    galaxy_metadata = galaxy_doc if isinstance(galaxy_doc, dict) else {}

    role_entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for role_dir in sorted(path for path in roles_dir.iterdir() if path.is_dir()):
        try:
            payload = scan_role_fn(
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
            )

            rendered_readme = None
            if include_rendered_readme:
                rendered_readme = render_collection_role_readme_fn(
                    payload=payload,
                    role_name=role_dir.name,
                )

            if runbook_output_dir or runbook_csv_output_dir:
                write_collection_role_runbook_artifacts_fn(
                    role_name=role_dir.name,
                    payload=payload,
                    runbook_output_dir=runbook_output_dir,
                    runbook_csv_output_dir=runbook_csv_output_dir,
                )

            role_entries.append(
                {
                    "role": role_dir.name,
                    "path": str(role_dir),
                    "payload": payload,
                    "rendered_readme": rendered_readme,
                }
            )
        except collection_role_content_recoverable_errors as exc:
            failures.append(
                build_failure_record_fn(
                    role_name=role_dir.name,
                    role_path=str(role_dir),
                    exc=exc,
                    include_traceback=include_traceback,
                )
            )
            continue

    dependencies = aggregate_collection_dependencies_fn(root)
    plugin_catalog = scan_collection_plugins_fn(root)
    return {
        "collection": {
            "path": str(root),
            "metadata": galaxy_metadata,
        },
        "dependencies": dependencies,
        "plugin_catalog": plugin_catalog,
        "roles": role_entries,
        "failures": failures,
        "summary": {
            "total_roles": len(role_entries) + len(failures),
            "scanned_roles": len(role_entries),
            "failed_roles": len(failures),
        },
    }
