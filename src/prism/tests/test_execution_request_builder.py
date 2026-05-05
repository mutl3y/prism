"""Unit tests for scanner_core.execution_request_builder pure helpers (FIND-13 closure)."""

from __future__ import annotations

from typing import Protocol, TypeGuard, cast

import pytest

from prism.scanner_core.di import DIContainer
from prism.scanner_core.execution_request_builder import (
    NonCollectionRunScanExecutionRequest,
    _FeatureDetectorRunner as _ExecutionRequestFeatureDetectorRunner,
    _ScanStateBridge,
    _FeatureDetectorFactory as _ExecutionRequestFeatureDetectorFactory,
    _VariableDiscoveryRunner as _ExecutionRequestVariableDiscoveryRunner,
    _VariableDiscoveryFactory as _ExecutionRequestVariableDiscoveryFactory,
    _assemble_execution_request,
    _assemble_runtime_participants,
)
from prism.scanner_core.events import (
    clear_default_listeners,
    register_default_listener,
)
from prism.scanner_core.protocols_runtime import DIFactoryOverride
from prism.scanner_core.scanner_context import ScannerContext
from prism.scanner_data import VariableRow
from prism.scanner_data.contracts_request import (
    FeaturesContext,
    ScanContextPayload,
    ScanOptionsDict,
)
from prism.scanner_plugins.registry import PluginRegistry


def _scan_options(
    *,
    role_path: str = "/tmp/role",
    strict_phase_failures: bool | None = None,
    platform: str | None = None,
) -> ScanOptionsDict:
    scan_options: ScanOptionsDict = {
        "role_path": role_path,
        "role_name_override": None,
        "readme_config_path": None,
        "policy_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": None,
        "detailed_catalog": False,
        "include_task_parameters": False,
        "include_task_runbooks": False,
        "inline_task_runbooks": False,
        "include_collection_checks": False,
        "keep_unknown_style_sections": False,
        "adopt_heading_mode": None,
        "vars_seed_paths": None,
        "style_readme_path": None,
        "style_source_path": None,
        "style_guide_skeleton": False,
        "compare_role_path": None,
        "fail_on_unconstrained_dynamic_includes": None,
        "fail_on_yaml_like_task_annotations": None,
        "ignore_unresolved_internal_underscore_references": None,
    }
    if strict_phase_failures is not None:
        scan_options["strict_phase_failures"] = strict_phase_failures
    if platform is not None:
        scan_options["platform"] = platform
    return scan_options


def _features_context(
    *,
    external_collections: str = "",
) -> FeaturesContext:
    return {
        "task_files_scanned": 0,
        "tasks_scanned": 0,
        "recursive_task_includes": 0,
        "unique_modules": "",
        "external_collections": external_collections,
        "handlers_notified": "",
        "privileged_tasks": 0,
        "conditional_tasks": 0,
        "tagged_tasks": 0,
        "included_role_calls": 0,
        "included_roles": "",
        "dynamic_included_role_calls": 0,
        "dynamic_included_roles": "",
        "disabled_task_annotations": 0,
        "yaml_like_task_annotations": 0,
    }


class _VariableDiscoveryRunner(Protocol):
    def discover(self) -> tuple[VariableRow, ...]: ...


class _FeatureDetectorRunner(Protocol):
    def detect(self) -> FeaturesContext: ...


class _PrepareScanContextFn(Protocol):
    def __call__(self, scan_options: ScanOptionsDict) -> ScanContextPayload: ...


def _is_variable_discovery_runner(value: object) -> TypeGuard[_VariableDiscoveryRunner]:
    return hasattr(value, "discover")


def _is_feature_detector_runner(value: object) -> TypeGuard[_FeatureDetectorRunner]:
    return hasattr(value, "detect")


def _is_prepare_scan_context_fn(value: object) -> TypeGuard[_PrepareScanContextFn]:
    return callable(value)


class _NoopVariableDiscovery:
    def discover(self) -> tuple[VariableRow, ...]:
        return ()


class _NoopFeatureDetector:
    def detect(self) -> FeaturesContext:
        return _features_context()


class _NoopVariableDiscoveryFactory:
    def __call__(
        self,
        _di: DIContainer,
        _role_path: str,
        _scan_options: ScanOptionsDict,
    ) -> _ExecutionRequestVariableDiscoveryRunner:
        return _NoopVariableDiscovery()


class _NoopFeatureDetectorFactory:
    def __call__(
        self,
        _di: DIContainer,
        _role_path: str,
        _scan_options: ScanOptionsDict,
    ) -> _ExecutionRequestFeatureDetectorRunner:
        return _NoopFeatureDetector()


