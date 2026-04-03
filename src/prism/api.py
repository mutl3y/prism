"""Public library API for scanner consumers.

This module provides a stable import surface for external tooling that wants
machine-readable scan results without coupling to CLI internals.
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback
from typing import Any
import yaml

from .collection_plugins import scan_collection_plugins
from .errors import (
    ERROR_CATEGORY_RUNTIME,
    FailurePolicy,
    PrismRuntimeError,
    ROLE_CONTENT_ENCODING_INVALID,
    ROLE_CONTENT_INVALID,
    ROLE_CONTENT_IO_ERROR,
    ROLE_CONTENT_JSON_INVALID,
    ROLE_CONTENT_MISSING,
    ROLE_CONTENT_YAML_INVALID,
    ROLE_SCAN_FAILED,
    ROLE_SCAN_RUNTIME_ERROR,
    SCAN_ROLE_PAYLOAD_JSON_INVALID,
    SCAN_ROLE_PAYLOAD_SHAPE_INVALID,
    SCAN_ROLE_PAYLOAD_TYPE_INVALID,
    to_failure_detail,
)
from .repo_services import repo_scan_facade as _repo_scan_facade
from .scanner import _run_scan_payload
from .scanner import run_scan as _scanner_run_scan
from .scanner_analysis import render_runbook, render_runbook_csv
from .scanner_analysis.collection_dependencies import (  # noqa: F401
    aggregate_collection_dependencies,
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
    if isinstance(exc, PrismRuntimeError):
        return exc.code, exc.category, exc.code

    for error_type, code, category in _COLLECTION_ROLE_FAILURE_CODES:
        if isinstance(exc, error_type):
            return code, category, None
    return ROLE_SCAN_FAILED, ERROR_CATEGORY_RUNTIME, None


def _parse_scan_role_payload(payload: str | dict[str, Any]) -> dict[str, Any]:
    """Parse run_scan JSON payload with explicit classification at the API boundary."""
    if isinstance(payload, dict):
        parsed = payload
    else:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{SCAN_ROLE_PAYLOAD_JSON_INVALID}: scan_role received invalid JSON payload"
            ) from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(
            f"{SCAN_ROLE_PAYLOAD_TYPE_INVALID}: scan_role payload must be a JSON object"
        )

    if "role_name" in parsed and not isinstance(parsed.get("role_name"), str):
        raise RuntimeError(
            f"{SCAN_ROLE_PAYLOAD_SHAPE_INVALID}: expected role_name=str when present"
        )

    if "metadata" in parsed and not isinstance(parsed.get("metadata"), dict):
        raise RuntimeError(
            f"{SCAN_ROLE_PAYLOAD_SHAPE_INVALID}: expected metadata=object when present"
        )

    return parsed


def _normalize_scan_role_payload_shape(payload: dict[str, Any]) -> RoleScanResult:
    """Attach stable public field names to the structured scan payload."""
    normalized = dict(payload)
    if "variables" not in normalized and "display_variables" in normalized:
        normalized["variables"] = normalized["display_variables"]
    if "requirements" not in normalized and "requirements_display" in normalized:
        normalized["requirements"] = normalized["requirements_display"]
    if (
        "default_filters" not in normalized
        and "undocumented_default_filters" in normalized
    ):
        normalized["default_filters"] = normalized["undocumented_default_filters"]
    return normalized


def _build_failure_record(
    *,
    role_name: str,
    role_path: str,
    exc: Exception,
    include_traceback: bool,
) -> dict[str, Any]:
    error_code, error_category, error_detail_code = _collection_role_failure_details(
        exc
    )
    traceback_text = (
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if include_traceback
        else None
    )
    detail = to_failure_detail(
        code=error_code,
        message=str(exc),
        detail_code=error_detail_code,
        source=role_path,
        cause=exc,
        traceback_text=traceback_text,
    )
    failure = {
        "role": role_name,
        "path": role_path,
        "error_code": detail["code"],
        "error_category": detail["category"],
        "error_type": detail.get("cause_type", type(exc).__name__),
        "error": detail["message"],
    }
    if error_detail_code is not None:
        failure["error_detail_code"] = error_detail_code
        failure["detail_code"] = error_detail_code
    if traceback_text:
        failure["traceback"] = traceback_text
    return failure


def _aggregate_collection_dependencies(collection_root: Path) -> dict[str, Any]:
    """Delegate to the canonical collection_dependencies module."""
    return aggregate_collection_dependencies(collection_root)


def _render_collection_role_readme(
    *,
    payload: dict[str, Any],
    role_name: str,
) -> str:
    return render_readme(
        output="README.md",
        role_name=str(payload.get("role_name") or role_name),
        description=str(payload.get("description") or ""),
        variables=(payload.get("variables") or {}),
        requirements=(payload.get("requirements") or []),
        default_filters=(payload.get("default_filters") or []),
        metadata=(payload.get("metadata") or {}),
        write=False,
    )


def _write_collection_role_runbook_artifacts(
    *,
    role_name: str,
    payload: dict[str, Any],
    runbook_output_dir: str | None,
    runbook_csv_output_dir: str | None,
) -> None:
    write_collection_runbook_artifacts(
        role_name=role_name,
        metadata=(payload.get("metadata") or {}),
        runbook_output_dir=runbook_output_dir,
        runbook_csv_output_dir=runbook_csv_output_dir,
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
    # Auto-enable task catalog collection when runbook output is requested.
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

    galaxy_doc = _load_yaml_document(galaxy_path)
    galaxy_metadata = galaxy_doc if isinstance(galaxy_doc, dict) else {}

    role_entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for role_dir in sorted(path for path in roles_dir.iterdir() if path.is_dir()):
        try:
            payload = scan_role(
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
                rendered_readme = _render_collection_role_readme(
                    payload=payload,
                    role_name=role_dir.name,
                )

            if runbook_output_dir or runbook_csv_output_dir:
                _write_collection_role_runbook_artifacts(
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
        except _COLLECTION_ROLE_CONTENT_RECOVERABLE_ERRORS as exc:
            failures.append(
                _build_failure_record(
                    role_name=role_dir.name,
                    role_path=str(role_dir),
                    exc=exc,
                    include_traceback=include_traceback,
                )
            )
            continue

    dependencies = _aggregate_collection_dependencies(root)
    plugin_catalog = scan_collection_plugins(root)
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

    payload = _run_scan_payload(
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
    )
    return _normalize_scan_role_payload_shape(_parse_scan_role_payload(payload))


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

    def _scan_repo_role(
        role_path: str,
        effective_style_readme_path: str | None,
        role_name_override: str,
    ) -> RoleScanResult:
        return scan_role(
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

    repo_intake_components = _build_repo_intake_components(
        prepare_repo_scan_inputs_fn=_prepare_repo_scan_inputs,
        fetch_repo_directory_names_fn=_fetch_repo_directory_names,
        repo_path_looks_like_role_fn=_repo_path_looks_like_role,
        fetch_repo_file_fn=_fetch_repo_file,
        clone_repo_fn=_clone_repo,
        build_sparse_clone_paths_fn=_build_sparse_clone_paths,
        build_lightweight_sparse_clone_paths_fn=_build_lightweight_sparse_clone_paths,
        resolve_style_readme_candidate_fn=_resolve_style_readme_candidate,
    )

    run_result = _run_repo_scan(
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
        repo_scan_workspace_fn=_repo_scan_workspace,
        resolve_repo_scan_target_fn=_resolve_repo_scan_target,
        checkout_repo_lightweight_style_readme_fn=_checkout_repo_lightweight_style_readme,
        checkout_repo_scan_role_fn=_checkout_repo_scan_role,
        repo_intake_components=repo_intake_components,
        repo_name_from_url_fn=_repo_name_from_url,
    )

    payload = run_result.scan_output
    normalized_repo_style_readme_path = (
        run_result.checkout.resolved_repo_style_readme_path
    )
    if repo_style_readme_path:
        normalized_repo_style_readme_path = repo_style_readme_path
    normalized = _normalize_repo_scan_payload(
        payload,
        repo_style_readme_path=normalized_repo_style_readme_path,
        scanner_report_relpath=_resolve_repo_scan_scanner_report_relpath(
            concise_readme=concise_readme,
            scanner_report_output=scanner_report_output,
            primary_output_path="scan.json",
        ),
    )
    if isinstance(normalized, dict):
        return normalized
    return payload


__all__ = ["scan_collection", "scan_repo", "scan_role"]
