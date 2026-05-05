"""Execution request builder for the non-collection scan path."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Protocol, cast

from prism.scanner_data import VariableRow
from prism.scanner_core.di import resolve_platform_key
from prism.scanner_data.contracts_output import RunScanOutputPayload
from prism.scanner_data.contracts_request import (
    DisplayVariableEntry,
    FeaturesContext,
    RequirementsDisplayEntry,
    RoleNotes,
    ScanContextPayload,
    ScanOptionsDict,
    VariableInsight,
    YamlParseFailure,
    require_strict_phase_failures,
    resolve_strict_phase_failures,
)

if TYPE_CHECKING:
    from prism.scanner_core.di import DIContainer
    from prism.scanner_core.scanner_context import ScannerContext
    from prism.scanner_core.protocols_runtime import ScanPayloadBuilderFn
    from prism.scanner_plugins.interfaces import CommentDrivenDocumentationPlugin
    from prism.scanner_plugins.interfaces import ScanPipelineRuntimeRegistry


class _VariableDiscoveryRunner(Protocol):
    """Minimal variable-discovery surface needed during request assembly."""

    def discover(self) -> tuple[VariableRow, ...]: ...


class _FeatureDetectorRunner(Protocol):
    """Minimal feature-detection surface needed during request assembly."""

    def detect(self) -> FeaturesContext: ...


class _VariableDiscoveryFactory(Protocol):
    """Factory contract for building the variable-discovery participant."""

    def __call__(
        self,
        di: "DIContainer",
        role_path: str,
        scan_options: ScanOptionsDict,
    ) -> _VariableDiscoveryRunner: ...


class _FeatureDetectorFactory(Protocol):
    """Factory contract for building the feature-detector participant."""

    def __call__(
        self,
        di: "DIContainer",
        role_path: str,
        scan_options: ScanOptionsDict,
    ) -> _FeatureDetectorRunner: ...


class _EnsurePreparedPolicyBundleFn(Protocol):
    """Ingress policy-bundle contract used by request assembly."""

    def __call__(self, *, scan_options: ScanOptionsDict, di: object) -> None: ...


def _resolve_runtime_platform_key(
    scan_options: ScanOptionsDict,
    registry: "ScanPipelineRuntimeRegistry" | None = None,
) -> str:
    """Resolve the runtime platform key through the canonical DI selector order."""
    return resolve_platform_key(scan_options, registry)


class _DIContainerFactory(Protocol):
    """Factory contract for the execution-request DI container."""

    def __call__(
        self,
        role_path: str,
        scan_options: ScanOptionsDict,
        *,
        registry: "ScanPipelineRuntimeRegistry",
        platform_key: str,
        scanner_context_wiring: dict[str, object],
        factory_overrides: dict[str, object],
        inherit_default_event_listeners: bool,
    ) -> "DIContainer": ...


@dataclass(frozen=True)
class NonCollectionRunScanExecutionRequest:
    """Canonical scanner_core execution request for the non-collection run_scan path."""

    role_path: str
    scan_options: ScanOptionsDict
    strict_mode: bool
    runtime_registry: "ScanPipelineRuntimeRegistry"
    scanner_context: ScannerContext
    build_payload_fn: ScanPayloadBuilderFn


@dataclass(frozen=True)
class _RuntimeAssembly:
    """Concrete runtime participants needed before request finalization."""

    runtime_registry: "ScanPipelineRuntimeRegistry"
    container: DIContainer


class _RecordingVariableDiscovery:
    """Records discovered variable rows for use in scan context preparation."""

    def __init__(
        self,
        inner: _VariableDiscoveryRunner,
        bridge: "_ScanStateBridge",
    ) -> None:
        self._inner = inner
        self._bridge = bridge

    def discover(self) -> tuple[VariableRow, ...]:
        rows = tuple(self._inner.discover())
        self._bridge._discovered_rows = rows
        return rows


class _RecordingFeatureDetector:
    """Records detected features for use in scan context preparation."""

    def __init__(
        self,
        inner: _FeatureDetectorRunner,
        bridge: "_ScanStateBridge",
    ) -> None:
        self._inner = inner
        self._bridge = bridge

    def detect(self) -> FeaturesContext:
        features = copy.copy(self._inner.detect())
        self._bridge._features = features
        return features


class _ScanStateBridge:
    """Bridge mutable scan state between recording wrappers and context preparation.

    Invariant: Factory callables must produce valid discovery/detection instances.
    On factory failure, raises ValueError with explicit context to prevent silent corruption.
    """

    def __init__(
        self,
        *,
        container: object,
        variable_discovery_cls: _VariableDiscoveryFactory,
        feature_detector_cls: _FeatureDetectorFactory,
        extract_role_description_fn: Callable[[Path, str], str],
        resolve_comment_driven_documentation_plugin_fn: Callable[
            [object], "CommentDrivenDocumentationPlugin"
        ],
    ) -> None:
        self._discovered_rows: tuple[VariableRow, ...] = ()
        self._features: FeaturesContext | None = None
        self._variable_discovery_cls = variable_discovery_cls
        self._feature_detector_cls = feature_detector_cls
        self._extract_role_description_fn = extract_role_description_fn
        self._resolve_cdd_plugin_fn = resolve_comment_driven_documentation_plugin_fn
        self._container = container

    def variable_discovery_factory(
        self,
        di: DIContainer,
        resolved_role_path: str,
        options: ScanOptionsDict,
    ) -> _RecordingVariableDiscovery:
        try:
            inner = self._variable_discovery_cls(di, resolved_role_path, options)
        except Exception as exc:
            raise ValueError(
                f"Variable discovery factory failed for role_path={resolved_role_path}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        return _RecordingVariableDiscovery(inner, self)

    def feature_detector_factory(
        self,
        di: DIContainer,
        resolved_role_path: str,
        options: ScanOptionsDict,
    ) -> _RecordingFeatureDetector:
        try:
            inner = self._feature_detector_cls(di, resolved_role_path, options)
        except Exception as exc:
            raise ValueError(
                f"Feature detector factory failed for role_path={resolved_role_path}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        return _RecordingFeatureDetector(inner, self)

    def prepare_scan_context(
        self,
        scan_options: ScanOptionsDict,
        canonical_options: ScanOptionsDict,
    ) -> ScanContextPayload:
        resolved_role_path = str(scan_options["role_path"])
        role_root = Path(resolved_role_path).resolve()
        role_name = str(scan_options.get("role_name_override") or role_root.name)
        rows = self._discovered_rows
        features_metadata = self._features_metadata()

        display_variables = self._build_display_variables(rows)
        requirements_display = self._build_requirements_display(features_metadata)

        yaml_parse_failures = canonical_options.get("yaml_parse_failures")
        normalized = self._copy_yaml_parse_failures(yaml_parse_failures)

        return {
            "rp": resolved_role_path,
            "role_name": role_name,
            "description": self._extract_role_description_fn(role_root, role_name),
            "requirements_display": requirements_display,
            "undocumented_default_filters": [],
            "display_variables": display_variables,
            "metadata": {
                "features": features_metadata,
                "variable_insights": self._build_variable_insights(rows),
                "yaml_parse_failures": normalized,
                "role_notes": self._normalize_role_notes(
                    self._resolve_cdd_plugin_fn(
                        self._container
                    ).extract_role_notes_from_comments(
                        resolved_role_path,
                        exclude_paths=scan_options.get("exclude_path_patterns"),
                    )
                ),
            },
        }

    def _features_metadata(self) -> dict[str, object]:
        if self._features is None:
            return {}
        return cast(dict[str, object], copy.copy(self._features))

    @staticmethod
    def _normalize_role_notes(raw_role_notes: object) -> RoleNotes:
        if not isinstance(raw_role_notes, dict):
            raise ValueError("role_notes must be a dict[str, list[str]]")

        warnings = _ScanStateBridge._require_role_note_bucket(
            raw_role_notes, bucket="warnings"
        )
        deprecations = _ScanStateBridge._require_role_note_bucket(
            raw_role_notes, bucket="deprecations"
        )
        notes = _ScanStateBridge._require_role_note_bucket(
            raw_role_notes, bucket="notes"
        )
        additionals = _ScanStateBridge._require_role_note_bucket(
            raw_role_notes, bucket="additionals"
        )
        return {
            "warnings": warnings,
            "deprecations": deprecations,
            "notes": notes,
            "additionals": additionals,
        }

    @staticmethod
    def _require_role_note_bucket(
        raw_role_notes: dict[object, object], *, bucket: str
    ) -> list[str]:
        bucket_value = raw_role_notes.get(bucket)
        if not isinstance(bucket_value, list) or any(
            not isinstance(item, str) for item in bucket_value
        ):
            raise ValueError(
                f"role_notes.{bucket} must be a list[str] before ScannerContext handoff"
            )
        return list(bucket_value)

    @staticmethod
    def _require_row_name(row: VariableRow) -> str:
        raw_name = row.get("name")
        if not isinstance(raw_name, str) or not raw_name:
            raise ValueError(
                "display_variables rows must include a non-empty string name before ScannerContext handoff"
            )
        return raw_name

    @staticmethod
    def _require_bool_row_field(
        row: VariableRow,
        *,
        field_name: str,
        default: bool,
        row_name: str,
    ) -> bool:
        raw_value = row.get(field_name)
        if raw_value is None:
            return default
        if not isinstance(raw_value, bool):
            raise ValueError(
                f"display_variables.{row_name}.{field_name} must be a bool before ScannerContext handoff"
            )
        return raw_value

    @staticmethod
    def _require_optional_str_row_field(
        row: VariableRow,
        *,
        field_name: str,
        row_name: str,
    ) -> str | None:
        raw_value = row.get(field_name)
        if raw_value is None:
            return None
        if not isinstance(raw_value, str):
            raise ValueError(
                f"display_variables.{row_name}.{field_name} must be a string or None before ScannerContext handoff"
            )
        return raw_value

    @staticmethod
    def _require_provenance_confidence(
        row: VariableRow,
        *,
        row_name: str,
    ) -> float:
        raw_value = row.get("provenance_confidence")
        if raw_value is None:
            return 0.0
        if not isinstance(raw_value, (int, float)):
            raise ValueError(
                f"display_variables.{row_name}.provenance_confidence must be numeric before ScannerContext handoff"
            )
        return float(raw_value)

    @classmethod
    def _build_display_variable_entry(
        cls,
        row: VariableRow,
    ) -> tuple[str, DisplayVariableEntry]:
        row_name = cls._require_row_name(row)
        source = row.get("source")
        if source is not None and not isinstance(source, str):
            raise ValueError(
                f"display_variables.{row_name}.source must be a string or None before ScannerContext handoff"
            )
        entry: DisplayVariableEntry = {
            "type": row.get("type"),
            "default": row.get("default"),
            "source": source,
            "required": cls._require_bool_row_field(
                row,
                field_name="required",
                default=False,
                row_name=row_name,
            ),
            "documented": cls._require_bool_row_field(
                row,
                field_name="documented",
                default=False,
                row_name=row_name,
            ),
            "secret": cls._require_bool_row_field(
                row,
                field_name="secret",
                default=False,
                row_name=row_name,
            ),
            "is_unresolved": cls._require_bool_row_field(
                row,
                field_name="is_unresolved",
                default=False,
                row_name=row_name,
            ),
            "is_ambiguous": cls._require_bool_row_field(
                row,
                field_name="is_ambiguous",
                default=False,
                row_name=row_name,
            ),
            "uncertainty_reason": cls._require_optional_str_row_field(
                row,
                field_name="uncertainty_reason",
                row_name=row_name,
            ),
        }
        return row_name, entry

    @staticmethod
    def _copy_yaml_parse_failures(raw_failures: object) -> list[YamlParseFailure]:
        if raw_failures is None:
            return []
        if not isinstance(raw_failures, list):
            raise ValueError(
                "metadata.yaml_parse_failures must be a list[YamlParseFailure] before ScannerContext handoff"
            )

        normalized: list[YamlParseFailure] = []
        for index, row in enumerate(raw_failures):
            if not isinstance(row, dict):
                raise ValueError(
                    "metadata.yaml_parse_failures entries must be dict rows before ScannerContext handoff"
                )
            file_value = row.get("file")
            error_value = row.get("error")
            line_value = row.get("line")
            column_value = row.get("column")
            if not isinstance(file_value, str) or not isinstance(error_value, str):
                raise ValueError(
                    f"metadata.yaml_parse_failures[{index}] must include string file and error fields before ScannerContext handoff"
                )
            if line_value is not None and not isinstance(line_value, int):
                raise ValueError(
                    f"metadata.yaml_parse_failures[{index}].line must be int | None before ScannerContext handoff"
                )
            if column_value is not None and not isinstance(column_value, int):
                raise ValueError(
                    f"metadata.yaml_parse_failures[{index}].column must be int | None before ScannerContext handoff"
                )
            normalized.append(
                {
                    "file": file_value,
                    "line": line_value,
                    "column": column_value,
                    "error": error_value,
                }
            )
        return normalized

    @staticmethod
    def _build_variable_insights(
        rows: tuple[VariableRow, ...],
    ) -> list[VariableInsight]:
        return [
            {
                "name": _ScanStateBridge._require_row_name(row),
                "type": row.get("type"),
                "default": row.get("default"),
                "source": _ScanStateBridge._require_optional_str_row_field(
                    row,
                    field_name="source",
                    row_name=_ScanStateBridge._require_row_name(row),
                ),
                "required": _ScanStateBridge._require_bool_row_field(
                    row,
                    field_name="required",
                    default=False,
                    row_name=_ScanStateBridge._require_row_name(row),
                ),
                "documented": _ScanStateBridge._require_bool_row_field(
                    row,
                    field_name="documented",
                    default=False,
                    row_name=_ScanStateBridge._require_row_name(row),
                ),
                "secret": _ScanStateBridge._require_bool_row_field(
                    row,
                    field_name="secret",
                    default=False,
                    row_name=_ScanStateBridge._require_row_name(row),
                ),
                "is_unresolved": _ScanStateBridge._require_bool_row_field(
                    row,
                    field_name="is_unresolved",
                    default=False,
                    row_name=_ScanStateBridge._require_row_name(row),
                ),
                "is_ambiguous": _ScanStateBridge._require_bool_row_field(
                    row,
                    field_name="is_ambiguous",
                    default=False,
                    row_name=_ScanStateBridge._require_row_name(row),
                ),
                "uncertainty_reason": _ScanStateBridge._require_optional_str_row_field(
                    row,
                    field_name="uncertainty_reason",
                    row_name=_ScanStateBridge._require_row_name(row),
                ),
                "provenance_confidence": _ScanStateBridge._require_provenance_confidence(
                    row,
                    row_name=_ScanStateBridge._require_row_name(row),
                ),
            }
            for row in rows
        ]

    @staticmethod
    def _build_display_variables(
        rows: tuple[VariableRow, ...],
    ) -> dict[str, DisplayVariableEntry]:
        display_variables: dict[str, DisplayVariableEntry] = {}
        for row in sorted(rows, key=lambda item: str(item.get("name", ""))):
            row_name, entry = _ScanStateBridge._build_display_variable_entry(row)
            display_variables[row_name] = entry
        return display_variables

    @staticmethod
    def _build_requirements_display(
        features: dict[str, object],
    ) -> list[RequirementsDisplayEntry]:
        raw_collections = features.get("external_collections")
        if raw_collections is None:
            return []
        if not isinstance(raw_collections, str):
            raise ValueError(
                "features.external_collections must be a string before ScannerContext handoff"
            )
        if raw_collections in {"", "none"}:
            return []
        return [
            {"collection": name.strip()}
            for name in raw_collections.split(",")
            if name.strip()
        ]


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
    di_container_cls: _DIContainerFactory,
    feature_detector_cls: _FeatureDetectorFactory,
    scanner_context_cls: Callable[..., ScannerContext],
    variable_discovery_cls: _VariableDiscoveryFactory,
    resolve_comment_driven_documentation_plugin_fn: Callable[
        [object], "CommentDrivenDocumentationPlugin"
    ],
    default_plugin_registry: "ScanPipelineRuntimeRegistry",
    ensure_prepared_policy_bundle_fn: _EnsurePreparedPolicyBundleFn | None = None,
) -> NonCollectionRunScanExecutionRequest:
    """Build the scanner_core-owned execution request for non-collection run_scan."""
    validated_role_path = validate_role_path_fn(role_path)

    canonical_options = _build_canonical_options(
        validated_role_path=validated_role_path,
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
        policy_context=policy_context,
        strict_phase_failures=strict_phase_failures,
        scan_pipeline_plugin=scan_pipeline_plugin,
        build_run_scan_options_canonical_fn=build_run_scan_options_canonical_fn,
    )

    return _assemble_execution_request(
        canonical_options=canonical_options,
        variable_discovery_cls=variable_discovery_cls,
        feature_detector_cls=feature_detector_cls,
        extract_role_description_fn=extract_role_description_fn,
        resolve_comment_driven_documentation_plugin_fn=resolve_comment_driven_documentation_plugin_fn,
        di_container_cls=di_container_cls,
        scanner_context_cls=scanner_context_cls,
        build_run_scan_options_canonical_fn=build_run_scan_options_canonical_fn,
        default_plugin_registry=default_plugin_registry,
        ensure_prepared_policy_bundle_fn=ensure_prepared_policy_bundle_fn,
    )


def _build_canonical_options(
    *,
    validated_role_path: str,
    role_name_override: str | None,
    readme_config_path: str | None,
    policy_config_path: str | None,
    concise_readme: bool,
    scanner_report_output: str | None,
    include_vars_main: bool,
    include_scanner_report_link: bool,
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
    policy_context: dict[str, object] | None,
    strict_phase_failures: bool,
    scan_pipeline_plugin: str | None,
    build_run_scan_options_canonical_fn: Callable[..., ScanOptionsDict],
) -> ScanOptionsDict:
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
    canonical_options["strict_phase_failures"] = require_strict_phase_failures(
        strict_phase_failures,
    )
    canonical_options["concise_readme"] = bool(concise_readme)
    canonical_options["scanner_report_output"] = scanner_report_output
    canonical_options["include_scanner_report_link"] = bool(include_scanner_report_link)
    if isinstance(scan_pipeline_plugin, str) and scan_pipeline_plugin.strip():
        canonical_options["scan_pipeline_plugin"] = scan_pipeline_plugin.strip()
    return canonical_options


def _assemble_execution_request(
    *,
    canonical_options: ScanOptionsDict,
    variable_discovery_cls: _VariableDiscoveryFactory,
    feature_detector_cls: _FeatureDetectorFactory,
    extract_role_description_fn: Callable[[Path, str], str],
    resolve_comment_driven_documentation_plugin_fn: Callable[
        [object], "CommentDrivenDocumentationPlugin"
    ],
    di_container_cls: _DIContainerFactory,
    scanner_context_cls: Callable[..., ScannerContext],
    build_run_scan_options_canonical_fn: Callable[..., ScanOptionsDict],
    default_plugin_registry: "ScanPipelineRuntimeRegistry",
    ensure_prepared_policy_bundle_fn: _EnsurePreparedPolicyBundleFn | None,
) -> NonCollectionRunScanExecutionRequest:
    ensured_policy_bundle_fn = _require_prepared_policy_bundle_enforcer(
        ensure_prepared_policy_bundle_fn
    )

    runtime = _assemble_runtime_participants(
        canonical_options=canonical_options,
        variable_discovery_cls=variable_discovery_cls,
        feature_detector_cls=feature_detector_cls,
        extract_role_description_fn=extract_role_description_fn,
        resolve_comment_driven_documentation_plugin_fn=resolve_comment_driven_documentation_plugin_fn,
        di_container_cls=di_container_cls,
        scanner_context_cls=scanner_context_cls,
        default_plugin_registry=default_plugin_registry,
    )

    return _finalize_execution_request(
        canonical_options=canonical_options,
        runtime=runtime,
        ensure_prepared_policy_bundle_fn=ensured_policy_bundle_fn,
    )


def _require_prepared_policy_bundle_enforcer(
    ensure_prepared_policy_bundle_fn: _EnsurePreparedPolicyBundleFn | None,
) -> _EnsurePreparedPolicyBundleFn:
    if ensure_prepared_policy_bundle_fn is None:
        raise ValueError(
            "ensure_prepared_policy_bundle_fn is required for "
            "non-collection execution request construction"
        )
    return ensure_prepared_policy_bundle_fn


def _finalize_execution_request(
    *,
    canonical_options: ScanOptionsDict,
    runtime: _RuntimeAssembly,
    ensure_prepared_policy_bundle_fn: _EnsurePreparedPolicyBundleFn | None,
) -> NonCollectionRunScanExecutionRequest:
    """Finalize the execution request after runtime participants are assembled."""

    if ensure_prepared_policy_bundle_fn is None:
        raise ValueError(
            "ensure_prepared_policy_bundle_fn is required for "
            "non-collection execution request construction"
        )
    ensure_prepared_policy_bundle_fn(
        scan_options=canonical_options, di=runtime.container
    )
    runtime.container.replace_scan_options(canonical_options)
    scanner_context = runtime.container.factory_scanner_context()
    strict_mode = resolve_strict_phase_failures(canonical_options)

    def _build_payload() -> RunScanOutputPayload:
        return cast(RunScanOutputPayload, scanner_context.orchestrate_scan())

    return NonCollectionRunScanExecutionRequest(
        role_path=str(canonical_options["role_path"]),
        scan_options=canonical_options,
        strict_mode=strict_mode,
        runtime_registry=runtime.runtime_registry,
        scanner_context=scanner_context,
        build_payload_fn=_build_payload,
    )


def _assemble_runtime_participants(
    *,
    canonical_options: ScanOptionsDict,
    variable_discovery_cls: _VariableDiscoveryFactory,
    feature_detector_cls: _FeatureDetectorFactory,
    extract_role_description_fn: Callable[[Path, str], str],
    resolve_comment_driven_documentation_plugin_fn: Callable[
        [object], "CommentDrivenDocumentationPlugin"
    ],
    di_container_cls: _DIContainerFactory,
    scanner_context_cls: Callable[..., ScannerContext],
    default_plugin_registry: "ScanPipelineRuntimeRegistry",
) -> _RuntimeAssembly:
    runtime_registry = default_plugin_registry
    resolved_platform_key = _resolve_runtime_platform_key(
        canonical_options,
        runtime_registry,
    )

    # _bridge_slot resolves the forward reference: container needs bridge methods
    # as factory overrides, but bridge requires container at construction time.
    _bridge_slot: list[_ScanStateBridge] = []

    container = di_container_cls(
        role_path=str(canonical_options["role_path"]),
        scan_options=canonical_options,
        registry=runtime_registry,
        platform_key=resolved_platform_key,
        scanner_context_wiring={
            "scanner_context_cls": scanner_context_cls,
            "prepare_scan_context_fn": lambda opts: _bridge_slot[
                0
            ].prepare_scan_context(opts, canonical_options),
        },
        factory_overrides={
            "variable_discovery_factory": lambda di, rp, opts: _bridge_slot[
                0
            ].variable_discovery_factory(di, rp, opts),
            "feature_detector_factory": lambda di, rp, opts: _bridge_slot[
                0
            ].feature_detector_factory(di, rp, opts),
        },
        inherit_default_event_listeners=False,
    )
    bridge = _ScanStateBridge(
        container=container,
        variable_discovery_cls=variable_discovery_cls,
        feature_detector_cls=feature_detector_cls,
        extract_role_description_fn=extract_role_description_fn,
        resolve_comment_driven_documentation_plugin_fn=resolve_comment_driven_documentation_plugin_fn,
    )
    _bridge_slot.append(bridge)
    return _RuntimeAssembly(runtime_registry=runtime_registry, container=container)
