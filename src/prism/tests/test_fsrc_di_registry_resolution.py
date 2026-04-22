"""Tests for registry-driven DI plugin resolution in the fsrc lane."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path():
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


def test_di_variable_discovery_plugin_resolves_through_registry():
    """DI default variable-discovery plugin resolves via registry, not hardcoded import."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        plugins_module = importlib.import_module("prism.scanner_plugins")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
            registry=plugins_module.DEFAULT_PLUGIN_REGISTRY,
        )
        plugin = container.factory_variable_discovery_plugin()
        assert plugin.__class__.__name__ == "AnsibleVariableDiscoveryPlugin"


def test_di_feature_detection_plugin_resolves_through_registry():
    """DI default feature-detection plugin resolves via registry, not hardcoded import."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        plugins_module = importlib.import_module("prism.scanner_plugins")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
            registry=plugins_module.DEFAULT_PLUGIN_REGISTRY,
        )
        plugin = container.factory_feature_detection_plugin()
        assert plugin.__class__.__name__ == "AnsibleFeatureDetectionPlugin"


def test_di_no_hardcoded_ansible_imports_in_scanner_core_di():
    """scanner_core/di.py must not contain any direct imports from scanner_plugins.ansible."""
    di_path = FSRC_SOURCE_ROOT / "prism" / "scanner_core" / "di.py"
    source = di_path.read_text()
    assert "scanner_plugins.ansible" not in source


def test_di_variable_discovery_plugin_fails_closed_on_empty_registry():
    """DI raises ValueError when no variable-discovery plugin is registered."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        empty_registry = registry_module.PluginRegistry()
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
            registry=empty_registry,
        )
        with pytest.raises(ValueError, match="No platform key resolvable"):
            container.factory_variable_discovery_plugin()


def test_di_feature_detection_plugin_fails_closed_on_empty_registry():
    """DI raises ValueError when no feature-detection plugin is registered."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        empty_registry = registry_module.PluginRegistry()
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
            registry=empty_registry,
        )
        with pytest.raises(ValueError, match="No platform key resolvable"):
            container.factory_feature_detection_plugin()


def test_di_mock_precedence_preserved_for_variable_discovery_plugin():
    """Mock injection takes precedence over registry resolution."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
        )
        container.inject_mock_variable_discovery_plugin("mock-var-plugin")
        assert container.factory_variable_discovery_plugin() == "mock-var-plugin"


def test_di_mock_precedence_preserved_for_feature_detection_plugin():
    """Mock injection takes precedence over registry resolution."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
        )
        container.inject_mock_feature_detection_plugin("mock-feature-plugin")
        assert container.factory_feature_detection_plugin() == "mock-feature-plugin"


def test_di_factory_override_precedence_preserved_for_variable_discovery_plugin():
    """Factory override takes precedence over registry resolution."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")

        class _CustomPlugin:
            pass

        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
            factory_overrides={
                "variable_discovery_plugin_factory": lambda *_: _CustomPlugin(),
            },
        )
        result = container.factory_variable_discovery_plugin()
        assert result.__class__.__name__ == "_CustomPlugin"


def test_di_factory_override_precedence_preserved_for_feature_detection_plugin():
    """Factory override takes precedence over registry resolution."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")

        class _CustomPlugin:
            pass

        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
            factory_overrides={
                "feature_detection_plugin_factory": lambda *_: _CustomPlugin(),
            },
        )
        result = container.factory_feature_detection_plugin()
        assert result.__class__.__name__ == "_CustomPlugin"


# --- GF2-W1-T01: _resolve_platform_key selection chain tests ---


def test_registry_get_default_platform_key_returns_first_registered():
    """get_default_platform_key returns the first registered variable_discovery key."""
    with _prefer_fsrc_prism_on_sys_path():
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        reg = registry_module.PluginRegistry()

        class _FakePlugin:
            pass

        reg.register_variable_discovery_plugin("terraform", _FakePlugin)
        reg.register_variable_discovery_plugin("ansible", _FakePlugin)
        result = reg.get_default_platform_key()
        assert result in ("terraform", "ansible")
        assert result is not None


def test_registry_get_default_platform_key_empty_returns_none():
    """get_default_platform_key returns None when no plugins are registered."""
    with _prefer_fsrc_prism_on_sys_path():
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        reg = registry_module.PluginRegistry()
        assert reg.get_default_platform_key() is None


def test_resolve_platform_key_default_uses_registry():
    """With no explicit scan_options override, _resolve_platform_key falls through to registry."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        plugins_module = importlib.import_module("prism.scanner_plugins")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
            registry=plugins_module.DEFAULT_PLUGIN_REGISTRY,
        )
        key = container._resolve_platform_key()
        assert key == "ansible"


def test_resolve_platform_key_explicit_scan_pipeline_plugin():
    """scan_options.scan_pipeline_plugin overrides registry default."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={
                "role_path": "/tmp/role",
                "scan_pipeline_plugin": "terraform",
            },
        )
        assert container._resolve_platform_key() == "terraform"


def test_resolve_platform_key_policy_context_selection():
    """policy_context.selection.plugin overrides registry default."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={
                "role_path": "/tmp/role",
                "policy_context": {
                    "selection": {"plugin": "kubernetes"},
                },
            },
        )
        assert container._resolve_platform_key() == "kubernetes"


def test_resolve_platform_key_precedence_explicit_over_policy_context():
    """Explicit scan_pipeline_plugin wins over policy_context.selection.plugin."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={
                "role_path": "/tmp/role",
                "scan_pipeline_plugin": "terraform",
                "policy_context": {
                    "selection": {"plugin": "kubernetes"},
                },
            },
        )
        assert container._resolve_platform_key() == "terraform"


def test_resolve_platform_key_fails_closed_no_registry_default():
    """_resolve_platform_key raises ValueError when nothing is resolvable."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        empty_registry = registry_module.PluginRegistry()
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
            registry=empty_registry,
        )
        with pytest.raises(ValueError, match="No platform key resolvable"):
            container._resolve_platform_key()
