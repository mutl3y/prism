"""Public library API for scanner consumers.

This module provides a stable import surface for external tooling that wants
machine-readable scan results without coupling to CLI internals.

`api.py` is the stable top-level facade for Prism's public library API.
Package-owned implementation now lives under `prism.api_layer`, while this
module preserves public exports and only the compatibility seams that are
intentionally retained.
"""

from __future__ import annotations

import json
from typing import Any
import yaml

from .collection_plugins import scan_collection_plugins
from .errors import (
    FailurePolicy,
    ROLE_CONTENT_ENCODING_INVALID,
    ROLE_CONTENT_INVALID,
    ROLE_CONTENT_IO_ERROR,
    ROLE_CONTENT_JSON_INVALID,
    ROLE_CONTENT_MISSING,
    ROLE_CONTENT_YAML_INVALID,
    ROLE_SCAN_RUNTIME_ERROR,
    to_failure_detail,
)
from .api_layer import collection as api_collection
from .api_layer import common as api_common
from .api_layer import repo as api_repo
from .api_layer import role as api_role
from .repo_services import repo_scan_facade as _repo_scan_facade
from .scanner import _run_scan_payload
from .scanner import run_scan as _scanner_run_scan
from .scanner_analysis import render_runbook, render_runbook_csv
from .scanner_analysis.collection_dependencies import (  # noqa: F401
    _collection_dependency_key,
    _role_dependency_key,
    _merge_dependency_entry,
    _finalize_dependency_bucket,
    _load_yaml_document,
    _requirements_entries_from_document,
)
from .scanner_data.contracts_errors import (
    CollectionScanResult,
    RepoScanResult,
    RoleScanResult,
)
from .scanner_io.collection_renderer import write_collection_runbook_artifacts
from .scanner_readme import render_readme

API_PUBLIC_ENTRYPOINTS: tuple[str, ...] = ("scan_collection", "scan_repo", "scan_role")
API_SHARED_REPO_COMPATIBILITY_SEAMS: tuple[str, ...] = (
    "_build_lightweight_sparse_clone_paths",
    "_build_repo_intake_components",
    "_build_repo_style_readme_candidates",
    "_build_sparse_clone_paths",
    "_checkout_repo_lightweight_style_readme",
    "_checkout_repo_scan_role",
    "_clone_repo",
    "_fetch_repo_directory_names",
    "_fetch_repo_file",
    "_normalize_repo_scan_payload",
    "_normalize_repo_scan_metadata_paths",
    "_prepare_repo_scan_inputs",
    "_repo_name_from_url",
    "_repo_path_looks_like_role",
    "_repo_scan_workspace",
    "_run_repo_scan",
    "_resolve_repo_scan_target",
    "_resolve_repo_scan_scanner_report_relpath",
    "_resolve_style_readme_candidate",
)
API_RETAINED_PATCHABLE_SEAMS: tuple[str, ...] = (
    "run_scan",
    "render_readme",
    "render_runbook",
    "render_runbook_csv",
    "_run_scan_payload",
    "_normalize_repo_style_guide_path",
    "_collection_role_failure_details",
    "_parse_scan_role_payload",
    "_normalize_scan_role_payload_shape",
    "_build_failure_record",
    "_aggregate_collection_dependencies",
    "_render_collection_role_readme",
    "_write_collection_role_runbook_artifacts",
)
API_TRANSITIONAL_COMPATIBILITY_SEAMS: tuple[str, ...] = ()

