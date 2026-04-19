"""Focused ScannerContext orchestration checks for the fsrc package lane."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "fsrc" / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> object:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(FSRC_SOURCE_ROOT))
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        yield
    finally:
        sys.path[:] = original_path
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        sys.modules.update(original_modules)


class _DiscoveryStub:
    def __init__(self, payload: tuple[Any, ...] | Exception) -> None:
        self._payload = payload

    def discover(self) -> tuple[Any, ...]:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FeatureStub:
    def __init__(self, payload: dict[str, Any] | Exception) -> None:
        self._payload = payload

    def detect(self) -> dict[str, Any]:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _BuildOptionsRecorder:
    def __init__(self, result: dict[str, Any]) -> None:
        self.calls: list[dict[str, Any]] = []
        self._result = result

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return dict(self._result)


class _PreparedTaskLinePolicy:
    TASK_INCLUDE_KEYS = {"include_tasks"}
    ROLE_INCLUDE_KEYS = {"include_role"}
    INCLUDE_VARS_KEYS = {"include_vars"}
    SET_FACT_KEYS = {"set_fact"}
    TASK_BLOCK_KEYS = {"block"}
    TASK_META_KEYS = {"meta"}

    @staticmethod
    def detect_task_module(_task: dict[str, Any]) -> str:
        return "debug"


class _PreparedJinjaPolicy:
    @staticmethod
    def collect_undeclared_jinja_variables(_text: str) -> set[str]:
        return set()


def _prepared_policy_bundle() -> dict[str, Any]:
    return {
        "task_line_parsing": _PreparedTaskLinePolicy(),
        "jinja_analysis": _PreparedJinjaPolicy(),
    }


def _canonical_scan_options() -> dict[str, Any]:
    return {
        "role_path": "/tmp/role",
        "role_name_override": None,
        "readme_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": None,
        "detailed_catalog": False,
        "include_task_parameters": True,
        "include_task_runbooks": True,
        "inline_task_runbooks": True,
        "include_collection_checks": True,
        "keep_unknown_style_sections": True,
        "adopt_heading_mode": None,
        "vars_seed_paths": None,
        "style_readme_path": None,
        "style_source_path": None,
        "style_guide_skeleton": False,
        "compare_role_path": None,
        "fail_on_unconstrained_dynamic_includes": None,
        "fail_on_yaml_like_task_annotations": None,
        "ignore_unresolved_internal_underscore_references": None,
        "prepared_policy_bundle": _prepared_policy_bundle(),
    }


def _context_payload() -> dict[str, Any]:
    return {
        "rp": "/tmp/role",
        "role_name": "demo",
        "description": "demo description",
        "requirements_display": [{"name": "ansible-core"}],
        "undocumented_default_filters": [],
        "display_variables": {"demo_var": {"default": "value"}},
        "metadata": {"marker_prefix": "NOTE"},
    }


def test_fsrc_scanner_context_orchestrates_payload_shape_parity() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")

        options = _canonical_scan_options()
        recorder = _BuildOptionsRecorder(options)
        container = di_module.DIContainer(
            role_path=options["role_path"], scan_options=options
        )
        container.inject_mock_variable_discovery(
            _DiscoveryStub(({"name": "demo_var"},))
        )
        container.inject_mock_feature_detector(
            _FeatureStub(
                {
                    "task_files_scanned": 1,
                    "tasks_scanned": 2,
                }
            )
        )

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: _context_payload(),
        )
        result = context.orchestrate_scan()

    assert set(result) == {
        "role_name",
        "description",
        "display_variables",
        "requirements_display",
        "undocumented_default_filters",
        "metadata",
    }
    assert result["role_name"] == "demo"
    assert result["description"] == "demo description"
    assert result["display_variables"]["demo_var"]["default"] == "value"
    assert result["requirements_display"] == [{"name": "ansible-core"}]
    assert result["undocumented_default_filters"] == []
    assert result["metadata"]["features"]["task_files_scanned"] == 1
    assert result["metadata"]["features"]["tasks_scanned"] == 2
    assert recorder.calls == []


def test_fsrc_scanner_context_consumes_existing_canonical_options_without_rebuilding() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")

        options = _canonical_scan_options()
        options["scan_policy_warnings"] = [
            {
                "code": "sample_policy_warning",
                "message": "Sample warning for test.",
                "detail": {
                    "scope": "test",
                },
            }
        ]
        recorder = _BuildOptionsRecorder(options)
        container = di_module.DIContainer(
            role_path=options["role_path"], scan_options=options
        )
        container.inject_mock_variable_discovery(_DiscoveryStub(tuple()))
        container.inject_mock_feature_detector(
            _FeatureStub({"task_files_scanned": 1, "tasks_scanned": 2})
        )

        observed_scan_options: list[dict[str, Any]] = []

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda scan_options: (
                observed_scan_options.append(scan_options),
                _context_payload(),
            )[1],
        )
        result = context.orchestrate_scan()

    assert recorder.calls == []
    assert observed_scan_options == [options]
    assert result["metadata"]["scan_policy_warnings"] == options["scan_policy_warnings"]


def test_fsrc_scanner_context_dedupes_canonical_policy_warnings() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")

        ingress_warning = {
            "code": "sample_policy_warning",
            "message": "Sample warning for test.",
            "detail": {
                "scope": "test",
            },
        }
        metadata_only_warning = {
            "code": "metadata_only_warning",
            "message": "Metadata-local warning.",
            "detail": {"scope": "prepare_scan_context"},
        }
        options = _canonical_scan_options()
        options["scan_policy_warnings"] = [ingress_warning]
        recorder = _BuildOptionsRecorder(options)
        container = di_module.DIContainer(
            role_path=options["role_path"], scan_options=options
        )
        container.inject_mock_variable_discovery(_DiscoveryStub(tuple()))
        container.inject_mock_feature_detector(
            _FeatureStub({"task_files_scanned": 1, "tasks_scanned": 2})
        )

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: {
                **_context_payload(),
                "metadata": {
                    "marker_prefix": "NOTE",
                    "scan_policy_warnings": [
                        ingress_warning,
                        metadata_only_warning,
                    ],
                },
            },
        )
        result = context.orchestrate_scan()

    assert recorder.calls == []
    assert result["metadata"]["scan_policy_warnings"] == [
        ingress_warning,
        metadata_only_warning,
    ]


def test_fsrc_scanner_context_underscore_filter_uses_canonical_ingress_state() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")

        options = _canonical_scan_options()
        options["ignore_unresolved_internal_underscore_references"] = False
        options["policy_context"] = {
            "include_underscore_prefixed_references": False,
        }
        recorder = _BuildOptionsRecorder(options)
        container = di_module.DIContainer(
            role_path=options["role_path"], scan_options=options
        )
        container.inject_mock_variable_discovery(_DiscoveryStub(tuple()))
        container.inject_mock_feature_detector(
            _FeatureStub({"task_files_scanned": 1, "tasks_scanned": 2})
        )

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: {
                **_context_payload(),
                "display_variables": {
                    "_internal_value": {
                        "is_unresolved": True,
                        "source": "tasks/main.yml",
                    },
                    "public_value": {
                        "is_unresolved": True,
                        "source": "tasks/main.yml",
                    },
                },
                "metadata": {
                    "marker_prefix": "NOTE",
                    "variable_insights": [
                        {"name": "_internal_value", "is_unresolved": True},
                        {"name": "public_value", "is_unresolved": True},
                    ],
                },
            },
        )
        result = context.orchestrate_scan()

    assert recorder.calls == []
    assert "_internal_value" in result["display_variables"]
    assert (
        result["metadata"].get("ignore_unresolved_internal_underscore_references")
        is not True
    )
    assert "underscore_filtered_unresolved_count" not in result["metadata"]
    assert result["metadata"]["variable_insights"] == [
        {"name": "_internal_value", "is_unresolved": True},
        {"name": "public_value", "is_unresolved": True},
    ]


def test_fsrc_scanner_context_best_effort_records_error_envelope() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")
        errors_module = importlib.import_module("prism.errors")

        options = _canonical_scan_options()
        options["strict_phase_failures"] = False
        recorder = _BuildOptionsRecorder(options)
        container = di_module.DIContainer(
            role_path=options["role_path"], scan_options=options
        )
        container.inject_mock_variable_discovery(
            _DiscoveryStub(
                errors_module.PrismRuntimeError(
                    code="role_scan_runtime_error",
                    category="runtime",
                    message="boom",
                )
            )
        )
        container.inject_mock_feature_detector(_FeatureStub({"task_files_scanned": 0}))

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: _context_payload(),
        )
        result = context.orchestrate_scan()

    assert result["metadata"]["scan_degraded"] is True
    assert result["metadata"]["scan_errors"] == [
        {
            "phase": "discovery",
            "error_type": "PrismRuntimeError",
            "message": "role_scan_runtime_error: boom",
        }
    ]


def test_fsrc_scanner_context_strict_mode_reraises_recoverable_phase_error() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")
        errors_module = importlib.import_module("prism.errors")

        options = _canonical_scan_options()
        recorder = _BuildOptionsRecorder(options)
        container = di_module.DIContainer(
            role_path=options["role_path"], scan_options=options
        )
        container.inject_mock_variable_discovery(
            _DiscoveryStub(
                errors_module.PrismRuntimeError(
                    code="role_scan_runtime_error",
                    category="runtime",
                    message="strict",
                )
            )
        )
        container.inject_mock_feature_detector(_FeatureStub({"task_files_scanned": 0}))

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: _context_payload(),
        )

        with pytest.raises(errors_module.PrismRuntimeError, match="strict"):
            context.orchestrate_scan()


def test_fsrc_scanner_context_missing_required_keys_raises_shape_error() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")

        options = _canonical_scan_options()
        options.pop("style_readme_path")
        recorder = _BuildOptionsRecorder(options)
        container = di_module.DIContainer(role_path="/tmp/role", scan_options=options)
        container.inject_mock_variable_discovery(_DiscoveryStub(tuple()))
        container.inject_mock_feature_detector(_FeatureStub({"task_files_scanned": 0}))

        context = core_module.ScannerContext(
            di=container,
            role_path="/tmp/role",
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: _context_payload(),
        )

        with pytest.raises(
            ValueError, match="scan_options missing required canonical keys"
        ):
            context.orchestrate_scan()


def test_fsrc_di_plugin_factories_are_explicit_and_overridable() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")

        class _VarPlugin:
            pass

        class _FeaturePlugin:
            pass

        class _DocPlugin:
            pass

        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
            factory_overrides={
                "variable_discovery_plugin_factory": lambda *_args: _VarPlugin(),
                "feature_detection_plugin_factory": lambda *_args: _FeaturePlugin(),
                "comment_driven_doc_plugin_factory": lambda *_args: _DocPlugin(),
            },
        )

        assert (
            container.factory_variable_discovery_plugin().__class__.__name__
            == "_VarPlugin"
        )
        assert (
            container.factory_feature_detection_plugin().__class__.__name__
            == "_FeaturePlugin"
        )
        assert (
            container.factory_comment_driven_doc_plugin().__class__.__name__
            == "_DocPlugin"
        )

        container.clear_mocks()
        container.inject_mock_variable_discovery_plugin("var-plugin")
        container.inject_mock_feature_detection_plugin("feature-plugin")
        container.inject_mock_comment_driven_doc_plugin("doc-plugin")

        assert container.factory_variable_discovery_plugin() == "var-plugin"
        assert container.factory_feature_detection_plugin() == "feature-plugin"
        assert container.factory_comment_driven_doc_plugin() == "doc-plugin"


def test_fsrc_scanner_context_requires_prepared_policy_bundle_without_mutating_ingress_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")

        options = _canonical_scan_options()
        options.pop("prepared_policy_bundle")
        recorder = _BuildOptionsRecorder(dict(options))
        container = di_module.DIContainer(
            role_path=options["role_path"],
            scan_options=options,
            factory_overrides={
                "feature_detector_factory": (
                    lambda _di, _role_path, _scan_options: _FeatureStub(
                        {"task_files_scanned": 0, "tasks_scanned": 0}
                    )
                ),
            },
        )
        scanner_context_module = importlib.import_module(
            "prism.scanner_core.scanner_context"
        )
        ensure_calls: list[dict[str, Any]] = []

        def _record_ensure_prepared_policy_bundle(
            *, scan_options: dict[str, Any], di: object | None
        ) -> dict[str, Any]:
            del di
            ensure_calls.append(dict(scan_options))
            scan_options["prepared_policy_bundle"] = _prepared_policy_bundle()
            return scan_options["prepared_policy_bundle"]

        monkeypatch.setattr(
            scanner_context_module,
            "ensure_prepared_policy_bundle",
            _record_ensure_prepared_policy_bundle,
        )

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: _context_payload(),
        )

        with pytest.raises(ValueError, match="prepared_policy_bundle"):
            context.orchestrate_scan()

    assert ensure_calls == []
    assert "prepared_policy_bundle" not in options
    assert recorder.calls == []


def test_fsrc_scanner_context_prepared_policy_bundle_rejects_invalid_bundle() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")

        options = _canonical_scan_options()
        options["prepared_policy_bundle"] = {
            "task_line_parsing": object(),
            "jinja_analysis": object(),
        }
        recorder = _BuildOptionsRecorder(dict(options))
        container = di_module.DIContainer(
            role_path=options["role_path"],
            scan_options=options,
        )
        container.inject_mock_variable_discovery(_DiscoveryStub(tuple()))
        container.inject_mock_feature_detector(
            _FeatureStub({"task_files_scanned": 1, "tasks_scanned": 2})
        )

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: _context_payload(),
        )

        result = context.orchestrate_scan()

    assert result["role_name"] == "demo"
    assert recorder.calls == []


def test_fsrc_scan_request_prepared_policy_bundle_rejects_missing_task_meta_keys_at_ingress() -> (
    None
):
    class _MissingTaskMetaKeysPolicy:
        TASK_INCLUDE_KEYS = {"include_tasks"}
        ROLE_INCLUDE_KEYS = {"include_role"}
        INCLUDE_VARS_KEYS = {"include_vars"}
        SET_FACT_KEYS = {"set_fact"}
        TASK_BLOCK_KEYS = {"block"}

        @staticmethod
        def detect_task_module(_task: dict[str, Any]) -> str:
            return "debug"

    with _prefer_fsrc_prism_on_sys_path():
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )

        options = {
            "prepared_policy_bundle": {
                "task_line_parsing": _MissingTaskMetaKeysPolicy(),
                "jinja_analysis": _PreparedJinjaPolicy(),
            }
        }

        with pytest.raises(ValueError, match="TASK_META_KEYS"):
            bundle_resolver.ensure_prepared_policy_bundle(scan_options=options, di=None)


def test_fsrc_scanner_context_emits_dynamic_include_blocker_facts_with_contract_counts_and_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")
        blocker_eval_module = importlib.import_module(
            "prism.scanner_core.blocker_fact_evaluator"
        )

        options = _canonical_scan_options()
        options["fail_on_unconstrained_dynamic_includes"] = True
        options["exclude_path_patterns"] = ["tasks/generated/**"]
        recorder = _BuildOptionsRecorder(options)
        container = di_module.DIContainer(
            role_path=options["role_path"],
            scan_options=options,
        )
        container.inject_mock_variable_discovery(_DiscoveryStub(tuple()))
        container.inject_mock_feature_detector(
            _FeatureStub({"task_files_scanned": 1, "tasks_scanned": 2})
        )

        monkeypatch.setattr(
            blocker_eval_module,
            "collect_unconstrained_dynamic_task_includes",
            lambda *_args, **_kwargs: [
                {"task_file": "tasks/main.yml", "include_target": "{{ include_task }}"},
                {
                    "task_file": "tasks/extra.yml",
                    "include_target": "{{ include_other }}",
                },
            ],
        )
        monkeypatch.setattr(
            blocker_eval_module,
            "collect_unconstrained_dynamic_role_includes",
            lambda *_args, **_kwargs: [
                {"task_file": "tasks/main.yml", "include_target": "{{ role_name }}"}
            ],
        )

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: {
                **_context_payload(),
                "metadata": {
                    "features": {
                        "task_files_scanned": 1,
                        "tasks_scanned": 2,
                        "yaml_like_task_annotations": 0,
                    }
                },
            },
        )

        result = context.orchestrate_scan()

    blocker_facts = result["metadata"]["scan_policy_blocker_facts"]
    assert blocker_facts["dynamic_includes"] == {
        "enabled": True,
        "task_count": 2,
        "role_count": 1,
        "total_count": 3,
    }
    assert blocker_facts["yaml_like_annotations"] == {
        "enabled": False,
        "count": 0,
    }
    assert blocker_facts["provenance"] == {
        "role_path": "/tmp/role",
        "exclude_path_patterns": ["tasks/generated/**"],
        "metadata_feature_source": "metadata.features.yaml_like_task_annotations",
        "dynamic_include_sources": [
            "scanner_core.dynamic_include_audit.collect_unconstrained_dynamic_task_includes",
            "scanner_core.dynamic_include_audit.collect_unconstrained_dynamic_role_includes",
        ],
    }
    assert "scan_policy_warnings" not in result["metadata"]


def test_fsrc_scanner_context_emits_yaml_like_blocker_facts_with_contract_counts_and_provenance() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")

        options = _canonical_scan_options()
        options["fail_on_yaml_like_task_annotations"] = True
        recorder = _BuildOptionsRecorder(options)
        container = di_module.DIContainer(
            role_path=options["role_path"],
            scan_options=options,
        )
        container.inject_mock_variable_discovery(_DiscoveryStub(tuple()))
        container.inject_mock_feature_detector(
            _FeatureStub({"task_files_scanned": 1, "tasks_scanned": 2})
        )

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: {
                **_context_payload(),
                "metadata": {
                    "features": {
                        "task_files_scanned": 1,
                        "tasks_scanned": 2,
                        "yaml_like_task_annotations": 4,
                    }
                },
            },
        )

        result = context.orchestrate_scan()

    blocker_facts = result["metadata"]["scan_policy_blocker_facts"]
    assert blocker_facts["dynamic_includes"] == {
        "enabled": False,
        "task_count": 0,
        "role_count": 0,
        "total_count": 0,
    }
    assert blocker_facts["yaml_like_annotations"] == {
        "enabled": True,
        "count": 4,
    }
    assert blocker_facts["provenance"] == {
        "role_path": "/tmp/role",
        "exclude_path_patterns": None,
        "metadata_feature_source": "metadata.features.yaml_like_task_annotations",
        "dynamic_include_sources": [
            "scanner_core.dynamic_include_audit.collect_unconstrained_dynamic_task_includes",
            "scanner_core.dynamic_include_audit.collect_unconstrained_dynamic_role_includes",
        ],
    }
    assert "scan_policy_warnings" not in result["metadata"]


def test_fsrc_scanner_context_does_not_translate_blocker_outcomes_locally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")
        blocker_eval_module = importlib.import_module(
            "prism.scanner_core.blocker_fact_evaluator"
        )

        options = _canonical_scan_options()
        options["strict_phase_failures"] = True
        options["fail_on_unconstrained_dynamic_includes"] = True
        options["fail_on_yaml_like_task_annotations"] = True
        recorder = _BuildOptionsRecorder(options)
        container = di_module.DIContainer(
            role_path=options["role_path"],
            scan_options=options,
        )
        container.inject_mock_variable_discovery(_DiscoveryStub(tuple()))
        container.inject_mock_feature_detector(
            _FeatureStub({"task_files_scanned": 1, "tasks_scanned": 2})
        )

        monkeypatch.setattr(
            blocker_eval_module,
            "collect_unconstrained_dynamic_task_includes",
            lambda *_args, **_kwargs: [
                {"task_file": "tasks/main.yml", "include_target": "{{ include_task }}"}
            ],
        )
        monkeypatch.setattr(
            blocker_eval_module,
            "collect_unconstrained_dynamic_role_includes",
            lambda *_args, **_kwargs: [
                {"task_file": "tasks/main.yml", "include_target": "{{ role_name }}"}
            ],
        )

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: {
                **_context_payload(),
                "metadata": {
                    "features": {
                        "task_files_scanned": 1,
                        "tasks_scanned": 2,
                        "yaml_like_task_annotations": 2,
                    }
                },
            },
        )

        result = context.orchestrate_scan()

    blocker_facts = result["metadata"]["scan_policy_blocker_facts"]
    assert blocker_facts["dynamic_includes"]["total_count"] == 2
    assert blocker_facts["yaml_like_annotations"]["count"] == 2
    assert "scan_policy_warnings" not in result["metadata"]


def test_fsrc_scanner_core_builds_non_collection_execution_request() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")

        class _RecordingVariableDiscovery:
            def __init__(
                self,
                _di: object,
                _role_path: str,
                scan_options: dict[str, Any],
            ) -> None:
                self._scan_options = scan_options

            def discover(self) -> tuple[dict[str, Any], ...]:
                prepared_bundle = self._scan_options.get("prepared_policy_bundle")
                assert isinstance(prepared_bundle, dict)
                assert callable(
                    getattr(
                        prepared_bundle.get("task_line_parsing"),
                        "detect_task_module",
                        None,
                    )
                )
                assert callable(
                    getattr(
                        prepared_bundle.get("jinja_analysis"),
                        "collect_undeclared_jinja_variables",
                        None,
                    )
                )
                return (
                    {
                        "name": "demo_var",
                        "type": "str",
                        "default": "value",
                        "source": "defaults/main.yml",
                        "required": False,
                        "documented": True,
                        "secret": False,
                        "is_unresolved": False,
                        "is_ambiguous": False,
                        "uncertainty_reason": None,
                    },
                )

        class _RecordingFeatureDetector:
            def __init__(
                self,
                _di: object,
                _role_path: str,
                _scan_options: dict[str, Any],
            ) -> None:
                pass

            def detect(self) -> dict[str, Any]:
                return {
                    "task_files_scanned": 1,
                    "tasks_scanned": 2,
                    "external_collections": "community.general",
                }

        class _DocPlugin:
            @staticmethod
            def extract_role_notes_from_comments(
                role_path: str,
                *,
                exclude_paths: list[str] | None = None,
            ) -> list[str]:
                del exclude_paths
                return [f"notes-for:{role_path}"]

        class _Registry:
            pass

        def _build_run_scan_options_canonical(**kwargs: Any) -> dict[str, Any]:
            return {
                "role_path": kwargs["role_path"],
                "role_name_override": kwargs["role_name_override"],
                "readme_config_path": kwargs["readme_config_path"],
                "policy_config_path": kwargs["policy_config_path"],
                "include_vars_main": kwargs["include_vars_main"],
                "exclude_path_patterns": kwargs["exclude_path_patterns"],
                "detailed_catalog": kwargs["detailed_catalog"],
                "include_task_parameters": kwargs["include_task_parameters"],
                "include_task_runbooks": kwargs["include_task_runbooks"],
                "inline_task_runbooks": kwargs["inline_task_runbooks"],
                "include_collection_checks": kwargs["include_collection_checks"],
                "keep_unknown_style_sections": kwargs["keep_unknown_style_sections"],
                "adopt_heading_mode": kwargs["adopt_heading_mode"],
                "vars_seed_paths": kwargs["vars_seed_paths"],
                "style_readme_path": kwargs["style_readme_path"],
                "style_source_path": kwargs["style_source_path"],
                "style_guide_skeleton": kwargs["style_guide_skeleton"],
                "compare_role_path": kwargs["compare_role_path"],
                "fail_on_unconstrained_dynamic_includes": kwargs[
                    "fail_on_unconstrained_dynamic_includes"
                ],
                "fail_on_yaml_like_task_annotations": kwargs[
                    "fail_on_yaml_like_task_annotations"
                ],
                "ignore_unresolved_internal_underscore_references": kwargs[
                    "ignore_unresolved_internal_underscore_references"
                ],
                "policy_context": kwargs["policy_context"],
                "yaml_parse_failures": [],
            }

        request = core_module.build_non_collection_run_scan_execution_request(
            role_path="/tmp/demo-role",
            role_name_override="demo-role",
            readme_config_path=None,
            policy_config_path=None,
            concise_readme=False,
            scanner_report_output=None,
            include_vars_main=True,
            include_scanner_report_link=True,
            exclude_path_patterns=None,
            detailed_catalog=False,
            include_task_parameters=True,
            include_task_runbooks=True,
            inline_task_runbooks=True,
            include_collection_checks=True,
            keep_unknown_style_sections=True,
            adopt_heading_mode=None,
            vars_seed_paths=None,
            style_readme_path=None,
            style_source_path=None,
            style_guide_skeleton=False,
            compare_role_path=None,
            fail_on_unconstrained_dynamic_includes=None,
            fail_on_yaml_like_task_annotations=None,
            ignore_unresolved_internal_underscore_references=None,
            policy_context=None,
            strict_phase_failures=False,
            scan_pipeline_plugin=None,
            validate_role_path_fn=lambda role_path: role_path,
            extract_role_description_fn=lambda _role_root, role_name: (
                f"desc:{role_name}"
            ),
            build_run_scan_options_canonical_fn=_build_run_scan_options_canonical,
            di_container_cls=core_module.DIContainer,
            feature_detector_cls=_RecordingFeatureDetector,
            scanner_context_cls=core_module.ScannerContext,
            variable_discovery_cls=_RecordingVariableDiscovery,
            resolve_comment_driven_documentation_plugin_fn=(lambda _di: _DocPlugin()),
            default_plugin_registry=_Registry(),
        )

        payload = request.build_payload_fn()

    prepared_bundle = request.scan_options.get("prepared_policy_bundle")
    assert request.role_path == "/tmp/demo-role"
    assert request.strict_mode is False
    assert isinstance(prepared_bundle, dict)
    assert callable(
        getattr(prepared_bundle["task_line_parsing"], "detect_task_module", None)
    )
    assert callable(
        getattr(
            prepared_bundle["jinja_analysis"],
            "collect_undeclared_jinja_variables",
            None,
        )
    )
    assert payload["role_name"] == "demo-role"
    assert payload["description"] == "desc:demo-role"
    assert payload["display_variables"]["demo_var"]["default"] == "value"
    assert payload["metadata"]["role_notes"] == ["notes-for:/tmp/demo-role"]
    assert payload["metadata"]["features"]["task_files_scanned"] == 1
