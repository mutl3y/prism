"""T2-03: Entry-points-based plugin discovery tests."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from importlib.metadata import EntryPoint
import threading
from typing import cast

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
    def __init__(self, name: str, target: object) -> None:
        self.name = name
        self._target = target

    def load(self) -> object:
        if isinstance(self._target, Exception):
            raise self._target
        return self._target


def _iter_entry_points(
    entry_points: list[_FakeEntryPoint],
) -> Callable[[str], Iterable[EntryPoint]]:
    def _iter(_group: str) -> Iterable[EntryPoint]:
        return cast(Iterable[EntryPoint], entry_points)

    return _iter


def test_constant_group_name() -> None:
    assert PRISM_PLUGIN_ENTRY_POINT_GROUP == "prism.scanner_plugins"


def test_discover_registers_plugin_via_entry_point() -> None:
    reg = PluginRegistry()

    class _Plugin:
        PLUGIN_IS_STATELESS = True

        def process_scan_pipeline(self, scan_options, scan_context):
            return {}

    def _register(registry):
        registry.register_scan_pipeline_plugin("ext", _Plugin)

    eps = [_FakeEntryPoint("my_ext", _register)]
    registered = discover_entry_point_plugins(
        registry=reg, iter_entry_points_fn=_iter_entry_points(eps)
    )
    assert registered == ["my_ext"]
    assert "ext" in reg.list_scan_pipeline_plugins()


def test_discover_skips_load_failures_by_default(caplog) -> None:
    reg = PluginRegistry()
    eps = [_FakeEntryPoint("bad", ImportError("missing module"))]

    with caplog.at_level("WARNING"):
        registered = discover_entry_point_plugins(
            registry=reg, iter_entry_points_fn=_iter_entry_points(eps)
        )

    assert registered == []
    assert any("bad" in record.message for record in caplog.records)


def test_discover_raises_on_load_failure_when_strict() -> None:
    reg = PluginRegistry()
    eps = [_FakeEntryPoint("bad", ImportError("missing module"))]

    with pytest.raises(EntryPointPluginLoadError, match="bad"):
        discover_entry_point_plugins(
            registry=reg,
            iter_entry_points_fn=_iter_entry_points(eps),
            raise_on_error=True,
        )


def test_discover_skips_non_callable_entry_point() -> None:
    reg = PluginRegistry()
    eps = [_FakeEntryPoint("not_callable", "definitely_not_callable")]

    registered = discover_entry_point_plugins(
        registry=reg, iter_entry_points_fn=_iter_entry_points(eps)
    )
    assert registered == []


def test_discover_raises_on_non_callable_when_strict() -> None:
    reg = PluginRegistry()
    eps = [_FakeEntryPoint("not_callable", 42)]

    with pytest.raises(EntryPointPluginLoadError, match="must resolve to a callable"):
        discover_entry_point_plugins(
            registry=reg,
            iter_entry_points_fn=_iter_entry_points(eps),
            raise_on_error=True,
        )


def test_discover_skips_registration_failure_by_default(caplog) -> None:
    reg = PluginRegistry()

    def _broken(registry):
        raise RuntimeError("kaboom")

    eps = [_FakeEntryPoint("explosive", _broken)]
    with caplog.at_level("WARNING"):
        registered = discover_entry_point_plugins(
            registry=reg, iter_entry_points_fn=_iter_entry_points(eps)
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
            registry=reg, iter_entry_points_fn=_iter_entry_points(eps)
        )


def test_discover_with_default_real_entry_points_does_not_crash() -> None:
    """Smoke: calling discover with the real entry-points loader is safe."""
    reg = PluginRegistry()
    # No assertion on result — environment may have zero or more entry points.
    discover_entry_point_plugins(registry=reg)


def test_bootstrap_fails_closed_on_entry_point_discovery_defect(monkeypatch) -> None:
    from prism.scanner_plugins import bootstrap as bootstrap_module
    from prism.scanner_plugins import discovery as discovery_module
    from prism.scanner_plugins import registry as registry_module

    original_state = registry_module.plugin_registry.snapshot_state()
    original_default_registry = bootstrap_module._DEFAULT_REGISTRY
    bootstrap_module._DEFAULT_REGISTRY = None
    registry_module.plugin_registry.replace_state(
        registry_module.PluginRegistry().snapshot_state()
    )

    def _raise_on_discovery(**_kwargs):
        raise EntryPointPluginLoadError("discovery boom")

    monkeypatch.setattr(
        discovery_module,
        "discover_entry_point_plugins",
        _raise_on_discovery,
    )

    try:
        with pytest.raises(EntryPointPluginLoadError, match="discovery boom"):
            bootstrap_module.initialize_default_registry()

        assert bootstrap_module.is_registry_initialized() is False
        assert registry_module.plugin_registry.list_scan_pipeline_plugins() == []
        assert registry_module.plugin_registry.list_extract_policy_plugins() == []
        assert registry_module.plugin_registry.get_default_platform_key() is None
    finally:
        registry_module.plugin_registry.replace_state(original_state)
        bootstrap_module._DEFAULT_REGISTRY = original_default_registry


def test_bootstrap_concurrent_first_initialization_is_atomic(monkeypatch) -> None:
    from prism.scanner_plugins import bootstrap as bootstrap_module
    from prism.scanner_plugins import discovery as discovery_module
    from prism.scanner_plugins import registry as registry_module

    original_state = registry_module.plugin_registry.snapshot_state()
    original_default_registry = bootstrap_module._DEFAULT_REGISTRY
    bootstrap_module._DEFAULT_REGISTRY = None
    registry_module.plugin_registry.replace_state(
        registry_module.PluginRegistry().snapshot_state()
    )

    entered_discovery = threading.Event()
    release_discovery = threading.Event()
    discover_call_count = 0
    discover_call_count_lock = threading.Lock()

    def _blocking_discovery(*, registry, raise_on_error, **_kwargs):
        nonlocal discover_call_count
        assert raise_on_error is True
        with discover_call_count_lock:
            discover_call_count += 1
        assert registry is not registry_module.plugin_registry
        assert "ansible" in registry.list_scan_pipeline_plugins()
        entered_discovery.set()
        assert release_discovery.wait(timeout=5)
        return []

    monkeypatch.setattr(
        discovery_module,
        "discover_entry_point_plugins",
        _blocking_discovery,
    )

    results: list[object] = []
    errors: list[BaseException] = []

    def _worker() -> None:
        try:
            results.append(bootstrap_module.initialize_default_registry())
        except BaseException as exc:  # pragma: no cover - exercised only on failure
            errors.append(exc)

    try:
        threads = [threading.Thread(target=_worker) for _ in range(2)]
        for thread in threads:
            thread.start()

        assert entered_discovery.wait(timeout=5)
        assert bootstrap_module.is_registry_initialized() is False
        assert registry_module.plugin_registry.list_scan_pipeline_plugins() == []

        release_discovery.set()

        for thread in threads:
            thread.join(timeout=5)
            assert not thread.is_alive()

        assert errors == []
        assert discover_call_count == 1
        assert len(results) == 2
        assert all(result is registry_module.plugin_registry for result in results)
        assert bootstrap_module.is_registry_initialized() is True
        assert "ansible" in registry_module.plugin_registry.list_scan_pipeline_plugins()
        assert "default" in registry_module.plugin_registry.list_scan_pipeline_plugins()
    finally:
        registry_module.plugin_registry.replace_state(original_state)
        bootstrap_module._DEFAULT_REGISTRY = original_default_registry
