"""Coverage tests for fsrc scanner_core small surfaces."""

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


# ---------------------------------------------------------------------------
# scanner_core.__init__ public surface guards
# ---------------------------------------------------------------------------


def test_init_getattr_private_raises():
    with _prefer_fsrc_prism_on_sys_path():
        mod = importlib.import_module("prism.scanner_core")
        with pytest.raises(AttributeError, match="private member"):
            _ = mod._not_a_thing  # type: ignore[attr-defined]


def test_init_getattr_unknown_raises():
    with _prefer_fsrc_prism_on_sys_path():
        mod = importlib.import_module("prism.scanner_core")
        with pytest.raises(AttributeError):
            _ = mod.does_not_exist  # type: ignore[attr-defined]


def test_init_dir_lists_all_public():
    with _prefer_fsrc_prism_on_sys_path():
        mod = importlib.import_module("prism.scanner_core")
        listing = dir(mod)
        for name in mod.__all__:
            assert name in listing


# ---------------------------------------------------------------------------
# VariableDiscovery: fail-closed when no plugin available
# ---------------------------------------------------------------------------


class _NoPluginDI:
    """DI stub without factory_variable_discovery_plugin / feature."""

    scan_options = {}


def _make_variable_discovery(role_path: str = "/r"):
    mod = importlib.import_module("prism.scanner_core.variable_discovery")
    return mod.VariableDiscovery(_NoPluginDI(), role_path, {})


def test_variable_discovery_static_fails_without_plugin():
    with _prefer_fsrc_prism_on_sys_path():
        vd = _make_variable_discovery()
        with pytest.raises(ValueError, match="VariableDiscovery requires a plugin"):
            vd.discover_static()


def test_variable_discovery_referenced_fails_without_plugin():
    with _prefer_fsrc_prism_on_sys_path():
        vd = _make_variable_discovery()
        with pytest.raises(ValueError, match="VariableDiscovery requires a plugin"):
            vd.discover_referenced()


def test_variable_discovery_resolve_fails_without_plugin():
    with _prefer_fsrc_prism_on_sys_path():
        vd = _make_variable_discovery()
        with pytest.raises(ValueError, match="VariableDiscovery requires a plugin"):
            vd.resolve_unresolved(
                static_names=frozenset({"a"}), referenced=frozenset({"b"})
            )


# Plugin-backed paths -------------------------------------------------------


class _StubVarPlugin:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def discover_static_variables(self, role_path: str, options: dict[str, Any]):
        self.calls.append("static")
        return [{"name": "x"}, {"name": "y"}]

    def discover_referenced_variables(self, role_path: str, options: dict[str, Any]):
        self.calls.append("referenced")
        return ["x", "z"]

    def resolve_unresolved_variables(
        self,
        static_names: frozenset[str],
        referenced: frozenset[str],
        options: dict[str, Any],
    ):
        self.calls.append("resolve")
        return {name: "missing" for name in referenced - static_names}


class _PluginDI:
    scan_options = {}

    def __init__(self, plugin: Any) -> None:
        self._plugin = plugin
        self._row_builder = None

    def factory_variable_discovery_plugin(self) -> Any:
        return self._plugin

    def factory_variable_row_builder(self) -> Any:
        if self._row_builder is None:
            from prism.scanner_data.builders import VariableRowBuilder

            self._row_builder = VariableRowBuilder()
        return self._row_builder


def test_variable_discovery_uses_plugin_results():
    with _prefer_fsrc_prism_on_sys_path():
        mod = importlib.import_module("prism.scanner_core.variable_discovery")
        plugin = _StubVarPlugin()
        vd = mod.VariableDiscovery(_PluginDI(plugin), "/r", {})
        static = vd.discover_static()
        referenced = vd.discover_referenced()
        unresolved = vd.resolve_unresolved(
            static_names=frozenset({row["name"] for row in static}),
            referenced=referenced,
        )
        assert tuple(row["name"] for row in static) == ("x", "y")
        assert referenced == frozenset({"x", "z"})
        assert unresolved == {"z": "missing"}


def test_variable_discovery_combined_appends_unresolved_placeholders():
    with _prefer_fsrc_prism_on_sys_path():
        mod = importlib.import_module("prism.scanner_core.variable_discovery")
        plugin = _StubVarPlugin()
        vd = mod.VariableDiscovery(_PluginDI(plugin), "/r", {})
        rows = vd.discover()
        names = [row["name"] for row in rows]
        # "z" was referenced but not static -> placeholder appended
        assert "x" in names and "y" in names and "z" in names


# ---------------------------------------------------------------------------
# FeatureDetector: fail-closed when no plugin available
# ---------------------------------------------------------------------------


class _NoFeaturePluginDI:
    """DI stub lacking factory_feature_detection_plugin entirely."""

    scan_options = {}


def _make_feature_detector():
    mod_fd = importlib.import_module("prism.scanner_core.feature_detector")
    return mod_fd.FeatureDetector(_NoFeaturePluginDI(), "/r", {})


def test_feature_detector_detect_fails_without_plugin():
    with _prefer_fsrc_prism_on_sys_path():
        fd = _make_feature_detector()
        with pytest.raises(ValueError, match="FeatureDetector requires a plugin"):
            fd.detect()


def test_feature_detector_analyze_task_catalog_fails_without_plugin():
    with _prefer_fsrc_prism_on_sys_path():
        fd = _make_feature_detector()
        with pytest.raises(ValueError, match="FeatureDetector requires a plugin"):
            fd.analyze_task_catalog()


# ---------------------------------------------------------------------------
# scan_request.build_run_scan_options_canonical
# ---------------------------------------------------------------------------


def _build_canonical(**overrides: Any):
    mod = importlib.import_module("prism.scanner_core.scan_request")
    defaults: dict[str, Any] = {
        "role_path": "/r",
        "role_name_override": None,
        "readme_config_path": None,
        "include_vars_main": False,
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
    defaults.update(overrides)
    return mod.build_run_scan_options_canonical(**defaults)


def test_build_canonical_rejects_empty_role_path():
    with _prefer_fsrc_prism_on_sys_path():
        with pytest.raises(ValueError, match="role_path"):
            _build_canonical(role_path="   ")


def test_build_canonical_copies_prepared_policy_bundle():
    with _prefer_fsrc_prism_on_sys_path():
        bundle = {"comment_doc_marker_prefix": "PRISM"}
        opts = _build_canonical(prepared_policy_bundle=bundle)
        assert opts["prepared_policy_bundle"] == bundle
        assert opts["prepared_policy_bundle"] is not bundle


def test_build_canonical_normalizes_policy_context():
    with _prefer_fsrc_prism_on_sys_path():
        ctx = {"selection": {"plugin": "ansible"}}
        opts = _build_canonical(policy_context=ctx)
        assert opts["policy_context"] == ctx
        assert opts["policy_context"] is not ctx


def test_build_canonical_ignores_non_dict_policy_context():
    with _prefer_fsrc_prism_on_sys_path():
        opts = _build_canonical(policy_context="not-a-dict")  # type: ignore[arg-type]
        assert opts["policy_context"] is None


# ---------------------------------------------------------------------------
# task_extract_adapters._resolve_marker_prefix fail-closed without bundle
# ---------------------------------------------------------------------------


def test_resolve_marker_prefix_requires_scan_options():
    with _prefer_fsrc_prism_on_sys_path():
        mod = importlib.import_module("prism.scanner_core.task_extract_adapters")
        with pytest.raises(
            ValueError, match="prepared_policy_bundle must be available"
        ):
            mod._resolve_marker_prefix(None)
