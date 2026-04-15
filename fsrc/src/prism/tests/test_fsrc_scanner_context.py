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
    assert len(recorder.calls) == 1


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


def test_fsrc_scanner_context_prepares_policy_bundle_before_discovery() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        core_module = importlib.import_module("prism.scanner_core")
        di_module = importlib.import_module("prism.scanner_core.di")

        class _PreparedTaskLinePolicy:
            TASK_INCLUDE_KEYS = {"include_tasks"}
            ROLE_INCLUDE_KEYS = {"include_role"}
            INCLUDE_VARS_KEYS = {"include_vars"}
            SET_FACT_KEYS = {"set_fact"}
            TASK_BLOCK_KEYS = {"block"}
            TASK_META_KEYS = {"meta"}

            @staticmethod
            def detect_task_module(_task: dict) -> str:
                return "debug"

        class _PreparedJinjaPolicy:
            @staticmethod
            def collect_undeclared_jinja_variables(_text: str) -> set[str]:
                return set()

        class _DiscoveryRecorder:
            def __init__(self, scan_options: dict[str, Any]) -> None:
                self._scan_options = scan_options

            def discover(self) -> tuple[Any, ...]:
                prepared_bundle = self._scan_options.get("prepared_policy_bundle")
                assert isinstance(prepared_bundle, dict)
                assert prepared_bundle["task_line_parsing"] is task_line_policy
                assert prepared_bundle["jinja_analysis"] is jinja_policy
                return tuple()

        options = _canonical_scan_options()
        recorder = _BuildOptionsRecorder(dict(options))
        task_line_policy = _PreparedTaskLinePolicy()
        jinja_policy = _PreparedJinjaPolicy()
        container = di_module.DIContainer(
            role_path=options["role_path"],
            scan_options=options,
            factory_overrides={
                "variable_discovery_factory": (
                    lambda _di, _role_path, scan_options: _DiscoveryRecorder(
                        scan_options
                    )
                ),
                "feature_detector_factory": (
                    lambda _di, _role_path, _scan_options: _FeatureStub(
                        {"task_files_scanned": 0, "tasks_scanned": 0}
                    )
                ),
                "task_line_parsing_policy_plugin_factory": (
                    lambda *_args: task_line_policy
                ),
                "jinja_analysis_policy_plugin_factory": (lambda *_args: jinja_policy),
            },
        )

        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
            build_run_scan_options_fn=recorder,
            prepare_scan_context_fn=lambda _scan_options: _context_payload(),
        )
        context.orchestrate_scan()

    prepared_bundle = recorder.calls[0].get("prepared_policy_bundle")
    assert isinstance(prepared_bundle, dict)
    assert prepared_bundle["task_line_parsing"] is task_line_policy
    assert prepared_bundle["jinja_analysis"] is jinja_policy
