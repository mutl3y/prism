"""Coverage tests for scanner plugin registry utility module."""

from types import ModuleType

import pytest

from prism.scanner_plugins.registry import PluginRegistry, plugin_registry


class _PluginA:
    pass


class _PluginB:
    pass


def test_registry_constructor_starts_empty() -> None:
    registry = PluginRegistry()

    assert registry.list_variable_discovery_plugins() == []
    assert registry.list_feature_detection_plugins() == []
    assert registry.list_output_orchestration_plugins() == []
    assert registry.list_scan_pipeline_plugins() == []
    assert registry.list_comment_driven_doc_plugins() == []

    assert registry.get_variable_discovery_plugin("missing") is None
    assert registry.get_feature_detection_plugin("missing") is None
    assert registry.get_output_orchestration_plugin("missing") is None
    assert registry.get_scan_pipeline_plugin("missing") is None
    assert registry.get_comment_driven_doc_plugin("missing") is None


def test_registry_register_get_and_list_all_plugin_buckets() -> None:
    registry = PluginRegistry()

    registry.register_variable_discovery_plugin("var", _PluginA)
    registry.register_feature_detection_plugin("feat", _PluginA)
    registry.register_output_orchestration_plugin("out", _PluginA)
    registry.register_scan_pipeline_plugin("scan", _PluginB)
    registry.register_comment_driven_doc_plugin("doc", _PluginB)

    assert registry.get_variable_discovery_plugin("var") is _PluginA
    assert registry.get_feature_detection_plugin("feat") is _PluginA
    assert registry.get_output_orchestration_plugin("out") is _PluginA
    assert registry.get_scan_pipeline_plugin("scan") is _PluginB
    assert registry.get_comment_driven_doc_plugin("doc") is _PluginB

    assert registry.list_variable_discovery_plugins() == ["var"]
    assert registry.list_feature_detection_plugins() == ["feat"]
    assert registry.list_output_orchestration_plugins() == ["out"]
    assert registry.list_scan_pipeline_plugins() == ["scan"]
    assert registry.list_comment_driven_doc_plugins() == ["doc"]


def test_load_plugin_from_module_success_and_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = PluginRegistry()
    fake_module = ModuleType("fake.module")
    setattr(fake_module, "FakePlugin", _PluginA)
    calls = {"count": 0}

    def _import_module(name: str) -> ModuleType:
        calls["count"] += 1
        assert name == "fake.module"
        return fake_module

    monkeypatch.setattr(
        "prism.scanner_plugins.registry.importlib.import_module", _import_module
    )

    loaded = registry.load_plugin_from_module("fake.module", "FakePlugin")
    loaded_cached = registry.load_plugin_from_module("fake.module", "OtherNameIgnored")

    assert loaded is _PluginA
    assert loaded_cached is _PluginA
    assert calls["count"] == 1


def test_load_plugin_from_module_raises_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = PluginRegistry()

    def _raise_import_error(_: str) -> ModuleType:
        raise ImportError("boom")

    monkeypatch.setattr(
        "prism.scanner_plugins.registry.importlib.import_module", _raise_import_error
    )

    with pytest.raises(ImportError, match="boom"):
        registry.load_plugin_from_module("missing.module", "Plugin")


def test_load_plugin_from_module_raises_attribute_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = PluginRegistry()
    fake_module = ModuleType("fake.no.class")

    def _import_module(_: str) -> ModuleType:
        return fake_module

    monkeypatch.setattr(
        "prism.scanner_plugins.registry.importlib.import_module", _import_module
    )

    with pytest.raises(AttributeError):
        registry.load_plugin_from_module("fake.no.class", "MissingClass")


def test_global_registry_instance_exposes_public_registry_type() -> None:
    assert isinstance(plugin_registry, PluginRegistry)
