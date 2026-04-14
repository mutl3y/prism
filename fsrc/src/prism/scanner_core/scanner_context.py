"""Minimal scanner-context orchestrator for the fsrc package lane."""

from __future__ import annotations

from copy import deepcopy
import logging
from typing import Any, Callable

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
        self._build_run_scan_options_fn = (
            build_run_scan_options_fn or scan_request.build_run_scan_options_canonical
        )
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

        normalized_scan_options = self._build_run_scan_options_fn(
            role_path=str(self._scan_options.get("role_path") or self._role_path),
            role_name_override=self._scan_options.get("role_name_override"),
            readme_config_path=self._scan_options.get("readme_config_path"),
            include_vars_main=bool(self._scan_options.get("include_vars_main", True)),
            exclude_path_patterns=self._scan_options.get("exclude_path_patterns"),
            detailed_catalog=bool(self._scan_options.get("detailed_catalog", False)),
            include_task_parameters=bool(
                self._scan_options.get("include_task_parameters", True)
            ),
            include_task_runbooks=bool(
                self._scan_options.get("include_task_runbooks", True)
            ),
            inline_task_runbooks=bool(
                self._scan_options.get("inline_task_runbooks", True)
            ),
            include_collection_checks=bool(
                self._scan_options.get("include_collection_checks", True)
            ),
            keep_unknown_style_sections=bool(
                self._scan_options.get("keep_unknown_style_sections", True)
            ),
            adopt_heading_mode=self._scan_options.get("adopt_heading_mode"),
            vars_seed_paths=self._scan_options.get("vars_seed_paths"),
            style_readme_path=self._scan_options.get("style_readme_path"),
            style_source_path=self._scan_options.get("style_source_path"),
            style_guide_skeleton=bool(
                self._scan_options.get("style_guide_skeleton", False)
            ),
            compare_role_path=self._scan_options.get("compare_role_path"),
            fail_on_unconstrained_dynamic_includes=self._scan_options.get(
                "fail_on_unconstrained_dynamic_includes"
            ),
            fail_on_yaml_like_task_annotations=self._scan_options.get(
                "fail_on_yaml_like_task_annotations"
            ),
            ignore_unresolved_internal_underscore_references=self._scan_options.get(
                "ignore_unresolved_internal_underscore_references"
            ),
            policy_context=self._scan_options.get("policy_context"),
        )

        if self._prepare_scan_context_fn is None:
            raise ValueError(
                "prepare_scan_context_fn must be provided for canonical "
                "ScannerContext orchestration"
            )

        context_payload = self._prepare_scan_context_fn(normalized_scan_options)

        metadata = dict(context_payload.get("metadata") or {})
        if "features" not in metadata and self._detected_features:
            metadata["features"] = dict(self._detected_features)

        option_policy_warnings: list[dict[str, Any]] = []
        for warning_source in (
            self._scan_options.get("scan_policy_warnings"),
            normalized_scan_options.get("scan_policy_warnings"),
        ):
            if isinstance(warning_source, list):
                option_policy_warnings.extend(
                    warning for warning in warning_source if isinstance(warning, dict)
                )

        if option_policy_warnings:
            existing_policy_warnings = metadata.get("scan_policy_warnings")
            policy_warning_list = (
                list(existing_policy_warnings)
                if isinstance(existing_policy_warnings, list)
                else []
            )
            policy_warning_list.extend(option_policy_warnings)
            metadata["scan_policy_warnings"] = policy_warning_list

        display_variables = dict(context_payload.get("display_variables") or {})
        display_variables = self._apply_underscore_reference_policy(
            scan_options=normalized_scan_options,
            metadata=metadata,
            display_variables=display_variables,
        )

        self._enforce_failure_policies(
            scan_options=normalized_scan_options,
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
        policy_context = scan_options.get("policy_context")
        include_underscore = None
        if isinstance(policy_context, dict):
            raw_include_underscore = policy_context.get(
                "include_underscore_prefixed_references"
            )
            if isinstance(raw_include_underscore, bool):
                include_underscore = raw_include_underscore

        ignore_flag = bool(
            scan_options.get("ignore_unresolved_internal_underscore_references")
        )
        if include_underscore is not None:
            ignore_flag = not include_underscore

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
