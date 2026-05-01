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


@pytest.mark.parametrize(
    ("register_method", "slot_name"),
    [
        ("register_variable_discovery_plugin", "variable_discovery"),
        ("register_feature_detection_plugin", "feature_detection"),
    ],
)
def test_registry_rejects_runtime_plugins_without_di_constructor(
    register_method: str,
    slot_name: str,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        registry = registry_module.PluginRegistry()

        class _BadPlugin:
            pass

        with pytest.raises(registry_module.PluginConstructorMismatch) as exc_info:
            getattr(registry, register_method)(f"bad-{slot_name}", _BadPlugin)

    assert "accept di=..." in str(exc_info.value)


def test_di_mock_precedence_preserved_for_variable_discovery_plugin():
    """Mock injection takes precedence over registry resolution."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
        )
        container.inject_mock("variable_discovery_plugin", "mock-var-plugin")
        assert container.factory_variable_discovery_plugin() == "mock-var-plugin"


def test_di_mock_precedence_preserved_for_feature_detection_plugin():
    """Mock injection takes precedence over registry resolution."""
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options={"role_path": "/tmp/role"},
        )
        container.inject_mock("feature_detection_plugin", "mock-feature-plugin")
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
            def __init__(self, di: object | None = None) -> None:
                self.di = di

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


def test_execution_request_builder_uses_default_registry_over_scan_options_bypass():
    """Execution requests must source registry identity from the DI wiring seam."""
    with _prefer_fsrc_prism_on_sys_path():
        builder_module = importlib.import_module(
            "prism.scanner_core.execution_request_builder"
        )

        class _Registry:
            def __init__(self, default_platform_key: str) -> None:
                self._default_platform_key = default_platform_key

            def get_default_platform_key(self) -> str:
                return self._default_platform_key

        class _ScannerContext:
            def orchestrate_scan(self) -> dict[str, str]:
                return {"status": "ok"}

        class _Container:
            def __init__(
                self,
                role_path: str,
                scan_options: dict[str, object],
                *,
                registry: object,
                platform_key: str,
                scanner_context_wiring: dict[str, object],
                factory_overrides: dict[str, object],
            ) -> None:
                self.role_path = role_path
                self.scan_options = scan_options
                self.plugin_registry = registry
                self.platform_key = platform_key
                self.scanner_context_wiring = scanner_context_wiring
                self.factory_overrides = factory_overrides

            def factory_scanner_context(self) -> _ScannerContext:
                return _ScannerContext()

        authoritative_registry = _Registry("ansible")
        bypass_registry = _Registry("terraform")
        prepared_policy_di: list[object] = []

        request = builder_module._assemble_execution_request(
            canonical_options={
                "role_path": "/tmp/role",
                "plugin_registry": bypass_registry,
            },
            variable_discovery_cls=lambda *_args, **_kwargs: object(),
            feature_detector_cls=lambda *_args, **_kwargs: object(),
            extract_role_description_fn=lambda _path, _name: "",
            resolve_comment_driven_documentation_plugin_fn=lambda _container: object(),
            di_container_cls=_Container,
            scanner_context_cls=_ScannerContext,
            build_run_scan_options_canonical_fn=lambda **_kwargs: {
                "role_path": "/tmp/role"
            },
            default_plugin_registry=authoritative_registry,
            ensure_prepared_policy_bundle_fn=lambda *, scan_options, di: (
                prepared_policy_di.append(di)
            ),
        )

        assert request.runtime_registry is authoritative_registry
        assert prepared_policy_di[0].plugin_registry is authoritative_registry
        assert prepared_policy_di[0].platform_key == "ansible"


def test_loader_registry_resolution_ignores_scan_options_bypass():
    """Loader must not treat scan_options payloads as an alternate registry authority."""
    with _prefer_fsrc_prism_on_sys_path():
        loader_module = importlib.import_module("prism.scanner_io.loader")
        authoritative_registry = object()
        bypass_registry = object()

        class _Container:
            def __init__(self, plugin_registry: object | None) -> None:
                self.plugin_registry = plugin_registry
                self.scan_options = {"plugin_registry": bypass_registry}

        assert (
            loader_module._resolve_plugin_registry(_Container(authoritative_registry))
            is authoritative_registry
        )
        assert loader_module._resolve_plugin_registry(_Container(None)) is None


def test_loader_live_yaml_policy_resolution_uses_di_registry_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """load_yaml_file must thread only DI.plugin_registry into live resolver calls."""
    with _prefer_fsrc_prism_on_sys_path():
        loader_module = importlib.import_module("prism.scanner_io.loader")
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")

        authoritative_registry = object()
        bypass_registry = object()
        captured: dict[str, object] = {}

        class _Policy:
            @staticmethod
            def load_yaml_file(path: Path) -> object:
                return {"loaded_from": path.name}

        def _resolve_yaml_parsing_policy_plugin(
            di: object | None = None,
            *,
            registry: object | None = None,
        ) -> object:
            captured["di"] = di
            captured["registry"] = registry
            return _Policy()

        class _Container:
            def __init__(self) -> None:
                self.plugin_registry = authoritative_registry
                self.scan_options = {"plugin_registry": bypass_registry}

        monkeypatch.setattr(
            defaults_module,
            "resolve_yaml_parsing_policy_plugin",
            _resolve_yaml_parsing_policy_plugin,
        )

        yaml_path = tmp_path / "sample.yml"
        yaml_path.write_text("key: value\n", encoding="utf-8")

        assert loader_module.load_yaml_file(yaml_path, di=_Container()) == {
            "loaded_from": "sample.yml"
        }
        assert captured["registry"] is authoritative_registry
        assert captured["registry"] is not bypass_registry
