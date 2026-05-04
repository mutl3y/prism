"""Package-owned non-collection implementation for the fsrc public API facade."""

from __future__ import annotations

import copy
import logging
from pathlib import Path
import threading
from collections.abc import Collection, Mapping
from typing import TYPE_CHECKING, Callable, NotRequired, Protocol, cast

if TYPE_CHECKING:
    from .. import repo_services
    from prism.scanner_core.scan_cache import ScanCacheBackend

from . import plugin_facade
from prism.errors import (
    FailureDetail,
    FailurePolicy,
    PrismRuntimeError,
    normalize_metadata_warnings,
)
from prism.scanner_data import RepoScanResult
from prism.scanner_data.contracts_output import (
    RunScanOutputPayload,
    validate_run_scan_output_payload,
)
from prism.scanner_data.contracts_request import (
    CacheFingerprintProvider,
    DisplayVariables,
    PreparedPolicyBundle,
    ScanMetadata,
    ScanPolicyContext,
    ScanOptionsDict,
    require_strict_phase_failures,
)
from prism.scanner_kernel.orchestrator import RoutePreflightRuntimeCarrier

_logger = logging.getLogger(__name__)
_MISSING_PREPARED_POLICY_BUNDLE = object()
_UNCACHEABLE_BUNDLE_VALUE = object()


class _ExecutionRequestEnsurePreparedPolicyBundleFn(Protocol):
    """Execution-request contract for policy bundle preparation."""

    def __call__(self, *, scan_options: ScanOptionsDict, di: object) -> None: ...


class _BuildRunScanOptionsCanonicalFn(Protocol):
    """Typed local contract for canonical run-scan option assembly."""

    def __call__(
        self,
        *,
        role_path: str,
        role_name_override: str | None,
        readme_config_path: str | None,
        policy_config_path: str | None = None,
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
        policy_context: ScanPolicyContext | None = None,
        prepared_policy_bundle: PreparedPolicyBundle | None = None,
    ) -> ScanOptionsDict: ...


class _KernelOrchestratorFn(Protocol):
    """Typed local kernel orchestration contract for routed non-collection scans."""

    def __call__(
        self,
        *,
        role_path: str,
        scan_options: ScanOptionsDict,
        route_preflight_runtime: RoutePreflightRuntimeCarrier | None = None,
    ) -> dict[str, object]: ...


class _NormalizedNonCollectionResult(RunScanOutputPayload):
    """Stable public payload for the non-collection run-scan seam."""

    variables: DisplayVariables
    requirements: list[object]
    default_filters: list[object]
    warnings: NotRequired[list[FailureDetail]]


class _RouteScanPayloadOrchestrationFn(Protocol):
    """Route the non-collection payload through preflight and runtime orchestration."""

    def __call__(
        self,
        *,
        role_path: str,
        scan_options: ScanOptionsDict,
        kernel_orchestrator_fn: _KernelOrchestratorFn,
        registry: object | None = None,
    ) -> dict[str, object]: ...


class _RepoScanSourceRoleFn(Protocol):
    """Full scan_role contract accepted by the repo-scan facade entrypoint."""

    def __call__(
        self,
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
    ) -> RunScanOutputPayload: ...


class _OrchestrateScanPayloadWithSelectedPluginFn(Protocol):
    """Execute runtime payload orchestration for the selected scan plugin."""

    def __call__(
        self,
        *,
        build_payload_fn: Callable[[], RunScanOutputPayload],
        scan_options: ScanOptionsDict,
        strict_mode: bool,
        preflight_context: ScanMetadata | None = None,
        route_preflight_runtime: RoutePreflightRuntimeCarrier | None = None,
        registry: object | None = None,
    ) -> dict[str, object]: ...


def _copy_scan_options(scan_options: ScanOptionsDict) -> ScanOptionsDict:
    return cast(ScanOptionsDict, _copy_object_mapping(scan_options))


