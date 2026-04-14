"""Minimal API entrypoint for the fsrc Prism package lane."""

from __future__ import annotations

import copy
import importlib
from pathlib import Path
from typing import Any
import traceback

from prism.errors import PrismRuntimeError, ROLE_SCAN_RUNTIME_ERROR, to_failure_detail
from prism.errors import FailurePolicy
from prism.scanner_core.di import DIContainer
from prism.scanner_core.feature_detector import FeatureDetector
from prism.scanner_kernel.orchestrator import (
    resolve_scan_pipeline_plugin_class,
    resolve_scan_pipeline_plugin_name,
    route_scan_payload_orchestration,
)
from prism.scanner_core.scan_request import build_run_scan_options_canonical
from prism.scanner_core.scanner_context import ScannerContext
from prism.scanner_core.variable_discovery import VariableDiscovery
from prism.scanner_plugins.defaults import resolve_comment_driven_documentation_plugin
from prism.scanner_plugins import DEFAULT_PLUGIN_REGISTRY
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


def _merge_metadata_preserving_existing(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if key not in merged:
            merged[key] = value
            continue

        existing_value = merged[key]
        if isinstance(existing_value, dict) and isinstance(value, dict):
            merged[key] = _merge_metadata_preserving_existing(existing_value, value)
    return merged


def _orchestrate_scan_payload_with_plugin_instance(
    *,
    plugin: Any,
    plugin_name: str,
    payload: dict[str, Any],
    scan_options: dict[str, Any],
    strict_mode: bool,
    preflight_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = payload.get("metadata")
    base_metadata = copy.deepcopy(metadata) if isinstance(metadata, dict) else {}

    if isinstance(preflight_context, dict):
        plugin_output: Any = dict(preflight_context)
    else:
        try:
            process_scan_pipeline = getattr(plugin, "process_scan_pipeline", None)
            if callable(process_scan_pipeline):
                plugin_output = process_scan_pipeline(
                    scan_options=copy.deepcopy(scan_options),
                    scan_context=copy.deepcopy(base_metadata),
                )
            else:
                plugin_output = {}
        except Exception as exc:
            if strict_mode:
                raise PrismRuntimeError(
                    code="scan_pipeline_plugin_failed",
                    category="runtime",
                    message="scan-pipeline plugin execution failed",
                    detail={"plugin": plugin_name, "error": str(exc)},
                ) from exc

            warning_metadata = dict(base_metadata)
            existing_warnings = warning_metadata.get("plugin_runtime_warnings")
            warnings_list = (
                list(existing_warnings) if isinstance(existing_warnings, list) else []
            )
            warnings_list.append(
                {
                    "code": "scan_pipeline_plugin_failed",
                    "plugin": plugin_name,
                    "message": str(exc),
                }
            )
            warning_metadata["plugin_runtime_warnings"] = warnings_list
            payload["metadata"] = warning_metadata
            return payload

    if not isinstance(plugin_output, dict):
        return payload

    payload["metadata"] = _merge_metadata_preserving_existing(
        base_metadata,
        plugin_output,
    )
    return payload


def _orchestrate_with_scan_pipeline_plugin(
    *,
    context: ScannerContext,
    canonical_options: dict[str, Any],
    strict_mode: bool,
    preflight_context: dict[str, Any] | None = None,
    registry: Any | None = None,
) -> dict[str, object]:
    payload = context.orchestrate_scan()
    plugin_name = "unresolved"
    registry_obj = registry or DEFAULT_PLUGIN_REGISTRY

    try:
        plugin_name = resolve_scan_pipeline_plugin_name(
            scan_options=canonical_options,
            registry=registry_obj,
        )
        plugin_class = resolve_scan_pipeline_plugin_class(
            registry=registry_obj,
            plugin_name=plugin_name,
        )
    except Exception as exc:
        if strict_mode:
            raise PrismRuntimeError(
                code="scan_pipeline_plugin_failed",
                category="runtime",
                message="scan-pipeline plugin execution failed",
                detail={"plugin": plugin_name, "error": str(exc)},
            ) from exc

        metadata = payload.get("metadata")
        warning_metadata = dict(metadata) if isinstance(metadata, dict) else {}
        existing_warnings = warning_metadata.get("plugin_runtime_warnings")
        warnings_list = (
            list(existing_warnings) if isinstance(existing_warnings, list) else []
        )
        warnings_list.append(
            {
                "code": "scan_pipeline_plugin_failed",
                "plugin": plugin_name,
                "message": str(exc),
            }
        )
        warning_metadata["plugin_runtime_warnings"] = warnings_list
        payload["metadata"] = warning_metadata
        return payload

    if plugin_class is None:
        return payload

    plugin_instance = plugin_class()
    orchestrate_scan_payload = getattr(
        plugin_instance, "orchestrate_scan_payload", None
    )
    if callable(orchestrate_scan_payload):
        return orchestrate_scan_payload(
            payload=payload,
            scan_options=canonical_options,
            strict_mode=strict_mode,
            preflight_context=preflight_context,
        )

    return _orchestrate_scan_payload_with_plugin_instance(
        plugin=plugin_instance,
        plugin_name=plugin_name,
        payload=payload,
        scan_options=canonical_options,
        strict_mode=strict_mode,
        preflight_context=preflight_context,
    )


def run_scan(
    role_path: str,
    *,
    role_name_override: str | None = None,
    readme_config_path: str | None = None,
    include_vars_main: bool = True,
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
    """Run a minimal fsrc scanner-core orchestration and return a payload."""
    validated_role_path = _validate_role_path(role_path)

    canonical_options = build_run_scan_options_canonical(
        role_path=validated_role_path,
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
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        policy_context=policy_context,
    )
    canonical_options["strict_phase_failures"] = bool(strict_phase_failures)
    if isinstance(scan_pipeline_plugin, str) and scan_pipeline_plugin.strip():
        canonical_options["scan_pipeline_plugin"] = scan_pipeline_plugin.strip()

    scan_state: dict[str, Any] = {
        "discovered_rows": tuple(),
        "features": {},
    }
    container: DIContainer | None = None

    def _variable_discovery_factory(
        di: DIContainer,
        resolved_role_path: str,
        options: dict[str, Any],
    ) -> Any:
        discovery = VariableDiscovery(di, resolved_role_path, options)

        class _RecordingVariableDiscovery:
            def discover(self) -> tuple[dict[str, Any], ...]:
                rows = discovery.discover()
                scan_state["discovered_rows"] = tuple(rows)
                return rows

        return _RecordingVariableDiscovery()

    def _feature_detector_factory(
        di: DIContainer,
        resolved_role_path: str,
        options: dict[str, Any],
    ) -> Any:
        detector = FeatureDetector(di, resolved_role_path, options)

        class _RecordingFeatureDetector:
            def detect(self) -> dict[str, Any]:
                features = detector.detect()
                scan_state["features"] = dict(features)
                return features

        return _RecordingFeatureDetector()

    def _prepare_scan_context_fn(scan_options: dict[str, Any]) -> dict[str, Any]:
        resolved_role_path = str(scan_options["role_path"])
        role_root = Path(resolved_role_path).resolve()
        role_name = str(scan_options.get("role_name_override") or role_root.name)
        rows = tuple(scan_state.get("discovered_rows") or ())
        features = dict(scan_state.get("features") or {})
        yaml_parse_failures = canonical_options.get("yaml_parse_failures")
        normalized_yaml_parse_failures = (
            list(yaml_parse_failures) if isinstance(yaml_parse_failures, list) else []
        )

        display_variables: dict[str, dict[str, Any]] = {}
        for row in sorted(rows, key=lambda item: str(item.get("name", ""))):
            row_name = str(row.get("name") or "")
            if not row_name:
                continue
            display_variables[row_name] = {
                "type": row.get("type"),
                "default": row.get("default"),
                "source": row.get("source"),
                "required": bool(row.get("required", False)),
                "documented": bool(row.get("documented", False)),
                "secret": bool(row.get("secret", False)),
                "is_unresolved": bool(row.get("is_unresolved", False)),
                "is_ambiguous": bool(row.get("is_ambiguous", False)),
                "uncertainty_reason": row.get("uncertainty_reason"),
            }

        requirements_display: list[dict[str, str]] = []
        raw_collections = str(features.get("external_collections") or "none")
        if raw_collections != "none":
            requirements_display = [
                {"collection": name.strip()}
                for name in raw_collections.split(",")
                if name.strip()
            ]

        return {
            "rp": resolved_role_path,
            "role_name": role_name,
            "description": _extract_role_description(role_root, role_name),
            "requirements_display": requirements_display,
            "undocumented_default_filters": [],
            "display_variables": display_variables,
            "metadata": {
                "features": features,
                "variable_insights": [dict(row) for row in rows],
                "yaml_parse_failures": normalized_yaml_parse_failures,
                "role_notes": resolve_comment_driven_documentation_plugin(
                    container
                ).extract_role_notes_from_comments(
                    resolved_role_path,
                    exclude_paths=scan_options.get("exclude_path_patterns"),
                ),
            },
        }

    container = DIContainer(
        role_path=canonical_options["role_path"],
        scan_options=canonical_options,
        factory_overrides={
            "variable_discovery_factory": _variable_discovery_factory,
            "feature_detector_factory": _feature_detector_factory,
        },
    )
    context = ScannerContext(
        di=container,
        role_path=canonical_options["role_path"],
        scan_options=canonical_options,
        prepare_scan_context_fn=_prepare_scan_context_fn,
    )
    strict_mode = bool(canonical_options.get("strict_phase_failures", True))

    runtime_registry = canonical_options.get("plugin_registry")

    def _legacy_orchestrator(
        *,
        role_path: str,
        scan_options: dict[str, Any],
    ) -> dict[str, Any]:
        del role_path
        del scan_options
        return context.orchestrate_scan()

    def _kernel_orchestrator(
        *,
        role_path: str,
        scan_options: dict[str, Any],
    ) -> dict[str, Any]:
        del role_path
        return _orchestrate_with_scan_pipeline_plugin(
            context=context,
            canonical_options=dict(canonical_options, **scan_options),
            strict_mode=strict_mode,
            preflight_context=scan_options.get("_scan_pipeline_preflight_context"),
            registry=runtime_registry,
        )

    return route_scan_payload_orchestration(
        role_path=canonical_options["role_path"],
        scan_options=canonical_options,
        legacy_orchestrator_fn=_legacy_orchestrator,
        kernel_orchestrator_fn=_kernel_orchestrator,
        registry=runtime_registry,
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
    del concise_readme
    del scanner_report_output
    del include_scanner_report_link
    del policy_config_path

    strict_phase_failures = True
    if failure_policy is not None:
        strict_phase_failures = bool(failure_policy.strict)

    return run_scan(
        role_path,
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
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        strict_phase_failures=strict_phase_failures,
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
    del concise_readme
    del scanner_report_output
    del include_scanner_report_link
    del policy_config_path

    return _resolve_repo_scan_facade().run_repo_scan(
        repo_url=repo_url,
        repo_role_path=repo_role_path,
        repo_style_readme_path=repo_style_readme_path,
        style_readme_path=style_readme_path,
        repo_ref=repo_ref,
        repo_timeout=repo_timeout,
        lightweight_readme_only=lightweight_readme_only,
        scan_role_fn=lambda role_path, **scan_kwargs: scan_role(
            role_path,
            compare_role_path=compare_role_path,
            style_readme_path=(
                scan_kwargs.get("style_readme_path")
                if isinstance(scan_kwargs.get("style_readme_path"), str)
                else style_readme_path
            ),
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
            include_collection_checks=include_collection_checks,
            include_task_parameters=include_task_parameters,
            include_task_runbooks=include_task_runbooks,
            inline_task_runbooks=inline_task_runbooks,
            failure_policy=failure_policy,
        ),
    )
