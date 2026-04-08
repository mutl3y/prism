"""Wave 1 tests for FSRC additive scaffold and default-off extension seam."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from prism.scanner_core.extension_registry import ExtensionRegistry, HookPoint


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_module(module_name: str, module_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fsrc_scaffold_files_exist() -> None:
    root = _repo_root()
    assert (root / "fsrc/src/prism_next/__init__.py").exists()
    assert (root / "fsrc/src/prism_next/extension_seam.py").exists()
    assert (root / "fsrc/src/prism_next/contracts/runtime.py").exists()


def test_fsrc_scaffold_is_not_importable_by_default_runtime_path() -> None:
    # Wave 1 is scaffold-only and must not alter default runtime import behavior.
    assert importlib.util.find_spec("prism_next") is None


def test_extension_seam_default_off_returns_empty(monkeypatch) -> None:
    module = _load_module(
        "fsrc_extension_seam",
        _repo_root() / "fsrc/src/prism_next/extension_seam.py",
    )
    monkeypatch.delenv(module.FSRC_EXTENSION_SEAM_ENABLED_ENV_VAR, raising=False)

    registry = ExtensionRegistry()
    called = {"count": 0}

    def marker_processor(*_args, **_kwargs):
        called["count"] += 1
        return "called"

    registry.register(HookPoint.VARIABLE_DISCOVERY_PRE, marker_processor)

    result = module.maybe_call_extension_processors(
        registry,
        HookPoint.VARIABLE_DISCOVERY_PRE,
        "payload",
    )

    assert result == []
    assert called["count"] == 0


def test_extension_seam_enabled_calls_processors(monkeypatch) -> None:
    module = _load_module(
        "fsrc_extension_seam_enabled",
        _repo_root() / "fsrc/src/prism_next/extension_seam.py",
    )
    monkeypatch.setenv(module.FSRC_EXTENSION_SEAM_ENABLED_ENV_VAR, "1")

    registry = ExtensionRegistry()

    def marker_processor(value: str) -> str:
        return f"ok:{value}"

    registry.register(HookPoint.FEATURE_DETECTION_PRE, marker_processor)

    result = module.maybe_call_extension_processors(
        registry,
        HookPoint.FEATURE_DETECTION_PRE,
        "wave1",
    )

    assert result == ["ok:wave1"]


def test_runtime_contract_annotations_are_present() -> None:
    module = _load_module(
        "fsrc_runtime_contracts",
        _repo_root() / "fsrc/src/prism_next/contracts/runtime.py",
    )

    assert set(module.ExtensionHookCall.__annotations__) == {
        "hook_point",
        "args_count",
        "kwargs_keys",
    }
    assert set(module.ExtensionHookResult.__annotations__) == {
        "enabled",
        "result_count",
        "errors",
        "payload",
    }