def _resolve_run_scan_default_classes(
    *,
    di_container_cls: object | None,
    feature_detector_cls: object | None,
    scanner_context_cls: object | None,
    variable_discovery_cls: object | None,
) -> tuple[object, object, object, object]:
    """Resolve the default runtime classes for run_scan in one lazy seam."""
    if (
        di_container_cls is not None
        and feature_detector_cls is not None
        and scanner_context_cls is not None
        and variable_discovery_cls is not None
    ):
        return (
            di_container_cls,
            feature_detector_cls,
            scanner_context_cls,
            variable_discovery_cls,
        )

    from prism.scanner_core.di import DIContainer
    from prism.scanner_core.feature_detector import FeatureDetector
    from prism.scanner_core.scanner_context import ScannerContext
    from prism.scanner_core.variable_discovery import VariableDiscovery

    return (
        DIContainer if di_container_cls is None else di_container_cls,
        FeatureDetector if feature_detector_cls is None else feature_detector_cls,
        ScannerContext if scanner_context_cls is None else scanner_context_cls,
        VariableDiscovery if variable_discovery_cls is None else variable_discovery_cls,
    )


def _coerce_scan_metadata(value: object) -> ScanMetadata:
    if not isinstance(value, dict):
        return ScanMetadata()
    return cast(ScanMetadata, copy.copy(value))


def _default_build_run_scan_options_canonical(
    *,
    role_path: str,
    role_name_override: str | None,
    readme_config_path: str | None,
    policy_config_path: str | None = None,
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
    policy_context: ScanPolicyContext | None = None,
    prepared_policy_bundle: PreparedPolicyBundle | None = None,
) -> ScanOptionsDict:
    from prism.scanner_core.scan_request import build_run_scan_options_canonical

    return build_run_scan_options_canonical(
        role_path=role_path,
        role_name_override=role_name_override,
        readme_config_path=readme_config_path,
        policy_config_path=policy_config_path,
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
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        policy_context=policy_context,
        prepared_policy_bundle=prepared_policy_bundle,
    )


