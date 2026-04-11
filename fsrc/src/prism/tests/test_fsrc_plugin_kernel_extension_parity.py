"""Parity checks for fsrc scanner plugin/kernel/extension ownership seams."""

from __future__ import annotations

import importlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "fsrc" / "src"


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


def test_fsrc_scanner_plugin_kernel_extension_paths_import_cleanly() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_plugins = importlib.import_module("prism.scanner_plugins")
        scanner_kernel = importlib.import_module("prism.scanner_kernel")
        scanner_extensions = importlib.import_module("prism.scanner_extensions")

    assert scanner_plugins.__name__ == "prism.scanner_plugins"
    assert scanner_kernel.__name__ == "prism.scanner_kernel"
    assert scanner_extensions.__name__ == "prism.scanner_extensions"


def test_fsrc_plugin_registry_registers_and_resolves_plugins() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

    class _Plugin:
        pass

    registry = registry_module.PluginRegistry()
    registry.register_feature_detection_plugin("demo", _Plugin)

    assert registry.get_feature_detection_plugin("demo") is _Plugin
    assert registry.list_feature_detection_plugins() == ["demo"]


def test_fsrc_kernel_route_orchestration_respects_ansible_feature_flag(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )

    def _legacy_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "legacy", "role_path": role_path, "scan_options": scan_options}

    def _kernel_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "kernel", "role_path": role_path, "scan_options": scan_options}

    monkeypatch.setattr(
        orchestrator_module,
        "is_ansible_plugin_enabled",
        lambda: False,
    )
    legacy_result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"x": 1},
        legacy_orchestrator_fn=_legacy_orchestrator,
        kernel_orchestrator_fn=_kernel_orchestrator,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "is_ansible_plugin_enabled",
        lambda: True,
    )
    kernel_result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"x": 1},
        legacy_orchestrator_fn=_legacy_orchestrator,
        kernel_orchestrator_fn=_kernel_orchestrator,
    )

    assert legacy_result["lane"] == "legacy"
    assert kernel_result["lane"] == "kernel"


def test_fsrc_extension_registry_registers_and_validates_versions() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        registry_module = importlib.import_module("prism.scanner_extensions.registry")

    class _Extension(registry_module.ExtensionInterface):
        def get_name(self) -> str:
            return "demo"

        def get_version(self) -> str:
            return "1.2.3"

        def execute(self, data: dict) -> dict:
            return dict(data)

    registry = registry_module.ExtensionRegistry()
    registry.register(_Extension())

    assert registry.list_extensions() == ["demo"]
    assert registry.get_extension("demo", required_version="^1.0").get_name() == "demo"


def test_fsrc_extension_registry_rejects_caret_lower_bound_mismatch() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        registry_module = importlib.import_module("prism.scanner_extensions.registry")

    class _Extension(registry_module.ExtensionInterface):
        def get_name(self) -> str:
            return "demo"

        def get_version(self) -> str:
            return "1.2.3"

        def execute(self, data: dict) -> dict:
            return dict(data)

    registry = registry_module.ExtensionRegistry()
    registry.register(_Extension())

    try:
        registry.get_extension("demo", required_version="^1.2.4")
    except ValueError as exc:
        assert "does not satisfy" in str(exc)
    else:
        raise AssertionError("Expected caret lower-bound mismatch to raise ValueError")


def test_fsrc_repo_and_collection_context_builders_gate_on_kernel_flag(
    tmp_path: Path,
) -> None:
    role_a = tmp_path / "role_a"
    role_b = tmp_path / "role_b"
    for role in (role_a, role_b):
        (role / "defaults").mkdir(parents=True)
        (role / "vars").mkdir(parents=True)

    (role_a / "defaults" / "main.yml").write_text(
        "---\nshared_key: one\n", encoding="utf-8"
    )
    (role_b / "vars" / "main.yml").write_text(
        "---\nshared_key: two\n", encoding="utf-8"
    )

    with _prefer_fsrc_prism_on_sys_path():
        repo_context_module = importlib.import_module(
            "prism.scanner_kernel.repo_context"
        )
        collection_context_module = importlib.import_module(
            "prism.scanner_kernel.collection_context"
        )

        os.environ["PRISM_KERNEL_ENABLED"] = "0"
        assert (
            repo_context_module.build_repo_context_graph([str(role_a), str(role_b)])
            is None
        )
        assert (
            collection_context_module.build_collection_scan_context(
                collection_path=str(tmp_path),
                role_paths=[str(role_a), str(role_b)],
            )
            is None
        )

        os.environ["PRISM_KERNEL_ENABLED"] = "1"
        repo_context = repo_context_module.build_repo_context_graph(
            [str(role_a), str(role_b)],
            repo_url="https://example.invalid/demo.git",
        )
        assert repo_context is not None
        assert "shared_key" in repo_context["shared_variable_names"]

        collection_context = collection_context_module.build_collection_scan_context(
            collection_path=str(tmp_path),
            role_paths=[str(role_a), str(role_b)],
            collection_name="demo.collection",
        )
        assert collection_context is not None
        assert "shared_key" in collection_context["cross_role_shared_names"]
