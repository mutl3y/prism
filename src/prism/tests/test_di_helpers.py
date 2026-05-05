"""Tests for the shared scan_options_from_di helper in the fsrc lane."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path

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


class _FakeDI:
    def __init__(self, *, scan_options=None):
        if scan_options is not None:
            self.scan_options = scan_options


def _load_helper():
    mod = importlib.import_module("prism.scanner_core.di_helpers")
    return mod.scan_options_from_di


def test_none_di_returns_none():
    with _prefer_fsrc_prism_on_sys_path():
        fn = _load_helper()
        assert fn(None) is None


def test_no_arg_returns_none():
    with _prefer_fsrc_prism_on_sys_path():
        fn = _load_helper()
        assert fn() is None


def test_scan_options_dict():
    with _prefer_fsrc_prism_on_sys_path():
        fn = _load_helper()
        opts = {"key": "value"}
        di = _FakeDI(scan_options=opts)
        assert fn(di) is opts


def test_non_dict_scan_options_returns_none():
    with _prefer_fsrc_prism_on_sys_path():
        fn = _load_helper()
        di = _FakeDI(scan_options="not_a_dict")
        assert fn(di) is None


def test_no_scan_options_attr_returns_none():
    with _prefer_fsrc_prism_on_sys_path():
        fn = _load_helper()
        di = object()
        assert fn(di) is None


def _load_event_bus_helper():
    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_core.di_helpers")
        return module.get_event_bus_or_none


def test_get_event_bus_or_none_returns_none_when_factory_absent() -> None:
    helper = _load_event_bus_helper()
    assert helper(object()) is None


def test_get_event_bus_or_none_returns_none_when_factory_returns_none() -> None:
    helper = _load_event_bus_helper()

    class _DI:
        def factory_event_bus(self):
            return None

    assert helper(_DI()) is None


def test_get_event_bus_or_none_returns_bus_when_factory_present() -> None:
    helper = _load_event_bus_helper()

    class _FakeBus:
        pass

    fake_bus = _FakeBus()

    class _DI:
        def factory_event_bus(self):
            return fake_bus

    assert helper(_DI()) is fake_bus
