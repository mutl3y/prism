"""Execution request builder for the non-collection scan path."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Protocol, cast

from prism.scanner_core.di import resolve_platform_key
from prism.scanner_data import VariableRow
from prism.scanner_data.contracts_request import (
    DisplayVariableEntry,
    FeaturesContext,
    RoleNotes,
    ScanContextPayload,
    ScanOptionsDict,
    VariableInsight,
)

if TYPE_CHECKING:
    from prism.scanner_core.di import DIContainer
    from prism.scanner_core.scanner_context import ScannerContext
    from prism.scanner_core.protocols_runtime import ScanPayloadBuilderFn
    from prism.scanner_plugins.interfaces import CommentDrivenDocumentationPlugin


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


class _DIContainerFactory(Protocol):
    """Factory contract for the execution-request DI container."""

    def __call__(
        self,
        role_path: str,
        scan_options: ScanOptionsDict,
        *,
        registry: object,
        platform_key: str,
        scanner_context_wiring: dict[str, object],
        factory_overrides: dict[str, object],
    ) -> "DIContainer": ...


@dataclass(frozen=True)
class NonCollectionRunScanExecutionRequest:
    """Canonical scanner_core execution request for the non-collection run_scan path."""

    role_path: str
    scan_options: ScanOptionsDict
    strict_mode: bool
    runtime_registry: object
    scanner_context: ScannerContext
    build_payload_fn: ScanPayloadBuilderFn


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
        normalized = (
            list(yaml_parse_failures) if isinstance(yaml_parse_failures, list) else []
        )

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
    def _normalize_role_notes(raw_role_notes: dict[str, list[str]]) -> RoleNotes:
        return {
            "warnings": list(raw_role_notes.get("warnings", [])),
            "deprecations": list(raw_role_notes.get("deprecations", [])),
            "notes": list(raw_role_notes.get("notes", [])),
            "additionals": list(raw_role_notes.get("additionals", [])),
        }

    @staticmethod
    def _build_variable_insights(
        rows: tuple[VariableRow, ...],
    ) -> list[VariableInsight]:
        return [
            {
                "name": str(row.get("name") or ""),
                "type": row.get("type"),
                "default": row.get("default"),
                "source": row.get("source"),
                "required": bool(row.get("required", False)),
                "documented": bool(row.get("documented", False)),
                "secret": bool(row.get("secret", False)),
                "is_unresolved": bool(row.get("is_unresolved", False)),
                "is_ambiguous": bool(row.get("is_ambiguous", False)),
                "uncertainty_reason": row.get("uncertainty_reason"),
                "provenance_confidence": float(
                    row.get("provenance_confidence", 0.0) or 0.0
                ),
            }
            for row in rows
            if row.get("name")
        ]

    @staticmethod
    def _build_display_variables(
        rows: tuple[VariableRow, ...],
    ) -> dict[str, DisplayVariableEntry]:
        """Build display_variables payload from variable rows.

        Invariant: Required field 'name' must be present and non-empty in each row.
        Rows with missing/empty 'name' are skipped (logged at discovery phase).
        """
        display_variables: dict[str, DisplayVariableEntry] = {}
        for row in sorted(rows, key=lambda item: str(item.get("name", ""))):
            row_name = str(row.get("name") or "")
            if not row_name:
                continue
            entry: DisplayVariableEntry = {
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
            display_variables[row_name] = entry
        return display_variables

    @staticmethod
    def _build_requirements_display(
        features: dict[str, object],
    ) -> list[dict[str, str]]:
        raw_collections = str(features.get("external_collections") or "none")
        if raw_collections == "none":
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
    default_plugin_registry: object,
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
    canonical_options["strict_phase_failures"] = bool(strict_phase_failures)
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
    default_plugin_registry: object,
    ensure_prepared_policy_bundle_fn: _EnsurePreparedPolicyBundleFn | None,
) -> NonCollectionRunScanExecutionRequest:
    runtime_registry = default_plugin_registry
    resolved_platform_key = resolve_platform_key(canonical_options, runtime_registry)

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
    )
    bridge = _ScanStateBridge(
        container=container,
        variable_discovery_cls=variable_discovery_cls,
        feature_detector_cls=feature_detector_cls,
        extract_role_description_fn=extract_role_description_fn,
        resolve_comment_driven_documentation_plugin_fn=resolve_comment_driven_documentation_plugin_fn,
    )
    _bridge_slot.append(bridge)

    if ensure_prepared_policy_bundle_fn is None:
        raise ValueError(
            "ensure_prepared_policy_bundle_fn is required for "
            "non-collection execution request construction"
        )
    ensure_prepared_policy_bundle_fn(scan_options=canonical_options, di=container)
    scanner_context = container.factory_scanner_context()
    strict_mode = bool(canonical_options.get("strict_phase_failures", True))

    return NonCollectionRunScanExecutionRequest(
        role_path=str(canonical_options["role_path"]),
        scan_options=canonical_options,
        strict_mode=strict_mode,
        runtime_registry=runtime_registry,
        scanner_context=scanner_context,
        build_payload_fn=scanner_context.orchestrate_scan,
    )
