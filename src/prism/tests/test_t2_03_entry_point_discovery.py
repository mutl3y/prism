"""T2-03: Entry-points-based plugin discovery tests."""

from __future__ import annotations


import pytest

from prism.scanner_plugins import (
    EntryPointPluginLoadError,
    PRISM_PLUGIN_ENTRY_POINT_GROUP,
    discover_entry_point_plugins,
)
from prism.scanner_plugins.registry import (
    PluginAPIVersionMismatch,
    PluginRegistry,
)


class _FakeEntryPoint:
    def __init__(self, name: str, target):
        self.name = name
        self._target = target

    def load(self):
        if isinstance(self._target, Exception):
            raise self._target
        return self._target


def test_constant_group_name() -> None:
    assert PRISM_PLUGIN_ENTRY_POINT_GROUP == "prism.scanner_plugins"


def test_discover_registers_plugin_via_entry_point() -> None:
    reg = PluginRegistry()

    class _Plugin:
        def process_scan_pipeline(self, scan_options, scan_context):
            return {}

    def _register(registry):
        registry.register_scan_pipeline_plugin("ext", _Plugin)

    eps = [_FakeEntryPoint("my_ext", _register)]
    registered = discover_entry_point_plugins(
        registry=reg, iter_entry_points_fn=lambda group: eps
    )
    assert registered == ["my_ext"]
    assert "ext" in reg.list_scan_pipeline_plugins()


def test_discover_skips_load_failures_by_default(caplog) -> None:
    reg = PluginRegistry()
    eps = [_FakeEntryPoint("bad", ImportError("missing module"))]

    with caplog.at_level("WARNING"):
        registered = discover_entry_point_plugins(
            registry=reg, iter_entry_points_fn=lambda group: eps
        )

    assert registered == []
    assert any("bad" in record.message for record in caplog.records)


def test_discover_raises_on_load_failure_when_strict() -> None:
    reg = PluginRegistry()
    eps = [_FakeEntryPoint("bad", ImportError("missing module"))]

    with pytest.raises(EntryPointPluginLoadError, match="bad"):
        discover_entry_point_plugins(
            registry=reg,
            iter_entry_points_fn=lambda group: eps,
            raise_on_error=True,
        )


def test_discover_skips_non_callable_entry_point() -> None:
    reg = PluginRegistry()
    eps = [_FakeEntryPoint("not_callable", "definitely_not_callable")]

    registered = discover_entry_point_plugins(
        registry=reg, iter_entry_points_fn=lambda group: eps
    )
    assert registered == []


def test_discover_raises_on_non_callable_when_strict() -> None:
    reg = PluginRegistry()
    eps = [_FakeEntryPoint("not_callable", 42)]

    with pytest.raises(EntryPointPluginLoadError, match="must resolve to a callable"):
        discover_entry_point_plugins(
            registry=reg,
            iter_entry_points_fn=lambda group: eps,
            raise_on_error=True,
        )


def test_discover_skips_registration_failure_by_default(caplog) -> None:
    reg = PluginRegistry()

    def _broken(registry):
        raise RuntimeError("kaboom")

    eps = [_FakeEntryPoint("explosive", _broken)]
    with caplog.at_level("WARNING"):
        registered = discover_entry_point_plugins(
            registry=reg, iter_entry_points_fn=lambda group: eps
        )
    assert registered == []
    assert any("explosive" in r.message for r in caplog.records)


def test_discover_propagates_plugin_api_version_mismatch() -> None:
    reg = PluginRegistry()

    class _BadPlugin:
        PRISM_PLUGIN_API_VERSION = (99, 0)

        def process_scan_pipeline(self, scan_options, scan_context):
            return {}

    def _register(registry):
        registry.register_scan_pipeline_plugin("bad", _BadPlugin)

    eps = [_FakeEntryPoint("ver_mismatch", _register)]
    with pytest.raises(PluginAPIVersionMismatch):
        discover_entry_point_plugins(
            registry=reg, iter_entry_points_fn=lambda group: eps
        )


def test_discover_with_default_real_entry_points_does_not_crash() -> None:
    """Smoke: calling discover with the real entry-points loader is safe."""
    reg = PluginRegistry()
    # No assertion on result — environment may have zero or more entry points.
    discover_entry_point_plugins(registry=reg)