_NOOP_VARIABLE_DISCOVERY_FACTORY = _NoopVariableDiscoveryFactory()
_NOOP_FEATURE_DETECTOR_FACTORY = _NoopFeatureDetectorFactory()
_NOOP_VARIABLE_DISCOVERY_FACTORY_TYPED = cast(
    _ExecutionRequestVariableDiscoveryFactory,
    _NOOP_VARIABLE_DISCOVERY_FACTORY,
)
_NOOP_FEATURE_DETECTOR_FACTORY_TYPED = cast(
    _ExecutionRequestFeatureDetectorFactory,
    _NOOP_FEATURE_DETECTOR_FACTORY,
)


class _EmptyCommentDocumentationPlugin:
    def extract_role_notes_from_comments(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
        marker_prefix: str = "prism",
    ) -> dict[str, list[str]]:
        assert role_path
        assert exclude_paths is None
        assert marker_prefix == "prism"
        return {
            "warnings": [],
            "deprecations": [],
            "notes": [],
            "additionals": [],
        }


def _resolve_empty_comment_plugin(
    _container: object,
) -> _EmptyCommentDocumentationPlugin:
    return _EmptyCommentDocumentationPlugin()


class _StubScannerContext(ScannerContext):
    def __init__(self, **_kwargs: object) -> None:
        pass

    def orchestrate_scan(self) -> dict[str, str]:
        return {"status": "ok"}


def _build_run_scan_options_canonical(**_kwargs: object) -> ScanOptionsDict:
    role_path = _kwargs.get("role_path")
    return _scan_options(role_path=str(role_path or "/tmp/role"))


class _TestContainer(DIContainer):
    def __init__(
        self,
        role_path: str,
        scan_options: ScanOptionsDict,
        *,
        registry: object,
        platform_key: str,
        scanner_context_wiring: dict[str, object],
        factory_overrides: dict[str, object],
        inherit_default_event_listeners: bool,
    ) -> None:
        super().__init__(
            role_path,
            scan_options,
            registry=cast("PluginRegistry | None", registry),
            platform_key=platform_key,
            scanner_context_wiring=scanner_context_wiring,
            factory_overrides=cast("dict[str, DIFactoryOverride]", factory_overrides),
            inherit_default_event_listeners=inherit_default_event_listeners,
        )


class TestNonCollectionRunScanExecutionRequestShape:
    def test_is_frozen_dataclass(self) -> None:
        import dataclasses

        fields = {
            f.name for f in dataclasses.fields(NonCollectionRunScanExecutionRequest)
        }
        assert fields == {
            "role_path",
            "scan_options",
            "strict_mode",
            "runtime_registry",
            "scanner_context",
            "build_payload_fn",
        }

    def test_is_immutable(self) -> None:
        import dataclasses

        @dataclasses.dataclass(frozen=True)
        class _Stub:
            pass

        assert NonCollectionRunScanExecutionRequest.__dataclass_params__.frozen  # type: ignore[attr-defined]


class TestBuildDisplayVariables:
    def _call(self, rows):
        return _ScanStateBridge._build_display_variables(tuple(rows))

    def test_empty_rows_returns_empty_dict(self) -> None:
        assert self._call([]) == {}

    def test_rows_sorted_by_name(self) -> None:
        rows = [{"name": "z_var"}, {"name": "a_var"}]
        out = self._call(rows)
        assert list(out.keys()) == ["a_var", "z_var"]

    def test_rows_with_empty_name_raise_value_error(self) -> None:
        rows = [{"name": ""}, {"name": "valid"}]

        with pytest.raises(ValueError, match="display_variables rows must include"):
            self._call(rows)

    def test_rows_with_invalid_display_variables_bool_raise_value_error(self) -> None:
        rows = [{"name": "valid", "required": "yes"}]

        with pytest.raises(ValueError, match="display_variables.valid.required"):
            self._call(rows)

    def test_field_mapping_populates_correctly(self) -> None:
        row = {
            "name": "my_var",
            "type": "str",
            "default": "hello",
            "source": "defaults/main.yml",
            "required": True,
            "documented": True,
            "secret": False,
            "is_unresolved": False,
            "is_ambiguous": True,
            "uncertainty_reason": "templated",
        }
        out = self._call([row])
        entry = out["my_var"]
        assert entry["type"] == "str"
        assert entry["default"] == "hello"
        assert entry["required"] is True
        assert entry["documented"] is True
        assert entry["secret"] is False
        assert entry["is_ambiguous"] is True
        assert entry["uncertainty_reason"] == "templated"

    def test_missing_optional_fields_default_to_safe_values(self) -> None:
        out = self._call([{"name": "v"}])
        entry = out["v"]
        assert entry["required"] is False
        assert entry["documented"] is False
        assert entry["secret"] is False
        assert entry["is_unresolved"] is False
        assert entry["is_ambiguous"] is False
        assert entry["uncertainty_reason"] is None

    def test_duplicate_names_last_row_wins(self) -> None:
        rows = [
            {"name": "dup", "default": "first"},
            {"name": "dup", "default": "second"},
        ]
        out = self._call(rows)
        assert out["dup"]["default"] == "second"