def _copy_container_nodes(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _copy_container_nodes(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy_container_nodes(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_copy_container_nodes(item) for item in value)
    if isinstance(value, set):
        return {_copy_container_nodes(item) for item in value}
    if isinstance(value, frozenset):
        return frozenset(_copy_container_nodes(item) for item in value)
    return value


def _copy_object_mapping(value: Mapping[str, object]) -> dict[str, object]:
    return {key: _copy_container_nodes(item) for key, item in value.items()}


def _merge_scan_options(
    base: ScanOptionsDict,
    override: ScanOptionsDict,
) -> ScanOptionsDict:
    merged = _copy_object_mapping(base)
    merged.update(override)
    return cast(ScanOptionsDict, merged)


def _default_route_scan_payload_orchestration(
    *,
    role_path: str,
    scan_options: ScanOptionsDict,
    kernel_orchestrator_fn: _KernelOrchestratorFn,
    registry: object | None = None,
) -> dict[str, object]:
    from prism.scanner_kernel.orchestrator import route_scan_payload_orchestration
    from prism.scanner_core.protocols_runtime import KernelResponse

    def _kernel_orchestrator_adapter(
        *,
        role_path: str,
        scan_options: ScanOptionsDict,
        route_preflight_runtime: RoutePreflightRuntimeCarrier | None = None,
    ) -> KernelResponse:
        return cast(
            KernelResponse,
            kernel_orchestrator_fn(
                role_path=role_path,
                scan_options=scan_options,
                route_preflight_runtime=route_preflight_runtime,
            ),
        )

    return route_scan_payload_orchestration(
        role_path=role_path,
        scan_options=_copy_scan_options(scan_options),
        kernel_orchestrator_fn=_kernel_orchestrator_adapter,
        registry=registry,
    )


def _default_orchestrate_scan_payload_with_selected_plugin(
    *,
    build_payload_fn: Callable[[], RunScanOutputPayload],
    scan_options: ScanOptionsDict,
    strict_mode: bool,
    preflight_context: ScanMetadata | None = None,
    route_preflight_runtime: RoutePreflightRuntimeCarrier | None = None,
    registry: object | None = None,
) -> dict[str, object]:
    from prism.scanner_kernel.orchestrator import (
        orchestrate_scan_payload_with_selected_plugin,
    )

    def _build_payload_dict() -> dict[str, object]:
        return _copy_object_mapping(build_payload_fn())

    return orchestrate_scan_payload_with_selected_plugin(
        build_payload_fn=_build_payload_dict,
        scan_options=_copy_scan_options(scan_options),
        strict_mode=strict_mode,
        preflight_context=preflight_context,
        route_preflight_runtime=route_preflight_runtime,
        registry=registry,
    )


def _coerce_object_list(value: object) -> list[object] | None:
    if not isinstance(value, list):
        return None
    return list(value)


def _coerce_display_variables(value: object) -> DisplayVariables | None:
    if not isinstance(value, dict):
        return None
    return value


def _normalize_non_collection_result_shape(
    payload: Mapping[str, object],
) -> _NormalizedNonCollectionResult:
    validation_candidate = _copy_object_mapping(payload)
    if (
        "display_variables" not in validation_candidate
        and "variables" in validation_candidate
    ):
        validation_candidate["display_variables"] = validation_candidate["variables"]
    if (
        "requirements_display" not in validation_candidate
        and "requirements" in validation_candidate
    ):
        validation_candidate["requirements_display"] = validation_candidate[
            "requirements"
        ]
    if (
        "undocumented_default_filters" not in validation_candidate
        and "default_filters" in validation_candidate
    ):
        validation_candidate["undocumented_default_filters"] = validation_candidate[
            "default_filters"
        ]

    validated_payload = validate_run_scan_output_payload(validation_candidate)
    display_variables = _coerce_display_variables(
        validated_payload["display_variables"]
    )
    requirements_display = _coerce_object_list(
        validated_payload["requirements_display"]
    )
    undocumented_default_filters = _coerce_object_list(
        validated_payload["undocumented_default_filters"]
    )
    metadata = _coerce_scan_metadata(validated_payload["metadata"])

    if display_variables is None:
        raise ValueError("validated display_variables must be a dict")
    if requirements_display is None:
        raise ValueError("validated requirements_display must be a list")
    if undocumented_default_filters is None:
        raise ValueError("validated undocumented_default_filters must be a list")

    normalized: _NormalizedNonCollectionResult = {
        "role_name": validated_payload["role_name"],
        "description": validated_payload["description"],
        "display_variables": display_variables,
        "variables": display_variables,
        "requirements_display": requirements_display,
        "requirements": requirements_display,
        "undocumented_default_filters": undocumented_default_filters,
        "default_filters": undocumented_default_filters,
        "metadata": metadata,
    }

    warnings = normalize_metadata_warnings(_copy_object_mapping(metadata))
    if warnings:
        normalized["warnings"] = warnings

    return normalized


def _bundle_value_fingerprint(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        fingerprints = [_bundle_value_fingerprint(v) for v in value]
        if any(item is _UNCACHEABLE_BUNDLE_VALUE for item in fingerprints):
            return _UNCACHEABLE_BUNDLE_VALUE
        return fingerprints
    if isinstance(value, (set, frozenset)):
        fingerprints = [_bundle_value_fingerprint(v) for v in value]
        if any(item is _UNCACHEABLE_BUNDLE_VALUE for item in fingerprints):
            return _UNCACHEABLE_BUNDLE_VALUE
        return sorted(fingerprints, key=lambda item: repr(item))
    if isinstance(value, dict):
        fingerprints = [
            (str(key), _bundle_value_fingerprint(item)) for key, item in value.items()
        ]
        if any(item is _UNCACHEABLE_BUNDLE_VALUE for _, item in fingerprints):
            return _UNCACHEABLE_BUNDLE_VALUE
        return sorted(fingerprints)
    if isinstance(value, CacheFingerprintProvider):
        return value.cache_fingerprint()
    if getattr(type(value), "PLUGIN_IS_STATELESS", False):
        return f"{type(value).__module__}.{type(value).__qualname__}"
    return _UNCACHEABLE_BUNDLE_VALUE


def _is_string_collection(value: object) -> bool:
    return (
        isinstance(value, Collection)
        and not isinstance(value, (Mapping, str, bytes))
        and all(isinstance(item, str) for item in value)
    )


def _has_prepared_task_line_policy_shape(value: object) -> bool:
    if isinstance(value, Mapping):
        return False

    required_collection_attrs = (
        "TASK_INCLUDE_KEYS",
        "ROLE_INCLUDE_KEYS",
        "INCLUDE_VARS_KEYS",
        "SET_FACT_KEYS",
        "TASK_BLOCK_KEYS",
        "TASK_META_KEYS",
    )
    if not all(
        _is_string_collection(getattr(value, attr_name, None))
        for attr_name in required_collection_attrs
    ):
        return False

    return callable(getattr(value, "detect_task_module", None))


def _has_prepared_jinja_analysis_policy_shape(value: object) -> bool:
    if isinstance(value, Mapping):
        return False
    return callable(getattr(value, "collect_undeclared_jinja_variables", None))


def _has_cacheable_prepared_policy_bundle_shape(raw_bundle: object) -> bool:
    if not isinstance(raw_bundle, dict):
        return False

    return _has_prepared_task_line_policy_shape(
        raw_bundle.get("task_line_parsing")
    ) and _has_prepared_jinja_analysis_policy_shape(raw_bundle.get("jinja_analysis"))


def _prepared_policy_bundle_cache_marker(
    scan_options: Mapping[str, object],
) -> tuple[str, object]:
    raw_bundle = scan_options.get(
        "prepared_policy_bundle", _MISSING_PREPARED_POLICY_BUNDLE
    )
    if raw_bundle is _MISSING_PREPARED_POLICY_BUNDLE or raw_bundle is None:
        return ("__prepared_policy_bundle_state__", "missing")
    if not _has_cacheable_prepared_policy_bundle_shape(raw_bundle):
        return ("__prepared_policy_bundle_state__", "malformed")
    prepared_policy_bundle = cast(PreparedPolicyBundle, raw_bundle)
    fingerprint = sorted(
        (str(key), _bundle_value_fingerprint(value))
        for key, value in prepared_policy_bundle.items()
    )
    if any(value is _UNCACHEABLE_BUNDLE_VALUE for _, value in fingerprint):
        return ("__prepared_policy_bundle_state__", "uncacheable")
    return (
        "__bundle_fingerprint__",
        fingerprint,
    )


_repo_scan_facade: repo_services.RepoScanFacade | None = None
_repo_scan_facade_lock = threading.Lock()


def _resolve_repo_scan_facade() -> repo_services.RepoScanFacade:
    global _repo_scan_facade
    with _repo_scan_facade_lock:
        if _repo_scan_facade is None:
            from prism import repo_services

            _repo_scan_facade = repo_services.repo_scan_facade
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
            with readme_path.open("r", encoding="utf-8") as fh:
                for raw_line in fh:
                    stripped = raw_line.strip().lstrip("#").strip()
                    if stripped:
                        return stripped
        except (OSError, UnicodeDecodeError) as exc:
            _logger.warning(
                "Failed to read README for role %s at %s: %s",
                role_name,
                readme_path,
                exc,
            )
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
    policy_context: ScanPolicyContext | None = None,
    strict_phase_failures: bool = True,
    scan_pipeline_plugin: str | None = None,
    cache_backend: ScanCacheBackend | None = None,
    validate_role_path_fn=_validate_role_path,
    extract_role_description_fn=_extract_role_description,
    build_run_scan_options_canonical_fn: _BuildRunScanOptionsCanonicalFn | None = None,
    route_scan_payload_orchestration_fn: _RouteScanPayloadOrchestrationFn | None = None,
    orchestrate_scan_payload_with_selected_plugin_fn: (
        _OrchestrateScanPayloadWithSelectedPluginFn | None
    ) = None,
    di_container_cls=None,
    feature_detector_cls=None,
    scanner_context_cls=None,
    variable_discovery_cls=None,
    resolve_comment_driven_documentation_plugin_fn: (
        Callable[[object], plugin_facade.CommentDrivenDocumentationPlugin] | None
    ) = None,
    default_plugin_registry: plugin_facade.ScanPipelineRuntimeRegistry | None = None,
) -> _NormalizedNonCollectionResult:
    """Run the non-collection scanner orchestration and return a payload."""
    # Lazy-load scanner_core and scanner_kernel imports to reduce module load time
    if build_run_scan_options_canonical_fn is None:
        build_run_scan_options_canonical_fn = _default_build_run_scan_options_canonical
    if route_scan_payload_orchestration_fn is None:
        route_scan_payload_orchestration_fn = _default_route_scan_payload_orchestration
    if orchestrate_scan_payload_with_selected_plugin_fn is None:
        orchestrate_scan_payload_with_selected_plugin_fn = (
            _default_orchestrate_scan_payload_with_selected_plugin
        )
    (
        di_container_cls,
        feature_detector_cls,
        scanner_context_cls,
        variable_discovery_cls,
    ) = _resolve_run_scan_default_classes(
        di_container_cls=di_container_cls,
        feature_detector_cls=feature_detector_cls,
        scanner_context_cls=scanner_context_cls,
        variable_discovery_cls=variable_discovery_cls,
    )

    from prism.scanner_core.scanner_context import (
        build_non_collection_run_scan_execution_request,
    )

    if resolve_comment_driven_documentation_plugin_fn is None:
        resolve_comment_driven_documentation_plugin_fn = (
            plugin_facade.resolve_comment_driven_documentation_plugin
        )

    if default_plugin_registry is None:
        default_plugin_registry = plugin_facade.get_default_scan_pipeline_registry()

    _resolved_ensure_fn = plugin_facade.ensure_prepared_policy_bundle

    def _ensure_prepared_policy_bundle_for_execution_request(
        *,
        scan_options: ScanOptionsDict,
        di: object,
    ) -> None:
        prepared_policy_bundle = _resolved_ensure_fn(
            scan_options=_copy_object_mapping(scan_options),
            di=di,
        )
        scan_options["prepared_policy_bundle"] = prepared_policy_bundle

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
        policy_context=(
            _copy_object_mapping(policy_context) if policy_context is not None else None
        ),
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
        ensure_prepared_policy_bundle_fn=_ensure_prepared_policy_bundle_for_execution_request,
    )

    _cache_key: str | None = None
    if cache_backend is not None:
        from prism.scanner_core.scan_cache import (
            build_runtime_wiring_identity,
            compute_path_content_hash,
            compute_role_content_hash,
            compute_scan_cache_key,
        )

        _role_content_hash = compute_role_content_hash(execution_request.role_path)
        _bundle_marker_key, _bundle_marker_value = _prepared_policy_bundle_cache_marker(
            execution_request.scan_options
        )
        if (
            _bundle_marker_key == "__prepared_policy_bundle_state__"
            and _bundle_marker_value == "uncacheable"
        ):
            _logger.debug(
                "Skipping scan cache because prepared_policy_bundle contains stateful values without cache_fingerprint()."
            )
            cache_backend = None
        else:
            _stable_opts = {
                k: v
                for k, v in execution_request.scan_options.items()
                if k != "prepared_policy_bundle"
            }
            _external_style_inputs = []
            for _key in ("style_readme_path", "style_source_path"):
                _path = _stable_opts.get(_key)
                if isinstance(_path, str) and _path:
                    _external_style_inputs.append(
                        (_key, compute_path_content_hash(_path))
                    )
            _stable_opts[_bundle_marker_key] = _bundle_marker_value
            if _external_style_inputs:
                _stable_opts["__external_style_fingerprint__"] = sorted(
                    _external_style_inputs
                )
            _stable_opts["__runtime_wiring_identity__"] = build_runtime_wiring_identity(
                route_scan_payload_orchestration_fn=route_scan_payload_orchestration_fn,
                orchestrate_scan_payload_with_selected_plugin_fn=(
                    orchestrate_scan_payload_with_selected_plugin_fn
                ),
                runtime_registry=execution_request.runtime_registry,
            )
            _cache_key = compute_scan_cache_key(
                role_content_hash=_role_content_hash,
                scan_options=_stable_opts,
            )
            _cached = cache_backend.get(_cache_key)
            if _cached is not None:
                return _normalize_non_collection_result_shape(_cached)

    def _kernel_orchestrator(
        *,
        role_path: str,
        scan_options: ScanOptionsDict,
        route_preflight_runtime: RoutePreflightRuntimeCarrier | None = None,
    ) -> dict[str, object]:
        del role_path
        merged_scan_options = _merge_scan_options(
            execution_request.scan_options,
            scan_options,
        )
        return orchestrate_scan_payload_with_selected_plugin_fn(
            build_payload_fn=execution_request.build_payload_fn,
            scan_options=merged_scan_options,
            strict_mode=execution_request.strict_mode,
            route_preflight_runtime=route_preflight_runtime,
            registry=execution_request.runtime_registry,
        )

    result = route_scan_payload_orchestration_fn(
        role_path=execution_request.role_path,
        scan_options=execution_request.scan_options,
        kernel_orchestrator_fn=_kernel_orchestrator,
        registry=execution_request.runtime_registry,
    )

    normalized_result = _normalize_non_collection_result_shape(result)

    if cache_backend is not None and _cache_key is not None:
        cache_backend.set(_cache_key, normalized_result)

    return normalized_result


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
    run_scan_fn: Callable[..., _NormalizedNonCollectionResult] = run_scan,
) -> _NormalizedNonCollectionResult:
    """Package-owned role scan seam for the fsrc public facade."""
    strict_phase_failures = True
    if failure_policy is not None:
        strict_phase_failures = require_strict_phase_failures(
            failure_policy.strict,
            field_name="failure_policy.strict",
        )

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
    return result


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
    scan_role_fn: _RepoScanSourceRoleFn = scan_role,
    resolve_repo_scan_facade_fn=_resolve_repo_scan_facade,
) -> RepoScanResult:
    """Package-owned repo scan seam for the fsrc public facade."""
    delegated_style_readme_path = style_readme_path

    def _scan_repo_role(
        role_path: str,
        *,
        style_readme_path: str | None = None,
        role_name_override: str | None = None,
    ) -> RunScanOutputPayload:
        return scan_role_fn(
            role_path,
            compare_role_path=compare_role_path,
            style_readme_path=style_readme_path or delegated_style_readme_path,
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
        )

    return resolve_repo_scan_facade_fn().run_repo_scan(
        repo_url=repo_url,
        repo_role_path=repo_role_path,
        repo_style_readme_path=repo_style_readme_path,
        style_readme_path=style_readme_path,
        repo_ref=repo_ref,
        repo_timeout=repo_timeout,
        lightweight_readme_only=lightweight_readme_only,
        scan_role_fn=_scan_repo_role,
    )


def __getattr__(name: str):
    """Lazy module attribute access for scanner_core and scanner_kernel re-exports."""
    if name == "build_run_scan_options_canonical":
        from prism.scanner_core.scan_request import build_run_scan_options_canonical

        return build_run_scan_options_canonical
    if name == "route_scan_payload_orchestration":
        from prism.scanner_kernel.orchestrator import route_scan_payload_orchestration

        return route_scan_payload_orchestration
    if name == "orchestrate_scan_payload_with_selected_plugin":
        from prism.scanner_kernel.orchestrator import (
            orchestrate_scan_payload_with_selected_plugin,
        )

        return orchestrate_scan_payload_with_selected_plugin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
