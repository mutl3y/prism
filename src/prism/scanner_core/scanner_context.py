"""Minimal scanner-context orchestrator for the fsrc package lane."""

from __future__ import annotations

import copy
import logging
from collections.abc import Collection, Mapping
from typing import Any, Callable, TypeGuard, cast

from prism.errors import PrismRuntimeError
from prism.scanner_core.di import DIContainer
from prism.scanner_core.metadata_merger import merge_policy_warning_entries
from prism.scanner_data.contracts_request import (
    DisplayVariables,
    FeaturesContext,
    PreparedPolicyBundle,
    PreparedJinjaAnalysisPolicy,
    PreparedTaskLineParsingPolicy,
    RequirementsDisplayEntry,
    ScanContextPayload,
    ScanErrorEntry,
    ScanMetadata,
    ScanOptionsDict,
    ScanPolicyBlockerFacts,
    resolve_strict_phase_failures,
)
from prism.scanner_core.execution_request_builder import (
    NonCollectionRunScanExecutionRequest,
    build_non_collection_run_scan_execution_request,
)
from prism.scanner_core.filters.underscore_policy import (
    apply_underscore_reference_filter,
)

_REQUIRED_SCAN_OPTION_KEYS: frozenset[str] = frozenset(
    {
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
)

_RECOVERABLE_PHASE_ERRORS: tuple[type[Exception], ...] = (PrismRuntimeError,)


def _is_scan_metadata(value: object) -> TypeGuard[ScanMetadata]:
    return isinstance(value, dict)


def _copy_scan_metadata(metadata: object) -> ScanMetadata:
    """Preserve the ScanMetadata TypedDict contract across shallow copies."""
    if not _is_scan_metadata(metadata):
        raise ValueError(
            "prepare_scan_context metadata must be a dict before ScannerContext orchestration"
        )

    copied_metadata = ScanMetadata(**metadata)
    role_notes = copied_metadata.get("role_notes")
    if role_notes is not None:
        _validate_role_notes(role_notes)

    yaml_parse_failures = copied_metadata.get("yaml_parse_failures")
    if yaml_parse_failures is not None:
        _validate_yaml_parse_failures(yaml_parse_failures)

    return copied_metadata


def _copy_features_metadata(features: FeaturesContext) -> dict[str, object]:
    """Project feature facts into metadata without mutating detector-owned state."""
    return {key: value for key, value in features.items()}


def _copy_display_variables(display_variables: object) -> DisplayVariables:
    if not isinstance(display_variables, dict):
        raise ValueError(
            "prepare_scan_context display_variables must be a dict before ScannerContext orchestration"
        )

    copied_display_variables = copy.copy(display_variables)
    for variable_name, entry in copied_display_variables.items():
        if not isinstance(variable_name, str) or not variable_name:
            raise ValueError(
                "prepare_scan_context display_variables keys must be non-empty strings"
            )
        if not isinstance(entry, dict):
            raise ValueError(
                f"prepare_scan_context display_variables.{variable_name} must be a dict"
            )
    return copied_display_variables


def _validate_role_notes(role_notes: object) -> None:
    if not isinstance(role_notes, dict):
        raise ValueError(
            "prepare_scan_context metadata.role_notes must be a dict[str, list[str]]"
        )
    for bucket in ("warnings", "deprecations", "notes", "additionals"):
        bucket_value = role_notes.get(bucket)
        if not isinstance(bucket_value, list) or any(
            not isinstance(item, str) for item in bucket_value
        ):
            raise ValueError(
                f"prepare_scan_context metadata.role_notes.{bucket} must be a list[str]"
            )


def _validate_yaml_parse_failures(yaml_parse_failures: object) -> None:
    if not isinstance(yaml_parse_failures, list):
        raise ValueError(
            "prepare_scan_context metadata.yaml_parse_failures must be a list"
        )
    for index, row in enumerate(yaml_parse_failures):
        if not isinstance(row, dict):
            raise ValueError(
                f"prepare_scan_context metadata.yaml_parse_failures[{index}] must be a dict"
            )
        if not isinstance(row.get("file"), str) or not isinstance(
            row.get("error"), str
        ):
            raise ValueError(
                f"prepare_scan_context metadata.yaml_parse_failures[{index}] must include string file and error fields"
            )
        line = row.get("line")
        column = row.get("column")
        if line is not None and not isinstance(line, int):
            raise ValueError(
                f"prepare_scan_context metadata.yaml_parse_failures[{index}].line must be int | None"
            )
        if column is not None and not isinstance(column, int):
            raise ValueError(
                f"prepare_scan_context metadata.yaml_parse_failures[{index}].column must be int | None"
            )


def _copy_requirements_display(
    requirements_display: object,
) -> list[RequirementsDisplayEntry]:
    if not isinstance(requirements_display, list):
        raise ValueError(
            "prepare_scan_context requirements_display must be a list before ScannerContext orchestration"
        )

    copied_requirements_display: list[RequirementsDisplayEntry] = []
    for index, entry in enumerate(requirements_display):
        if not isinstance(entry, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in entry.items()
        ):
            raise ValueError(
                f"prepare_scan_context requirements_display[{index}] must be a dict[str, str]"
            )
        copied_requirements_display.append(
            cast(RequirementsDisplayEntry, copy.copy(entry))
        )
    return copied_requirements_display


def _is_prepared_policy_bundle(value: object) -> TypeGuard[PreparedPolicyBundle]:
    return isinstance(value, dict)


def _is_string_collection(value: object) -> bool:
    return (
        isinstance(value, Collection)
        and not isinstance(value, (Mapping, str, bytes))
        and all(isinstance(item, str) for item in value)
    )


def _has_prepared_task_line_policy_shape(
    value: object,
) -> TypeGuard[PreparedTaskLineParsingPolicy]:
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


def _has_prepared_jinja_analysis_policy_shape(
    value: object,
) -> TypeGuard[PreparedJinjaAnalysisPolicy]:
    if isinstance(value, Mapping):
        return False
    return callable(getattr(value, "collect_undeclared_jinja_variables", None))


def _require_prepared_policy_bundle(
    scan_options: ScanOptionsDict,
) -> PreparedPolicyBundle:
    prepared_policy_bundle = scan_options.get("prepared_policy_bundle")
    if not _is_prepared_policy_bundle(prepared_policy_bundle):
        raise ValueError(
            "scan_options must include a prepared_policy_bundle before "
            "ScannerContext orchestration"
        )

    task_line_policy = prepared_policy_bundle.get("task_line_parsing")
    if not _has_prepared_task_line_policy_shape(task_line_policy):
        raise ValueError(
            "prepared_policy_bundle.task_line_parsing must provide canonical "
            "task-line policy members before ScannerContext orchestration"
        )

    jinja_analysis_policy = prepared_policy_bundle.get("jinja_analysis")
    if not _has_prepared_jinja_analysis_policy_shape(jinja_analysis_policy):
        raise ValueError(
            "prepared_policy_bundle.jinja_analysis must provide canonical "
            "Jinja analysis members before ScannerContext orchestration"
        )

    return prepared_policy_bundle


def _build_empty_features_context() -> FeaturesContext:
    """Initialize an empty FeaturesContext with all required keys."""
    return FeaturesContext(
        task_files_scanned=0,
        tasks_scanned=0,
        recursive_task_includes=0,
        unique_modules="",
        external_collections="",
        handlers_notified="",
        privileged_tasks=0,
        conditional_tasks=0,
        tagged_tasks=0,
        included_role_calls=0,
        included_roles="",
        dynamic_included_role_calls=0,
        dynamic_included_roles="",
        disabled_task_annotations=0,
        yaml_like_task_annotations=0,
    )


__all__ = [
    "NonCollectionRunScanExecutionRequest",
    "ScannerContext",
    "build_non_collection_run_scan_execution_request",
]


class ScannerContext:
    """Coordinate variable discovery, feature detection, and payload shaping."""

    def __init__(
        self,
        *,
        di: DIContainer,
        role_path: str,
        scan_options: ScanOptionsDict,
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
        self._strict_phase_failures = resolve_strict_phase_failures(self._scan_options)

        self._discovered_variables: tuple[Any, ...] = ()
        self._detected_features: FeaturesContext = _build_empty_features_context()
        self._scan_metadata: ScanMetadata = ScanMetadata()
        self._scan_errors: list[ScanErrorEntry] = []

    def orchestrate_scan(self) -> dict[str, Any]:
        self._discovered_variables = ()
        self._detected_features = _build_empty_features_context()
        self._scan_metadata = ScanMetadata()
        self._scan_errors = []

        _require_prepared_policy_bundle(self._scan_options)

        self._discovered_variables = self._discover_variables()
        self._detected_features = self._detect_features()

        return self._build_output_payload()

    def _record_phase_error(self, phase: str, error: Exception) -> ScanErrorEntry:
        entry: ScanErrorEntry = {
            "phase": phase,
            "error_type": error.__class__.__name__,
            "message": str(error),
        }
        self._scan_errors.append(entry)
        self._scan_metadata = ScanMetadata(
            scan_errors=list(self._scan_errors),
            scan_degraded=True,
        )
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

    def _detect_features(self) -> FeaturesContext:
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
            return _build_empty_features_context()

    def _build_output_payload(self) -> dict[str, object]:
        self._validate_required_scan_option_keys()
        context_payload = self._build_context_payload()
        metadata = _copy_scan_metadata(context_payload.get("metadata"))
        self._merge_features_into_metadata(metadata)
        self._merge_policy_warnings_into_metadata(metadata)
        display_variables = self._apply_underscore_reference_policy(
            scan_options=self._scan_options,
            metadata=metadata,
            display_variables=_copy_display_variables(
                context_payload.get("display_variables")
            ),
        )
        metadata["scan_policy_blocker_facts"] = self._build_scan_policy_blocker_facts(
            scan_options=self._scan_options,
            metadata=metadata,
        )
        self._record_scan_errors_into_metadata(metadata)
        self._scan_metadata = metadata

        return {
            "role_name": context_payload["role_name"],
            "description": context_payload["description"],
            "display_variables": display_variables,
            "requirements_display": _copy_requirements_display(
                context_payload["requirements_display"]
            ),
            "undocumented_default_filters": list(
                context_payload["undocumented_default_filters"]
            ),
            "metadata": metadata,
        }

    def _validate_required_scan_option_keys(self) -> None:
        missing_keys = sorted(
            key for key in _REQUIRED_SCAN_OPTION_KEYS if key not in self._scan_options
        )
        if missing_keys:
            raise ValueError(
                "scan_options missing required canonical keys: "
                + ", ".join(missing_keys)
            )

    def _build_context_payload(self) -> ScanContextPayload:
        if self._prepare_scan_context_fn is None:
            raise ValueError(
                "prepare_scan_context_fn must be provided for canonical "
                "ScannerContext orchestration"
            )
        return self._prepare_scan_context_fn(self._scan_options)

    def _merge_features_into_metadata(self, metadata: ScanMetadata) -> None:
        if "features" not in metadata and self._detected_features:
            metadata["features"] = _copy_features_metadata(self._detected_features)

    def _merge_policy_warnings_into_metadata(self, metadata: ScanMetadata) -> None:
        policy_warning_list = merge_policy_warning_entries(
            self._scan_options.get("scan_policy_warnings"),
            metadata.get("scan_policy_warnings"),
        )
        if policy_warning_list:
            metadata["scan_policy_warnings"] = policy_warning_list

    def _record_scan_errors_into_metadata(self, metadata: ScanMetadata) -> None:
        if self._scan_errors:
            metadata["scan_errors"] = list(self._scan_errors)
            metadata["scan_degraded"] = True

    def _build_scan_policy_blocker_facts(
        self,
        *,
        scan_options: ScanOptionsDict,
        metadata: ScanMetadata,
    ) -> ScanPolicyBlockerFacts:
        builder_fn = self._di.factory_blocker_fact_builder()
        return builder_fn(
            scan_options=scan_options,
            metadata=metadata,
            di=self._di,
        )

    def _apply_underscore_reference_policy(
        self,
        *,
        scan_options: ScanOptionsDict,
        metadata: ScanMetadata,
        display_variables: DisplayVariables,
    ) -> DisplayVariables:
        return apply_underscore_reference_filter(
            display_variables=display_variables,
            metadata=metadata,
            ignore_flag=bool(
                scan_options.get("ignore_unresolved_internal_underscore_references")
            ),
        )

    @property
    def discovered_variables(self) -> tuple[Any, ...]:
        return self._discovered_variables

    @property
    def detected_features(self) -> FeaturesContext:
        return copy.deepcopy(self._detected_features)

    @property
    def scan_metadata(self) -> ScanMetadata:
        return copy.deepcopy(self._scan_metadata)
