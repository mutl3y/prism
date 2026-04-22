"""Targeted unit tests for prism.scanner_core.di (fsrc lane) coverage."""

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


def _load_di_module():
    return importlib.import_module("prism.scanner_core.di")


class _FakeRegistry:
    def __init__(
        self,
        *,
        default_key: str | None = "ansible",
        variable_plugin: Any | None = None,
        feature_plugin: Any | None = None,
    ) -> None:
        self._default = default_key
        self._var = variable_plugin
        self._feat = feature_plugin

    def get_default_platform_key(self) -> str | None:
        return self._default

    def get_variable_discovery_plugin(self, _key: str) -> Any:
        return self._var

    def get_feature_discovery_plugin(self, _key: str) -> Any:  # pragma: no cover
        return None

    def get_feature_detection_plugin(self, _key: str) -> Any:
        return self._feat


class _StubPlugin:
    def __init__(self, *, di: Any) -> None:
        self.di = di


# ---------------------------------------------------------------------------
# resolve_platform_key
# ---------------------------------------------------------------------------


def test_resolve_platform_key_explicit_string():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        assert di.resolve_platform_key({"scan_pipeline_plugin": "ansible"}) == "ansible"


def test_resolve_platform_key_from_policy_context():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        opts = {"policy_context": {"selection": {"plugin": "fakeplat"}}}
        assert di.resolve_platform_key(opts) == "fakeplat"


def test_resolve_platform_key_registry_default():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        assert di.resolve_platform_key({}, registry=_FakeRegistry()) == "ansible"


def test_resolve_platform_key_raises_when_unresolvable():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        with pytest.raises(ValueError):
            di.resolve_platform_key({})
        with pytest.raises(ValueError):
            di.resolve_platform_key({}, registry=_FakeRegistry(default_key=None))


# ---------------------------------------------------------------------------
# DIContainer constructor validation
# ---------------------------------------------------------------------------


def test_container_rejects_empty_role_path():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        with pytest.raises(ValueError):
            di.DIContainer(role_path="", scan_options={})


def test_container_rejects_none_scan_options():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        with pytest.raises(ValueError):
            di.DIContainer(role_path="/r", scan_options=None)  # type: ignore[arg-type]


def test_container_scan_options_property_exposes_dict():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        opts = {"k": "v"}
        c = di.DIContainer(role_path="/r", scan_options=opts)
        assert c.scan_options is opts


# ---------------------------------------------------------------------------
# factory_scanner_context wiring guard
# ---------------------------------------------------------------------------


def test_factory_scanner_context_requires_wiring():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        with pytest.raises(RuntimeError):
            c.factory_scanner_context()


# ---------------------------------------------------------------------------
# factory_variable_discovery / factory_feature_detector
# ---------------------------------------------------------------------------


def test_factory_variable_discovery_uses_mock_when_injected():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        sentinel = object()
        c.inject_mock_variable_discovery(sentinel)
        assert c.factory_variable_discovery() is sentinel


def test_factory_variable_discovery_uses_override():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        sentinel = object()

        def _override(container, role_path, scan_options):
            assert role_path == "/r"
            assert scan_options == {}
            return sentinel

        c = di.DIContainer(
            role_path="/r",
            scan_options={},
            factory_overrides={"variable_discovery_factory": _override},
        )
        assert c.factory_variable_discovery() is sentinel


def test_factory_feature_detector_uses_mock_when_injected():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        sentinel = object()
        c.inject_mock_feature_detector(sentinel)
        assert c.factory_feature_detector() is sentinel


def test_factory_feature_detector_uses_override():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        sentinel = object()
        c = di.DIContainer(
            role_path="/r",
            scan_options={},
            factory_overrides={"feature_detector_factory": lambda *a, **k: sentinel},
        )
        assert c.factory_feature_detector() is sentinel


def test_factory_variable_row_builder_caches():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        first = c.factory_variable_row_builder()
        assert c.factory_variable_row_builder() is first


