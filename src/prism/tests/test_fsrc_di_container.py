"""Focused DI container checks for the fsrc package lane."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


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


class _StubScannerContext:
    def __init__(
        self,
        *,
        di: Any,
        role_path: str,
        scan_options: dict[str, Any],
        prepare_scan_context_fn: Any,
    ) -> None:
        self.di = di
        self.role_path = role_path
        self.scan_options = scan_options
        self.prepare_scan_context_fn = prepare_scan_context_fn


def _prepare_scan_context_stub() -> dict[str, object]:
    return {"ok": True}


def test_fsrc_di_container_importable_from_module_and_package_root() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        core_module = importlib.import_module("prism.scanner_core")

    assert hasattr(di_module, "DIContainer")
    assert hasattr(core_module, "DIContainer")


def test_fsrc_di_container_instantiates_and_validates_inputs() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"include_vars_main": True},
        )

        with pytest.raises(ValueError, match="role_path must not be empty"):
            di_module.DIContainer(role_path="", scan_options={})

        with pytest.raises(ValueError, match="scan_options must not be None"):
            di_module.DIContainer(role_path="/tmp/role", scan_options=None)

    assert container is not None


def test_fsrc_di_container_scanner_context_factory_requires_wiring() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(role_path="/tmp/role", scan_options={})

        with pytest.raises(RuntimeError, match="factory_scanner_context is disabled"):
            container.factory_scanner_context()


def test_fsrc_di_container_composes_scanner_context_when_wired() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        options = {"role_name_override": None}
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options=options,
            scanner_context_wiring={
                "scanner_context_cls": _StubScannerContext,
                "prepare_scan_context_fn": _prepare_scan_context_stub,
            },
        )

        context = container.factory_scanner_context()

    assert isinstance(context, _StubScannerContext)
    assert context.di is container
    assert context.role_path == "/tmp/role"
    assert context.scan_options is options
    assert context.prepare_scan_context_fn is _prepare_scan_context_stub


def test_fsrc_di_container_variable_row_builder_is_cached() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(role_path="/tmp/role", scan_options={})
        first = container.factory_variable_row_builder()
        second = container.factory_variable_row_builder()

    assert first is second


def test_fsrc_di_container_task_annotation_policy_factory_override() -> None:
    def _factory(
        _container: object, _role_path: str, _options: dict[str, object]
    ) -> str:
        return "task-annotation-policy"

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={},
            factory_overrides={
                "task_annotation_policy_plugin_factory": _factory,
            },
        )

    assert container.factory_task_annotation_policy_plugin() == "task-annotation-policy"


def test_fsrc_di_container_task_line_parsing_policy_factory_override() -> None:
    def _factory(
        _container: object, _role_path: str, _options: dict[str, object]
    ) -> str:
        return "task-line-parsing-policy"

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={},
            factory_overrides={
                "task_line_parsing_policy_plugin_factory": _factory,
            },
        )

    assert (
        container.factory_task_line_parsing_policy_plugin()
        == "task-line-parsing-policy"
    )


def test_fsrc_di_container_task_traversal_policy_factory_override() -> None:
    def _factory(
        _container: object, _role_path: str, _options: dict[str, object]
    ) -> str:
        return "task-traversal-policy"

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={},
            factory_overrides={
                "task_traversal_policy_plugin_factory": _factory,
            },
        )

    assert container.factory_task_traversal_policy_plugin() == "task-traversal-policy"


def test_fsrc_di_container_variable_extractor_policy_factory_override() -> None:
    def _factory(
        _container: object, _role_path: str, _options: dict[str, object]
    ) -> str:
        return "variable-extractor-policy"

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={},
            factory_overrides={
                "variable_extractor_policy_plugin_factory": _factory,
            },
        )

    assert (
        container.factory_variable_extractor_policy_plugin()
        == "variable-extractor-policy"
    )


def test_fsrc_di_container_yaml_parsing_policy_factory_override() -> None:
    def _factory(
        _container: object, _role_path: str, _options: dict[str, object]
    ) -> str:
        return "yaml-parsing-policy"

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={},
            factory_overrides={
                "yaml_parsing_policy_plugin_factory": _factory,
            },
        )

    assert container.factory_yaml_parsing_policy_plugin() == "yaml-parsing-policy"


def test_fsrc_di_container_jinja_analysis_policy_factory_override() -> None:
    def _factory(
        _container: object, _role_path: str, _options: dict[str, object]
    ) -> str:
        return "jinja-analysis-policy"

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={},
            factory_overrides={
                "jinja_analysis_policy_plugin_factory": _factory,
            },
        )

    assert container.factory_jinja_analysis_policy_plugin() == "jinja-analysis-policy"