class TestBuildRequirementsDisplay:
    def _call(self, features):
        return _ScanStateBridge._build_requirements_display(features)

    def test_no_external_collections_returns_empty_list(self) -> None:
        assert self._call({}) == []

    def test_none_sentinel_returns_empty_list(self) -> None:
        assert self._call({"external_collections": "none"}) == []

    def test_single_collection_entry(self) -> None:
        out = self._call({"external_collections": "ns.col"})
        assert out == [{"collection": "ns.col"}]

    def test_comma_separated_entries(self) -> None:
        out = self._call({"external_collections": "ns.a, ns.b, ns.c"})
        assert out == [
            {"collection": "ns.a"},
            {"collection": "ns.b"},
            {"collection": "ns.c"},
        ]

    def test_strips_surrounding_whitespace(self) -> None:
        out = self._call({"external_collections": "  ns.x  ,  ns.y  "})
        assert [e["collection"] for e in out] == ["ns.x", "ns.y"]

    def test_empty_entries_in_csv_are_skipped(self) -> None:
        out = self._call({"external_collections": "ns.a,,ns.b"})
        assert [e["collection"] for e in out] == ["ns.a", "ns.b"]

    def test_invalid_external_collections_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="external_collections"):
            self._call({"external_collections": ["ns.a"]})


class TestRoleNotesFailClosed:
    def test_missing_role_notes_bucket_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="role_notes.deprecations"):
            _ScanStateBridge._normalize_role_notes(
                {
                    "warnings": [],
                    "notes": [],
                    "additionals": [],
                }
            )

    def test_invalid_role_notes_bucket_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="role_notes.notes"):
            _ScanStateBridge._normalize_role_notes(
                {
                    "warnings": [],
                    "deprecations": [],
                    "notes": [1],
                    "additionals": [],
                }
            )


class TestPrepareScanContextMetadataFailClosed:
    def test_invalid_yaml_parse_failures_raise_value_error(self) -> None:
        bridge = _ScanStateBridge(
            container=object(),
            variable_discovery_cls=_NOOP_VARIABLE_DISCOVERY_FACTORY_TYPED,
            feature_detector_cls=_NOOP_FEATURE_DETECTOR_FACTORY_TYPED,
            extract_role_description_fn=lambda _path, _name: "role description",
            resolve_comment_driven_documentation_plugin_fn=_resolve_empty_comment_plugin,
        )

        with pytest.raises(ValueError, match="yaml_parse_failures"):
            bridge.prepare_scan_context(
                _scan_options(),
                {
                    **_scan_options(),
                    "yaml_parse_failures": "invalid",
                },
            )


