"""Minimal scanner-context orchestrator for the fsrc package lane."""

from __future__ import annotations

from copy import deepcopy
import logging
from typing import Any, Callable

from prism.errors import PrismRuntimeError
from prism.scanner_core import scan_request
from prism.scanner_data.contracts_request import ScanContextPayload, ScanOptionsDict

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
        if self._scan_errors:
            metadata["scan_errors"] = list(self._scan_errors)
            metadata["scan_degraded"] = True
        self._scan_metadata = metadata

        return {
            "role_name": context_payload["role_name"],
            "description": context_payload["description"],
            "display_variables": dict(context_payload.get("display_variables") or {}),
            "requirements_display": list(context_payload["requirements_display"]),
            "undocumented_default_filters": list(
                context_payload["undocumented_default_filters"]
            ),
            "metadata": metadata,
        }

    @property
    def discovered_variables(self) -> tuple[Any, ...]:
        return self._discovered_variables

    @property
    def detected_features(self) -> dict[str, Any]:
        return deepcopy(self._detected_features)

    @property
    def scan_metadata(self) -> dict[str, Any]:
        return deepcopy(self._scan_metadata)
