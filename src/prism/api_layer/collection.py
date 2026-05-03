"""Package-owned collection-scan implementation for the fsrc public API facade."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from prism.errors import PrismRuntimeError
from prism.scanner_data import (
    CollectionDependencies,
    CollectionFailureRecord,
    CollectionIdentity,
    CollectionPluginCatalog,
    CollectionRoleEntry,
    CollectionScanResult,
    RunScanOutputPayload,
    ScanMetadata,
)


class ScanRoleFn(Protocol):
    def __call__(
        self,
        role_path: str,
        *,
        compare_role_path: str | None = ...,
        style_readme_path: str | None = ...,
        role_name_override: str | None = ...,
        vars_seed_paths: list[str] | None = ...,
        concise_readme: bool = ...,
        scanner_report_output: str | None = ...,
        include_vars_main: bool = ...,
        include_scanner_report_link: bool = ...,
        readme_config_path: str | None = ...,
        adopt_heading_mode: str | None = ...,
        style_guide_skeleton: bool = ...,
        keep_unknown_style_sections: bool = ...,
        exclude_path_patterns: list[str] | None = ...,
        style_source_path: str | None = ...,
        policy_config_path: str | None = ...,
        fail_on_unconstrained_dynamic_includes: bool | None = ...,
        fail_on_yaml_like_task_annotations: bool | None = ...,
        ignore_unresolved_internal_underscore_references: bool | None = ...,
        detailed_catalog: bool = ...,
        include_collection_checks: bool = ...,
        include_task_parameters: bool = ...,
        include_task_runbooks: bool = ...,
        inline_task_runbooks: bool = ...,
    ) -> RunScanOutputPayload: ...


class BuildCollectionIdentityFn(Protocol):
    def __call__(self, collection_root: Path) -> CollectionIdentity: ...


class AggregateCollectionDependenciesFn(Protocol):
    def __call__(self, collection_root: Path) -> CollectionDependencies: ...


class ScanCollectionPluginsFn(Protocol):
    def __call__(self, collection_root: Path) -> CollectionPluginCatalog: ...


class RenderCollectionRoleReadmeFn(Protocol):
    def __call__(self, *, role_name: str, payload: RunScanOutputPayload) -> str: ...


class WriteCollectionRunbookArtifactsFn(Protocol):
    def __call__(
        self,
        *,
        role_name: str,
        metadata: ScanMetadata,
        runbook_output_dir: str | None,
        runbook_csv_output_dir: str | None,
    ) -> None: ...


class BuildCollectionRoleEntryFn(Protocol):
    def __call__(
        self,
        *,
        role_dir: Path,
        payload: RunScanOutputPayload,
        rendered_readme: str | None,
    ) -> CollectionRoleEntry: ...


class BuildCollectionFailureRecordFn(Protocol):
    def __call__(
        self,
        *,
        role_dir: Path,
        exc: Exception,
        include_traceback: bool,
    ) -> CollectionFailureRecord: ...


class BuildCollectionScanResultFn(Protocol):
    def __call__(
        self,
        *,
        collection_root: Path,
        collection_identity: CollectionIdentity | None,
        dependencies: CollectionDependencies | None,
        plugin_catalog: CollectionPluginCatalog | None,
        roles: list[CollectionRoleEntry],
        failures: list[CollectionFailureRecord],
    ) -> CollectionScanResult: ...


def _payload_metadata(payload: RunScanOutputPayload) -> ScanMetadata:
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        return metadata
    return {}


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
    scan_role_fn: ScanRoleFn,
    build_collection_identity_fn: BuildCollectionIdentityFn,
    aggregate_collection_dependencies_fn: AggregateCollectionDependenciesFn,
    scan_collection_plugins_fn: ScanCollectionPluginsFn,
    render_collection_role_readme_fn: RenderCollectionRoleReadmeFn,
    write_collection_runbook_artifacts_fn: WriteCollectionRunbookArtifactsFn,
    build_collection_role_entry_fn: BuildCollectionRoleEntryFn,
    build_collection_failure_record_fn: BuildCollectionFailureRecordFn,
    build_collection_scan_result_fn: BuildCollectionScanResultFn,
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

    roles_payload: list[CollectionRoleEntry] = []
    failures: list[CollectionFailureRecord] = []

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
        except PrismRuntimeError as exc:
            if not exc.code.startswith("role_content_"):
                raise
            failures.append(
                build_collection_failure_record_fn(
                    role_dir=role_dir,
                    exc=exc,
                    include_traceback=include_traceback,
                )
            )
            continue
        except collection_role_content_recoverable_errors as exc:
            failures.append(
                build_collection_failure_record_fn(
                    role_dir=role_dir,
                    exc=exc,
                    include_traceback=include_traceback,
                )
            )
            continue

        rendered_readme = None
        if include_rendered_readme:
            rendered_readme = render_collection_role_readme_fn(
                role_name=role_dir.name,
                payload=role_payload,
            )

        if runbook_output_dir or runbook_csv_output_dir:
            write_collection_runbook_artifacts_fn(
                role_name=role_dir.name,
                metadata=_payload_metadata(role_payload),
                runbook_output_dir=runbook_output_dir,
                runbook_csv_output_dir=runbook_csv_output_dir,
            )

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
