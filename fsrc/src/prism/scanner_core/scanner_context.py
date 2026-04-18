"""Minimal scanner-context orchestrator for the fsrc package lane."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Callable, cast

from prism.errors import PrismRuntimeError
from prism.scanner_core import scan_request
from prism.scanner_data.contracts_request import ScanContextPayload, ScanOptionsDict
from prism.scanner_core.dynamic_include_audit import (
    collect_unconstrained_dynamic_role_includes,
)
from prism.scanner_core.dynamic_include_audit import (
    collect_unconstrained_dynamic_task_includes,
)

_REQUIRED_SCAN_OPTION_KEYS: set[str] = {
    "role_path",
    "role_name_override",
    "readme_config_path",
    "include_vars_main",
    "exclude_path_patterns",
    "detailed_catalog",
    "include_task_parameters",
    "include_task_runbooks",
    "inline_task_runbooks",
    "include_collection_checks",
    "keep_unknown_style_sections",
    "adopt_heading_mode",
    "vars_seed_paths",
    "style_readme_path",
    "style_source_path",
    "style_guide_skeleton",
    "compare_role_path",
    "fail_on_unconstrained_dynamic_includes",
    "fail_on_yaml_like_task_annotations",
    "ignore_unresolved_internal_underscore_references",
}

_RECOVERABLE_PHASE_ERRORS: tuple[type[Exception], ...] = (PrismRuntimeError,)
_TASK_LINE_REQUIRED_ATTRIBUTES: tuple[str, ...] = (
    "TASK_INCLUDE_KEYS",
    "ROLE_INCLUDE_KEYS",
    "INCLUDE_VARS_KEYS",
    "SET_FACT_KEYS",
    "TASK_BLOCK_KEYS",
    "TASK_META_KEYS",
)


def _validate_task_line_policy(policy: object) -> None:
    if not callable(getattr(policy, "detect_task_module", None)):
        raise ValueError(
            "prepared_policy_bundle.task_line_parsing must provide "
            "detect_task_module"
        )

    missing_attributes = [
        name
        for name in _TASK_LINE_REQUIRED_ATTRIBUTES
        if getattr(policy, name, None) is None
    ]
    if missing_attributes:
        raise ValueError(
            "prepared_policy_bundle.task_line_parsing is missing required "
            "attributes: " + ", ".join(missing_attributes)
        )


def _validate_jinja_analysis_policy(policy: object) -> None:
    if not callable(getattr(policy, "collect_undeclared_jinja_variables", None)):
        raise ValueError(
            "prepared_policy_bundle.jinja_analysis must provide "
            "collect_undeclared_jinja_variables"
        )


def _require_prepared_policy_bundle(
    scan_options: ScanOptionsDict,
) -> dict[str, Any]:
    prepared_policy_bundle = scan_options.get("prepared_policy_bundle")
    if not isinstance(prepared_policy_bundle, dict):
        raise ValueError(
            "scan_options must include a prepared_policy_bundle before "
            "ScannerContext orchestration"
        )

    task_line_policy = prepared_policy_bundle.get("task_line_parsing")
    if task_line_policy is None:
        raise ValueError(
            "prepared_policy_bundle.task_line_parsing must be provided before "
            "ScannerContext orchestration"
        )
    _validate_task_line_policy(task_line_policy)

    jinja_analysis_policy = prepared_policy_bundle.get("jinja_analysis")
    if jinja_analysis_policy is None:
        raise ValueError(
            "prepared_policy_bundle.jinja_analysis must be provided before "
            "ScannerContext orchestration"
        )
    _validate_jinja_analysis_policy(jinja_analysis_policy)

    return cast(dict[str, Any], prepared_policy_bundle)


def _copy_policy_warning_entries(raw_warnings: object) -> list[dict[str, Any]]:
    if not isinstance(raw_warnings, list):
        return []
    return [dict(warning) for warning in raw_warnings if isinstance(warning, dict)]


def _merge_policy_warning_entries(
    ingress_warnings: object,
    metadata_warnings: object,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for warning in _copy_policy_warning_entries(ingress_warnings):
        if warning not in merged:
            merged.append(warning)
    for warning in _copy_policy_warning_entries(metadata_warnings):
        if warning not in merged:
            merged.append(warning)
    return merged


@dataclass(frozen=True)
class NonCollectionRunScanExecutionRequest:
    """Canonical scanner_core execution request for the non-collection run_scan path."""

    role_path: str
    scan_options: ScanOptionsDict
    strict_mode: bool
    runtime_registry: Any
    scanner_context: ScannerContext
    build_payload_fn: Callable[[], dict[str, Any]]


def build_non_collection_run_scan_execution_request(
    *,
    role_path: str,
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
    validate_role_path_fn: Callable[[str], str],
    extract_role_description_fn: Callable[[Path, str], str],
    build_run_scan_options_canonical_fn: Callable[..., ScanOptionsDict],
    di_container_cls: Callable[..., Any],
    feature_detector_cls: Callable[..., Any],
    scanner_context_cls: Callable[..., ScannerContext],
    variable_discovery_cls: Callable[..., Any],
    resolve_comment_driven_documentation_plugin_fn: Callable[[Any], Any],
    default_plugin_registry: Any,
) -> NonCollectionRunScanExecutionRequest:
    """Build the scanner_core-owned execution request for non-collection run_scan."""
    validated_role_path = validate_role_path_fn(role_path)

    canonical_options = build_run_scan_options_canonical_fn(
        role_path=validated_role_path,
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
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        policy_context=policy_context,
    )
    canonical_options["strict_phase_failures"] = bool(strict_phase_failures)
    canonical_options["concise_readme"] = bool(concise_readme)
    canonical_options["scanner_report_output"] = scanner_report_output
    canonical_options["include_scanner_report_link"] = bool(include_scanner_report_link)
    if isinstance(scan_pipeline_plugin, str) and scan_pipeline_plugin.strip():
        canonical_options["scan_pipeline_plugin"] = scan_pipeline_plugin.strip()

    scan_state: dict[str, Any] = {
        "discovered_rows": tuple(),
        "features": {},
    }

    def _variable_discovery_factory(
        di: Any,
        resolved_role_path: str,
        options: dict[str, Any],
    ) -> Any:
        discovery = variable_discovery_cls(di, resolved_role_path, options)

        class _RecordingVariableDiscovery:
            def discover(self) -> tuple[dict[str, Any], ...]:
                rows = tuple(discovery.discover())
                scan_state["discovered_rows"] = rows
                return rows

        return _RecordingVariableDiscovery()

    def _feature_detector_factory(
        di: Any,
        resolved_role_path: str,
        options: dict[str, Any],
    ) -> Any:
        detector = feature_detector_cls(di, resolved_role_path, options)

        class _RecordingFeatureDetector:
            def detect(self) -> dict[str, Any]:
                features = dict(detector.detect())
                scan_state["features"] = features
                return features

        return _RecordingFeatureDetector()

    def _prepare_scan_context_fn(scan_options: ScanOptionsDict) -> ScanContextPayload:
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
            "description": extract_role_description_fn(role_root, role_name),
            "requirements_display": requirements_display,
            "undocumented_default_filters": [],
            "display_variables": display_variables,
            "metadata": {
                "features": features,
                "variable_insights": [dict(row) for row in rows],
                "yaml_parse_failures": normalized_yaml_parse_failures,
                "role_notes": resolve_comment_driven_documentation_plugin_fn(
                    container
                ).extract_role_notes_from_comments(
                    resolved_role_path,
                    exclude_paths=scan_options.get("exclude_path_patterns"),
                ),
            },
        }

    container = di_container_cls(
        role_path=str(canonical_options["role_path"]),
        scan_options=canonical_options,
        scanner_context_wiring={
            "scanner_context_cls": scanner_context_cls,
            "prepare_scan_context_fn": _prepare_scan_context_fn,
            "build_run_scan_options_fn": build_run_scan_options_canonical_fn,
        },
        factory_overrides={
            "variable_discovery_factory": _variable_discovery_factory,
            "feature_detector_factory": _feature_detector_factory,
        },
    )
    scan_request.ensure_prepared_policy_bundle(
        scan_options=cast(dict[str, Any], canonical_options),
        di=container,
    )
    scanner_context = container.factory_scanner_context()
    strict_mode = bool(canonical_options.get("strict_phase_failures", True))
    runtime_registry = (
        canonical_options.get("plugin_registry") or default_plugin_registry
    )

    return NonCollectionRunScanExecutionRequest(
        role_path=str(canonical_options["role_path"]),
        scan_options=canonical_options,
        strict_mode=strict_mode,
        runtime_registry=runtime_registry,
        scanner_context=scanner_context,
        build_payload_fn=scanner_context.orchestrate_scan,
    )


class ScannerContext:
    """Coordinate variable discovery, feature detection, and payload shaping."""

    def __init__(
        self,
        *,
        di: Any,
        role_path: str,
        scan_options: ScanOptionsDict,
        build_run_scan_options_fn: Callable[..., ScanOptionsDict] | None = None,
        prepare_scan_context_fn: (
            Callable[[ScanOptionsDict], ScanContextPayload] | None
        ) = None,
    ) -> None:
        if di is None:
            raise ValueError("di (DIContainer) must not be None")
        if not role_path:
            raise ValueError("role_path must not be empty")
        if scan_options is None:
            raise ValueError("scan_options must not be None")

        self._di = di
        self._role_path = role_path
        self._scan_options = scan_options
        self._prepare_scan_context_fn = prepare_scan_context_fn
        self._strict_phase_failures = bool(
            self._scan_options.get("strict_phase_failures", True)
        )

        self._discovered_variables: tuple[Any, ...] = ()
        self._detected_features: dict[str, Any] = {}
        self._scan_metadata: dict[str, Any] = {}
        self._scan_errors: list[dict[str, str]] = []

    def orchestrate_scan(self) -> dict[str, Any]:
        self._discovered_variables = ()
        self._detected_features = {}
        self._scan_metadata = {}
        self._scan_errors = []

        _require_prepared_policy_bundle(self._scan_options)

        self._discovered_variables = self._discover_variables()
        self._detected_features = self._detect_features()

        return self._build_output_payload()

    def _record_phase_error(self, phase: str, error: Exception) -> dict[str, str]:
        entry = {
            "phase": phase,
            "error_type": error.__class__.__name__,
            "message": str(error),
        }
        self._scan_errors.append(entry)
        self._scan_metadata = {
            "scan_errors": list(self._scan_errors),
            "scan_degraded": True,
        }
        return entry

    def _discover_variables(self) -> tuple[Any, ...]:
        try:
            discovery = self._di.factory_variable_discovery()
            return discovery.discover()
        except Exception as error:
            logger = logging.getLogger(__name__)
            if self._strict_phase_failures or not isinstance(
                error,
                _RECOVERABLE_PHASE_ERRORS,
            ):
                logger.error("Variable discovery failed")
                raise
            entry = self._record_phase_error("discovery", error)
            logger.error(
                "Variable discovery failed; continuing in best-effort mode",
                extra={"scan_error": entry},
            )
            return ()

    def _detect_features(self) -> dict[str, Any]:
        try:
            detector = self._di.factory_feature_detector()
            return detector.detect()
        except Exception as error:
            logger = logging.getLogger(__name__)
            if self._strict_phase_failures or not isinstance(
                error,
                _RECOVERABLE_PHASE_ERRORS,
            ):
                logger.error("Feature detection failed")
                raise
            entry = self._record_phase_error("feature_detection", error)
            logger.error(
                "Feature detection failed; continuing in best-effort mode",
                extra={"scan_error": entry},
            )
            return {"task_files_scanned": 0, "tasks_scanned": 0}

    def _build_output_payload(self) -> dict[str, Any]:
        missing_keys = sorted(
            key for key in _REQUIRED_SCAN_OPTION_KEYS if key not in self._scan_options
        )
        if missing_keys:
            raise ValueError(
                "scan_options missing required canonical keys: "
                + ", ".join(missing_keys)
            )

        if self._prepare_scan_context_fn is None:
            raise ValueError(
                "prepare_scan_context_fn must be provided for canonical "
                "ScannerContext orchestration"
            )

        context_payload = self._prepare_scan_context_fn(self._scan_options)

        metadata = dict(context_payload.get("metadata") or {})
        if "features" not in metadata and self._detected_features:
            metadata["features"] = dict(self._detected_features)

        policy_warning_list = _merge_policy_warning_entries(
            self._scan_options.get("scan_policy_warnings"),
            metadata.get("scan_policy_warnings"),
        )
        if policy_warning_list:
            metadata["scan_policy_warnings"] = policy_warning_list

        display_variables = dict(context_payload.get("display_variables") or {})
        display_variables = self._apply_underscore_reference_policy(
            scan_options=self._scan_options,
            metadata=metadata,
            display_variables=display_variables,
        )

        self._enforce_failure_policies(
            scan_options=self._scan_options,
            metadata=metadata,
        )

        if self._scan_errors:
            metadata["scan_errors"] = list(self._scan_errors)
            metadata["scan_degraded"] = True
        self._scan_metadata = metadata

        return {
            "role_name": context_payload["role_name"],
            "description": context_payload["description"],
            "display_variables": display_variables,
            "requirements_display": list(context_payload["requirements_display"]),
            "undocumented_default_filters": list(
                context_payload["undocumented_default_filters"]
            ),
            "metadata": metadata,
        }

    def _append_policy_warning(
        self,
        metadata: dict[str, Any],
        *,
        code: str,
        message: str,
        detail: dict[str, Any],
    ) -> None:
        warnings = metadata.get("scan_policy_warnings")
        warning_list = list(warnings) if isinstance(warnings, list) else []
        warning_list.append({"code": code, "message": message, "detail": detail})
        metadata["scan_policy_warnings"] = warning_list

    def _enforce_failure_policies(
        self,
        *,
        scan_options: ScanOptionsDict,
        metadata: dict[str, Any],
    ) -> None:
        features = metadata.get("features")
        feature_map = dict(features) if isinstance(features, dict) else {}

        if bool(scan_options.get("fail_on_unconstrained_dynamic_includes")):
            dynamic_task_includes = collect_unconstrained_dynamic_task_includes(
                str(scan_options["role_path"]),
                exclude_paths=scan_options.get("exclude_path_patterns"),
                di=self._di,
            )
            dynamic_role_includes = collect_unconstrained_dynamic_role_includes(
                str(scan_options["role_path"]),
                exclude_paths=scan_options.get("exclude_path_patterns"),
                di=self._di,
            )
            dynamic_task_count = len(dynamic_task_includes)
            dynamic_role_count = len(dynamic_role_includes)
            dynamic_total = dynamic_task_count + dynamic_role_count
            if dynamic_total > 0:
                detail = {
                    "dynamic_task_includes": dynamic_task_count,
                    "dynamic_role_includes": dynamic_role_count,
                }
                if self._strict_phase_failures:
                    raise PrismRuntimeError(
                        code="unconstrained_dynamic_includes_detected",
                        category="runtime",
                        message="Scan policy failure: unconstrained dynamic include targets were detected.",
                        detail=detail,
                    )
                self._append_policy_warning(
                    metadata,
                    code="unconstrained_dynamic_includes_detected",
                    message="Scan policy warning: unconstrained dynamic include targets were detected.",
                    detail=detail,
                )

        yaml_like_count = int(feature_map.get("yaml_like_task_annotations") or 0)
        if (
            bool(scan_options.get("fail_on_yaml_like_task_annotations"))
            and yaml_like_count > 0
        ):
            detail = {"yaml_like_task_annotations": yaml_like_count}
            if self._strict_phase_failures:
                raise PrismRuntimeError(
                    code="yaml_like_task_annotations_detected",
                    category="runtime",
                    message="Scan policy failure: yaml-like task annotations were detected.",
                    detail=detail,
                )
            self._append_policy_warning(
                metadata,
                code="yaml_like_task_annotations_detected",
                message="Scan policy warning: yaml-like task annotations were detected.",
                detail=detail,
            )

    def _apply_underscore_reference_policy(
        self,
        *,
        scan_options: ScanOptionsDict,
        metadata: dict[str, Any],
        display_variables: dict[str, Any],
    ) -> dict[str, Any]:
        ignore_flag = bool(
            scan_options.get("ignore_unresolved_internal_underscore_references")
        )

        if not ignore_flag:
            return display_variables

        metadata["ignore_unresolved_internal_underscore_references"] = True

        filtered = {
            name: data
            for name, data in display_variables.items()
            if not (
                isinstance(name, str)
                and name.startswith("_")
                and isinstance(data, dict)
                and bool(data.get("is_unresolved"))
            )
        }

        filtered_count = len(display_variables) - len(filtered)
        if filtered_count > 0:
            metadata["underscore_filtered_unresolved_count"] = filtered_count
            insights = metadata.get("variable_insights")
            if isinstance(insights, list):
                metadata["variable_insights"] = [
                    row
                    for row in insights
                    if not (
                        isinstance(row, dict)
                        and isinstance(row.get("name"), str)
                        and str(row.get("name")).startswith("_")
                        and bool(row.get("is_unresolved"))
                    )
                ]

        return filtered

    @property
    def discovered_variables(self) -> tuple[Any, ...]:
        return self._discovered_variables

    @property
    def detected_features(self) -> dict[str, Any]:
        return deepcopy(self._detected_features)

    @property
    def scan_metadata(self) -> dict[str, Any]:
        return deepcopy(self._scan_metadata)
