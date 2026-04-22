"""Focused precedence and strategy-ownership tests for task-annotation parsing."""

from __future__ import annotations

import importlib
import pytest
import sys
from contextlib import contextmanager
from pathlib import Path

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


class _DIPolicy:
    @staticmethod
    def extract_task_annotations_for_file(
        lines: list[str],
        marker_prefix: str = "prism",
        include_task_index: bool = False,
    ) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
        del lines
        del marker_prefix
        del include_task_index
        return [{"kind": "di", "text": "from-di"}], {}


class _RegistryPolicy:
    @staticmethod
    def extract_task_annotations_for_file(
        lines: list[str],
        marker_prefix: str = "prism",
        include_task_index: bool = False,
    ) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
        del lines
        del marker_prefix
        del include_task_index
        return [{"kind": "registry", "text": "from-registry"}], {}


class _DIContainer:
    def __init__(self) -> None:
        self.scan_options: dict = {"role_path": "/tmp", "exclude_path_patterns": None}

    def factory_task_annotation_policy_plugin(self) -> _DIPolicy:
        return _DIPolicy()


def _sample_lines() -> list[str]:
    return [
        "# prism ~ task: Example task | runbook: sample",
        "- name: Example task",
    ]


def test_task_parser_annotation_policy_precedence_di_over_registry() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        parser_module = importlib.import_module(
            "prism.scanner_extract.task_annotation_parsing"
        )
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

        plugin_registry = registry_module.plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_annotation_parsing")

        try:
            plugin_registry.register_extract_policy_plugin(
                "task_annotation_parsing",
                _RegistryPolicy,
            )
            container = _DIContainer()
            bundle_resolver.ensure_prepared_policy_bundle(
                scan_options=container.scan_options, di=container
            )
            marker_prefix = container.scan_options["prepared_policy_bundle"][
                "comment_doc_marker_prefix"
            ]
            implicit, explicit = parser_module._extract_task_annotations_for_file(
                _sample_lines(),
                marker_prefix=marker_prefix,
                di=container,
            )
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop(
                    "task_annotation_parsing",
                    None,
                )
            else:
                plugin_registry.register_extract_policy_plugin(
                    "task_annotation_parsing",
                    original,
                )

    assert explicit == {}
    assert implicit == [{"kind": "di", "text": "from-di"}]


def test_task_parser_annotation_policy_precedence_registry_over_fallback() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        parser_module = importlib.import_module(
            "prism.scanner_extract.task_annotation_parsing"
        )
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

        plugin_registry = registry_module.plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_annotation_parsing")

        try:
            plugin_registry.register_extract_policy_plugin(
                "task_annotation_parsing",
                _RegistryPolicy,
            )
            options: dict = {"role_path": "/tmp", "exclude_path_patterns": None}
            bundle_resolver.ensure_prepared_policy_bundle(scan_options=options, di=None)

            class _OptionsContainer:
                def __init__(self, opts: dict) -> None:
                    self.scan_options = opts

            container = _OptionsContainer(options)
            marker_prefix = options["prepared_policy_bundle"][
                "comment_doc_marker_prefix"
            ]
            implicit, explicit = parser_module._extract_task_annotations_for_file(
                _sample_lines(),
                marker_prefix=marker_prefix,
                di=container,
            )
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop(
                    "task_annotation_parsing",
                    None,
                )
            else:
                plugin_registry.register_extract_policy_plugin(
                    "task_annotation_parsing",
                    original,
                )

    assert explicit == {}
    assert implicit == [{"kind": "registry", "text": "from-registry"}]


def test_task_parser_annotation_policy_precedence_fallback_when_no_di_or_registry() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        parser_module = importlib.import_module(
            "prism.scanner_extract.task_annotation_parsing"
        )
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

        plugin_registry = registry_module.plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_annotation_parsing")

        try:
            plugin_registry._extract_policy_plugins.pop("task_annotation_parsing", None)
            with pytest.raises(ValueError):
                parser_module._extract_task_annotations_for_file(
                    _sample_lines(),
                    marker_prefix="prism",
                    di=None,
                )
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop(
                    "task_annotation_parsing",
                    None,
                )
            else:
                plugin_registry.register_extract_policy_plugin(
                    "task_annotation_parsing",
                    original,
                )


def test_annotation_policy_methods_delegate_to_strategy_module(monkeypatch) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        strategy_module = importlib.import_module(
            "prism.scanner_plugins.ansible.task_annotation_strategy"
        )
        policy_module = importlib.import_module(
            "prism.scanner_plugins.ansible.extract_policies"
        )

        monkeypatch.setattr(
            strategy_module,
            "split_task_annotation_label",
            lambda _text: ("delegated", "label"),
        )

        value = (
            policy_module.AnsibleTaskAnnotationPolicyPlugin.split_task_annotation_label(
                "ignored"
            )
        )

    assert value == ("delegated", "label")