class TestRuntimeAssemblySeam:
    def test_execution_request_finalization_seam_requires_prepared_policy_enforcement(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="ensure_prepared_policy_bundle_fn is required",
        ):
            _assemble_execution_request(
                canonical_options=_scan_options(),
                variable_discovery_cls=_NOOP_VARIABLE_DISCOVERY_FACTORY_TYPED,
                feature_detector_cls=_NOOP_FEATURE_DETECTOR_FACTORY_TYPED,
                extract_role_description_fn=lambda _path, _name: "",
                resolve_comment_driven_documentation_plugin_fn=_resolve_empty_comment_plugin,
                di_container_cls=lambda *args, **kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "runtime assembly should not begin before enforcer validation"
                    )
                ),
                scanner_context_cls=_StubScannerContext,
                build_run_scan_options_canonical_fn=_build_run_scan_options_canonical,
                default_plugin_registry=cast(PluginRegistry, object()),
                ensure_prepared_policy_bundle_fn=None,
            )

    def test_runtime_participants_use_authoritative_registry_and_bridge_factories(
        self,
    ) -> None:
        class _Registry:
            def __init__(self, default_platform_key: str) -> None:
                self._default_platform_key = default_platform_key

            def get_default_platform_key(self) -> str:
                return self._default_platform_key

        class _VariableDiscovery:
            def discover(self) -> tuple[VariableRow, ...]:
                return (
                    {
                        "name": "var_a",
                        "type": "str",
                        "default": "",
                        "source": "defaults/main.yml",
                        "documented": False,
                        "required": False,
                        "secret": False,
                        "provenance_source_file": None,
                        "provenance_line": None,
                        "provenance_confidence": 0.0,
                        "uncertainty_reason": None,
                        "is_unresolved": False,
                        "is_ambiguous": False,
                    },
                )

        class _FeatureDetector:
            def detect(self) -> FeaturesContext:
                return _features_context(external_collections="ns.collection")

        class _VariableDiscoveryFactory:
            def __call__(
                self,
                _di: DIContainer,
                _role_path: str,
                _scan_options: ScanOptionsDict,
            ) -> _ExecutionRequestVariableDiscoveryRunner:
                return _VariableDiscovery()

        class _FeatureDetectorFactory:
            def __call__(
                self,
                _di: DIContainer,
                _role_path: str,
                _scan_options: ScanOptionsDict,
            ) -> _ExecutionRequestFeatureDetectorRunner:
                return _FeatureDetector()

        class _CommentDocumentationPlugin:
            def extract_role_notes_from_comments(
                self,
                role_path: str,
                exclude_paths: list[str] | None = None,
                marker_prefix: str = "prism",
            ) -> dict[str, list[str]]:
                assert role_path
                assert exclude_paths is None
                assert marker_prefix == "prism"
                return {
                    "warnings": [],
                    "deprecations": [],
                    "notes": [],
                    "additionals": [],
                }

        class _Container(_TestContainer):
            def __init__(
                self,
                role_path: str,
                scan_options: ScanOptionsDict,
                *,
                registry: object,
                platform_key: str,
                scanner_context_wiring: dict[str, object],
                factory_overrides: dict[str, object],
                inherit_default_event_listeners: bool,
            ) -> None:
                super().__init__(
                    role_path,
                    scan_options,
                    registry=registry,
                    platform_key=platform_key,
                    scanner_context_wiring=scanner_context_wiring,
                    factory_overrides=factory_overrides,
                    inherit_default_event_listeners=inherit_default_event_listeners,
                )

        runtime = _assemble_runtime_participants(
            canonical_options=_scan_options(),
            variable_discovery_cls=cast(
                _ExecutionRequestVariableDiscoveryFactory,
                _VariableDiscoveryFactory(),
            ),
            feature_detector_cls=cast(
                _ExecutionRequestFeatureDetectorFactory,
                _FeatureDetectorFactory(),
            ),
            extract_role_description_fn=lambda _path, _name: "role description",
            resolve_comment_driven_documentation_plugin_fn=(
                lambda _container: _CommentDocumentationPlugin()
            ),
            di_container_cls=_Container,
            scanner_context_cls=_StubScannerContext,
            default_plugin_registry=cast(PluginRegistry, _Registry("ansible")),
        )

        discovery = runtime.container.factory_overrides["variable_discovery_factory"](
            runtime.container,
            "/tmp/role",
            _scan_options(),
        )
        features = runtime.container.factory_overrides["feature_detector_factory"](
            runtime.container,
            "/tmp/role",
            _scan_options(),
        )
        assert _is_variable_discovery_runner(discovery)
        assert _is_feature_detector_runner(features)
        prepare_scan_context = runtime.container.scanner_context_wiring[
            "prepare_scan_context_fn"
        ]
        assert _is_prepare_scan_context_fn(prepare_scan_context)

        discovery.discover()
        features.detect()
        payload = prepare_scan_context(_scan_options())

        assert runtime.runtime_registry is runtime.container.plugin_registry
        assert runtime.container.platform_key == "ansible"
        assert runtime.container.inherit_default_event_listeners is False
        assert runtime.container.factory_event_bus().listener_count == 0
        assert payload["requirements_display"] == [{"collection": "ns.collection"}]
        assert payload["display_variables"] == {
            "var_a": payload["display_variables"]["var_a"]
        }

    def test_runtime_participants_do_not_inherit_process_default_listeners(
        self,
    ) -> None:
        seen: list[str] = []

        def listener(_event: object) -> None:
            seen.append("early")

        def late_listener(_event: object) -> None:
            seen.append("late")

        class _Registry:
            def get_default_platform_key(self) -> str:
                return "ansible"

        clear_default_listeners()
        register_default_listener(listener)
        try:
            runtime = _assemble_runtime_participants(
                canonical_options=_scan_options(),
                variable_discovery_cls=_NOOP_VARIABLE_DISCOVERY_FACTORY_TYPED,
                feature_detector_cls=_NOOP_FEATURE_DETECTOR_FACTORY_TYPED,
                extract_role_description_fn=lambda _path, _name: "role description",
                resolve_comment_driven_documentation_plugin_fn=(
                    _resolve_empty_comment_plugin
                ),
                di_container_cls=DIContainer,
                scanner_context_cls=_StubScannerContext,
                default_plugin_registry=cast(PluginRegistry, _Registry()),
            )

            bus = runtime.container.factory_event_bus()
            register_default_listener(late_listener)
            assert runtime.container.inherit_default_event_listeners is False
            assert bus.listener_count == 0
            with bus.phase("feature_detection"):
                pass
            assert seen == []
        finally:
            clear_default_listeners()

    def test_runtime_participants_use_platform_option_before_registry_default(
        self,
    ) -> None:
        class _Registry:
            def get_default_platform_key(self) -> str:
                return "ansible"

        runtime = _assemble_runtime_participants(
            canonical_options=_scan_options(platform="terraform"),
            variable_discovery_cls=_NOOP_VARIABLE_DISCOVERY_FACTORY_TYPED,
            feature_detector_cls=_NOOP_FEATURE_DETECTOR_FACTORY_TYPED,
            extract_role_description_fn=lambda _path, _name: "role description",
            resolve_comment_driven_documentation_plugin_fn=(
                _resolve_empty_comment_plugin
            ),
            di_container_cls=DIContainer,
            scanner_context_cls=_StubScannerContext,
            default_plugin_registry=cast(PluginRegistry, _Registry()),
        )

        assert runtime.container.platform_key == "terraform"

    def test_execution_request_finalization_order_is_unchanged(self) -> None:
        calls: list[str] = []

        class _Registry:
            def get_default_platform_key(self) -> str:
                return "ansible"

        class _ScannerContext(_StubScannerContext):
            def orchestrate_scan(self) -> dict[str, str]:
                return {"status": "ok"}

        class _CommentDocumentationPlugin:
            def extract_role_notes_from_comments(
                self,
                role_path: str,
                exclude_paths: list[str] | None = None,
                marker_prefix: str = "prism",
            ) -> dict[str, list[str]]:
                assert role_path
                assert exclude_paths is None
                assert marker_prefix == "prism"
                return {
                    "warnings": [],
                    "deprecations": [],
                    "notes": [],
                    "additionals": [],
                }

        class _Container(_TestContainer):
            def __init__(
                self,
                role_path: str,
                scan_options: ScanOptionsDict,
                *,
                registry: object,
                platform_key: str,
                scanner_context_wiring: dict[str, object],
                factory_overrides: dict[str, object],
                inherit_default_event_listeners: bool,
            ) -> None:
                super().__init__(
                    role_path,
                    scan_options,
                    registry=registry,
                    platform_key=platform_key,
                    scanner_context_wiring=scanner_context_wiring,
                    factory_overrides=factory_overrides,
                    inherit_default_event_listeners=inherit_default_event_listeners,
                )

            def replace_scan_options(self, scan_options: ScanOptionsDict) -> None:
                calls.append("replace")
                self._scan_options = scan_options

            def factory_scanner_context(self) -> _ScannerContext:
                calls.append("context")
                return _ScannerContext()

        request = _assemble_execution_request(
            canonical_options=_scan_options(strict_phase_failures=False),
            variable_discovery_cls=_NOOP_VARIABLE_DISCOVERY_FACTORY_TYPED,
            feature_detector_cls=_NOOP_FEATURE_DETECTOR_FACTORY_TYPED,
            extract_role_description_fn=lambda _path, _name: "",
            resolve_comment_driven_documentation_plugin_fn=(
                lambda _container: _CommentDocumentationPlugin()
            ),
            di_container_cls=_Container,
            scanner_context_cls=_ScannerContext,
            build_run_scan_options_canonical_fn=_build_run_scan_options_canonical,
            default_plugin_registry=cast(PluginRegistry, _Registry()),
            ensure_prepared_policy_bundle_fn=lambda *, scan_options, di: calls.append(
                "ensure"
            ),
        )

        assert calls == ["ensure", "replace", "context"]
        assert request.strict_mode is False
        assert request.build_payload_fn() == {"status": "ok"}