# Compatibility export for downstream imports and parity checks with CLI/helpers.
_build_lightweight_sparse_clone_paths = (
    _repo_scan_facade.build_lightweight_sparse_clone_paths
)
_build_repo_intake_components = _repo_scan_facade.build_repo_intake_components
_repo_build_repo_style_readme_candidates = (
    _repo_scan_facade.build_repo_style_readme_candidates
)
_build_sparse_clone_paths = _repo_scan_facade.build_sparse_clone_paths
_checkout_repo_lightweight_style_readme = (
    _repo_scan_facade.checkout_repo_lightweight_style_readme
)
_checkout_repo_scan_role = _repo_scan_facade.checkout_repo_scan_role
_clone_repo = _repo_scan_facade.clone_repo
_fetch_repo_directory_names = _repo_scan_facade.fetch_repo_directory_names
_fetch_repo_file = _repo_scan_facade.fetch_repo_file
_normalize_repo_scan_payload = _repo_scan_facade.normalize_repo_scan_payload
_normalize_repo_scan_metadata_paths = (
    _repo_scan_facade.normalize_repo_scan_metadata_paths
)
_prepare_repo_scan_inputs = _repo_scan_facade.prepare_repo_scan_inputs
_repo_name_from_url = _repo_scan_facade.repo_name_from_url
_repo_path_looks_like_role = _repo_scan_facade.repo_path_looks_like_role
_repo_scan_workspace = _repo_scan_facade.repo_scan_workspace
_run_repo_scan = _repo_scan_facade.run_repo_scan
_resolve_repo_scan_target = _repo_scan_facade.resolve_repo_scan_target
_resolve_repo_scan_scanner_report_relpath = (
    _repo_scan_facade.resolve_repo_scan_scanner_report_relpath
)
_resolve_style_readme_candidate = _repo_scan_facade.resolve_style_readme_candidate

_build_repo_style_readme_candidates = _repo_build_repo_style_readme_candidates
run_scan = _scanner_run_scan


def _normalize_repo_style_guide_path(
    payload: dict[str, Any] | str,
    repo_style_readme_path: str | None,
) -> dict[str, Any] | str:
    return api_collection.normalize_repo_style_guide_path(
        payload, repo_style_readme_path
    )


_REQUIRED_ROLE_DIRS = ("defaults", "tasks", "meta")

_COLLECTION_ROLE_CONTENT_RECOVERABLE_ERRORS = (
    FileNotFoundError,
    OSError,
    UnicodeDecodeError,
    ValueError,
    json.JSONDecodeError,
    yaml.YAMLError,
    RuntimeError,
)

_COLLECTION_ROLE_FAILURE_CODES: tuple[tuple[type[Exception], str, str], ...] = (
    (FileNotFoundError, ROLE_CONTENT_MISSING, "io"),
    (UnicodeDecodeError, ROLE_CONTENT_ENCODING_INVALID, "io"),
    (json.JSONDecodeError, ROLE_CONTENT_JSON_INVALID, "parser"),
    (yaml.YAMLError, ROLE_CONTENT_YAML_INVALID, "parser"),
    (OSError, ROLE_CONTENT_IO_ERROR, "io"),
    (ValueError, ROLE_CONTENT_INVALID, "validation"),
    (RuntimeError, ROLE_SCAN_RUNTIME_ERROR, "runtime"),
)


def _collection_role_failure_details(exc: Exception) -> tuple[str, str, str | None]:
    return api_common.collection_role_failure_details(
        exc,
        collection_role_failure_codes=_COLLECTION_ROLE_FAILURE_CODES,
    )


def _parse_scan_role_payload(payload: str | dict[str, Any]) -> dict[str, Any]:
    return api_common.parse_scan_role_payload(payload)


def _normalize_scan_role_payload_shape(payload: dict[str, Any]) -> RoleScanResult:
    return api_common.normalize_scan_role_payload_shape(payload)


def _build_failure_record(
    *,
    role_name: str,
    role_path: str,
    exc: Exception,
    include_traceback: bool,
) -> dict[str, Any]:
    return api_common.build_failure_record(
        role_name=role_name,
        role_path=role_path,
        exc=exc,
        include_traceback=include_traceback,
        collection_role_failure_details_fn=_collection_role_failure_details,
        to_failure_detail_fn=to_failure_detail,
    )


def _aggregate_collection_dependencies(collection_root) -> dict[str, Any]:
    return api_collection.aggregate_collection_dependencies_payload(collection_root)