def test_factory_blocker_fact_builder_caches_callable():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        first = c.factory_blocker_fact_builder()
        assert callable(first)
        assert c.factory_blocker_fact_builder() is first


# ---------------------------------------------------------------------------
# Plugin resolution: registry / mock / override / fail-closed
# ---------------------------------------------------------------------------


def test_factory_variable_discovery_plugin_fail_closed_no_registry():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(
            role_path="/r",
            scan_options={"scan_pipeline_plugin": "ansible"},
        )
        with pytest.raises(ValueError, match="No plugin registry"):
            c.factory_variable_discovery_plugin()


def test_factory_variable_discovery_plugin_fail_closed_unregistered():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(
            role_path="/r",
            scan_options={"scan_pipeline_plugin": "ansible"},
            registry=_FakeRegistry(variable_plugin=None),
        )
        with pytest.raises(ValueError, match="No variable_discovery plugin"):
            c.factory_variable_discovery_plugin()


def test_factory_variable_discovery_plugin_resolves_via_registry():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(
            role_path="/r",
            scan_options={"scan_pipeline_plugin": "ansible"},
            registry=_FakeRegistry(variable_plugin=_StubPlugin),
        )
        plugin = c.factory_variable_discovery_plugin()
        assert isinstance(plugin, _StubPlugin)
        assert plugin.di is c


def test_factory_variable_discovery_plugin_uses_mock():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        sentinel = object()
        c.inject_mock_variable_discovery_plugin(sentinel)
        assert c.factory_variable_discovery_plugin() is sentinel


def test_factory_variable_discovery_plugin_uses_override():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        sentinel = object()
        c = di.DIContainer(
            role_path="/r",
            scan_options={},
            factory_overrides={
                "variable_discovery_plugin_factory": lambda *a, **k: sentinel
            },
        )
        assert c.factory_variable_discovery_plugin() is sentinel


def test_factory_feature_detection_plugin_fail_closed_unregistered():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(
            role_path="/r",
            scan_options={"scan_pipeline_plugin": "ansible"},
            registry=_FakeRegistry(feature_plugin=None),
        )
        with pytest.raises(ValueError, match="No feature_detection plugin"):
            c.factory_feature_detection_plugin()


def test_factory_feature_detection_plugin_resolves_via_registry():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(
            role_path="/r",
            scan_options={"scan_pipeline_plugin": "ansible"},
            registry=_FakeRegistry(feature_plugin=_StubPlugin),
        )
        plugin = c.factory_feature_detection_plugin()
        assert isinstance(plugin, _StubPlugin)
        assert plugin.di is c


def test_factory_feature_detection_plugin_uses_mock_and_override():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        sentinel = object()
        c.inject_mock_feature_detection_plugin(sentinel)
        assert c.factory_feature_detection_plugin() is sentinel
        c.clear_mocks()
        # After clearing mocks, override path activates
        sentinel2 = object()
        c2 = di.DIContainer(
            role_path="/r",
            scan_options={},
            factory_overrides={
                "feature_detection_plugin_factory": lambda *a, **k: sentinel2
            },
        )
        assert c2.factory_feature_detection_plugin() is sentinel2


# ---------------------------------------------------------------------------
# Optional policy plugin factories: default-None, mock, override branches.
# ---------------------------------------------------------------------------


_POLICY_FACTORIES = [
    ("comment_driven_doc_plugin", "factory_comment_driven_doc_plugin"),
    ("task_annotation_policy_plugin", "factory_task_annotation_policy_plugin"),
    (
        "task_line_parsing_policy_plugin",
        "factory_task_line_parsing_policy_plugin",
    ),
    ("task_traversal_policy_plugin", "factory_task_traversal_policy_plugin"),
    (
        "variable_extractor_policy_plugin",
        "factory_variable_extractor_policy_plugin",
    ),
    ("yaml_parsing_policy_plugin", "factory_yaml_parsing_policy_plugin"),
    ("jinja_analysis_policy_plugin", "factory_jinja_analysis_policy_plugin"),
]


@pytest.mark.parametrize("mock_name,factory_name", _POLICY_FACTORIES)
def test_optional_policy_plugin_default_none(mock_name, factory_name):
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        assert getattr(c, factory_name)() is None


@pytest.mark.parametrize("mock_name,factory_name", _POLICY_FACTORIES)
def test_optional_policy_plugin_mock_branch(mock_name, factory_name):
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        sentinel = object()
        c.inject_mock(mock_name, sentinel)
        assert getattr(c, factory_name)() is sentinel


@pytest.mark.parametrize("mock_name,factory_name", _POLICY_FACTORIES)
def test_optional_policy_plugin_override_branch(mock_name, factory_name):
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        sentinel = object()
        c = di.DIContainer(
            role_path="/r",
            scan_options={},
            factory_overrides={f"{mock_name}_factory": lambda *a, **k: sentinel},
        )
        assert getattr(c, factory_name)() is sentinel


# ---------------------------------------------------------------------------
# Cache + mock management
# ---------------------------------------------------------------------------


def test_clear_mocks_and_clear_cache():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        c.inject_mock("variable_discovery", object())
        first = c.factory_variable_row_builder()
        c.clear_mocks()
        c.clear_cache()
        assert c.factory_variable_row_builder() is not first


def test_pre_resolved_platform_key_is_used():
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(
            role_path="/r",
            scan_options={},
            registry=_FakeRegistry(variable_plugin=_StubPlugin, default_key="other"),
            platform_key="ansible",
        )
        plugin = c.factory_variable_discovery_plugin()
        assert isinstance(plugin, _StubPlugin)


# ---------------------------------------------------------------------------
# inject_mock_* convenience helpers thread through to inject_mock.
# ---------------------------------------------------------------------------


_INJECTOR_HELPERS = [
    ("inject_mock_comment_driven_doc_plugin", "comment_driven_doc_plugin"),
    (
        "inject_mock_task_annotation_policy_plugin",
        "task_annotation_policy_plugin",
    ),
    (
        "inject_mock_task_line_parsing_policy_plugin",
        "task_line_parsing_policy_plugin",
    ),
    (
        "inject_mock_task_traversal_policy_plugin",
        "task_traversal_policy_plugin",
    ),
    (
        "inject_mock_variable_extractor_policy_plugin",
        "variable_extractor_policy_plugin",
    ),
    (
        "inject_mock_yaml_parsing_policy_plugin",
        "yaml_parsing_policy_plugin",
    ),
    (
        "inject_mock_jinja_analysis_policy_plugin",
        "jinja_analysis_policy_plugin",
    ),
]


@pytest.mark.parametrize("helper_name,mock_key", _INJECTOR_HELPERS)
def test_inject_mock_helpers_thread_to_mocks(helper_name, mock_key):
    with _prefer_fsrc_prism_on_sys_path():
        di = _load_di_module()
        c = di.DIContainer(role_path="/r", scan_options={})
        sentinel = object()
        getattr(c, helper_name)(sentinel)
        # Resolve via the corresponding factory
        factory_name = {
            "comment_driven_doc_plugin": "factory_comment_driven_doc_plugin",
            "task_annotation_policy_plugin": "factory_task_annotation_policy_plugin",
            "task_line_parsing_policy_plugin": "factory_task_line_parsing_policy_plugin",
            "task_traversal_policy_plugin": "factory_task_traversal_policy_plugin",
            "variable_extractor_policy_plugin": "factory_variable_extractor_policy_plugin",
            "yaml_parsing_policy_plugin": "factory_yaml_parsing_policy_plugin",
            "jinja_analysis_policy_plugin": "factory_jinja_analysis_policy_plugin",
        }[mock_key]
        assert getattr(c, factory_name)() is sentinel