def _render_collection_role_readme(
    *,
    payload: dict[str, Any],
    role_name: str,
) -> str:
    return api_collection.render_collection_role_readme(
        payload=payload,
        role_name=role_name,
        render_readme_fn=render_readme,
    )


def _write_collection_role_runbook_artifacts(
    *,
    role_name: str,
    payload: dict[str, Any],
    runbook_output_dir: str | None,
    runbook_csv_output_dir: str | None,
) -> None:
    return api_collection.write_collection_role_runbook_artifacts_payload(
        role_name=role_name,
        payload=payload,
        runbook_output_dir=runbook_output_dir,
        runbook_csv_output_dir=runbook_csv_output_dir,
        write_collection_runbook_artifacts_fn=write_collection_runbook_artifacts,
        render_runbook_fn=render_runbook,
        render_runbook_csv_fn=render_runbook_csv,
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
    """Scan an Ansible collection root and return per-role payloads + metadata."""
    return api_collection.scan_collection(
        collection_path,
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
        include_rendered_readme=include_rendered_readme,
        detailed_catalog=detailed_catalog,
        include_collection_checks=include_collection_checks,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        runbook_output_dir=runbook_output_dir,
        runbook_csv_output_dir=runbook_csv_output_dir,
        include_traceback=include_traceback,
        load_yaml_document_fn=_load_yaml_document,
        scan_role_fn=scan_role,
        render_collection_role_readme_fn=_render_collection_role_readme,
        write_collection_role_runbook_artifacts_fn=_write_collection_role_runbook_artifacts,
        build_failure_record_fn=_build_failure_record,
        aggregate_collection_dependencies_fn=_aggregate_collection_dependencies,
        scan_collection_plugins_fn=scan_collection_plugins,
        collection_role_content_recoverable_errors=(
            _COLLECTION_ROLE_CONTENT_RECOVERABLE_ERRORS
        ),
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
) -> RoleScanResult:
    """Return the scanner payload as a Python dictionary.

    External orchestrators should prefer this wrapper over importing internal
    scanner helpers directly. The wrapper uses the in-memory payload path and
    keeps JSON as a serializer rather than the core in-process contract.
    """

    return api_role.scan_role(
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
        run_scan_payload_fn=_run_scan_payload,
        parse_scan_role_payload_fn=_parse_scan_role_payload,
        normalize_scan_role_payload_shape_fn=_normalize_scan_role_payload_shape,
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
    """Clone a repository source, scan the requested role path, and return a dict.

    This mirrors the CLI repo-intake path but remains file-write free for callers
    that want to orchestrate scans programmatically.
    """
    return api_repo.scan_repo(
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
        build_repo_intake_components_fn=_build_repo_intake_components,
        prepare_repo_scan_inputs_fn=_prepare_repo_scan_inputs,
        fetch_repo_directory_names_fn=_fetch_repo_directory_names,
        repo_path_looks_like_role_fn=_repo_path_looks_like_role,
        fetch_repo_file_fn=_fetch_repo_file,
        clone_repo_fn=_clone_repo,
        build_sparse_clone_paths_fn=_build_sparse_clone_paths,
        build_lightweight_sparse_clone_paths_fn=_build_lightweight_sparse_clone_paths,
        resolve_style_readme_candidate_fn=_resolve_style_readme_candidate,
        run_repo_scan_fn=_run_repo_scan,
        repo_scan_workspace_fn=_repo_scan_workspace,
        resolve_repo_scan_target_fn=_resolve_repo_scan_target,
        checkout_repo_lightweight_style_readme_fn=_checkout_repo_lightweight_style_readme,
        checkout_repo_scan_role_fn=_checkout_repo_scan_role,
        repo_name_from_url_fn=_repo_name_from_url,
        normalize_repo_scan_payload_fn=_normalize_repo_scan_payload,
        resolve_repo_scan_scanner_report_relpath_fn=(
            _resolve_repo_scan_scanner_report_relpath
        ),
    )


__all__ = ["scan_collection", "scan_repo", "scan_role"]
