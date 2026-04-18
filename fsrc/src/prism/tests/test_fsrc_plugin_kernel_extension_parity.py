"""Parity checks for fsrc scanner plugin/kernel ownership seams."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest


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

    assert scanner_plugins.__name__ == "prism.scanner_plugins"
    assert scanner_kernel.__name__ == "prism.scanner_kernel"


def test_fsrc_markdown_parser_domain_does_not_import_scanner_readme() -> None:
    parser_file = (
        FSRC_SOURCE_ROOT
        / "prism"
        / "scanner_plugins"
        / "parsers"
        / "markdown"
        / "style_parser.py"
    )
    imports = [
        line.strip()
        for line in parser_file.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("from ") or line.strip().startswith("import ")
    ]

    forbidden = [line for line in imports if "prism.scanner_readme" in line]
    assert not forbidden


def test_fsrc_plugin_registry_registers_and_resolves_plugins() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

    class _Plugin:
        pass

    registry = registry_module.PluginRegistry()
    registry.register_feature_detection_plugin("demo", _Plugin)

    assert registry.get_feature_detection_plugin("demo") is _Plugin
    assert registry.list_feature_detection_plugins() == ["demo"]


def test_fsrc_plugin_registry_dynamic_loader_cache_uses_module_and_class_key() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        comment_doc_module = importlib.import_module(
            "prism.scanner_plugins.parsers.comment_doc.role_notes_parser"
        )
        registry = registry_module.PluginRegistry()
        task_line_class = registry.load_plugin_from_module(
            "prism.scanner_plugins.parsers.comment_doc.role_notes_parser",
            "CommentDrivenDocumentationParser",
        )
        task_annotation_class = registry.load_plugin_from_module(
            "prism.scanner_plugins.defaults",
            "resolve_comment_driven_documentation_plugin",
        )

    assert task_line_class is comment_doc_module.CommentDrivenDocumentationParser
    assert (
        task_annotation_class
        is defaults_module.resolve_comment_driven_documentation_plugin
    )
    assert task_line_class is not task_annotation_class


def test_fsrc_default_plugin_registry_bootstrap_registers_required_plugins() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_plugins = importlib.import_module("prism.scanner_plugins")
        ansible_plugins = importlib.import_module("prism.scanner_plugins.ansible")
        policies_module = importlib.import_module("prism.scanner_plugins.policies")
        comment_doc_module = importlib.import_module(
            "prism.scanner_plugins.parsers.comment_doc.role_notes_parser"
        )

    registry = scanner_plugins.DEFAULT_PLUGIN_REGISTRY

    assert "default" in set(registry.list_comment_driven_doc_plugins())
    assert "default" in set(registry.list_scan_pipeline_plugins())
    assert "ansible" in set(registry.list_scan_pipeline_plugins())
    assert (
        registry.get_comment_driven_doc_plugin("default")
        is comment_doc_module.CommentDrivenDocumentationParser
    )
    assert (
        registry.get_scan_pipeline_plugin("default")
        is policies_module.DefaultScanPipelinePlugin
    )
    assert (
        registry.get_scan_pipeline_plugin("ansible")
        is ansible_plugins.AnsibleScanPipelinePlugin
    )


def test_fsrc_default_plugin_registry_aligns_with_canonical_singleton() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_plugins = importlib.import_module("prism.scanner_plugins")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

    assert scanner_plugins.DEFAULT_PLUGIN_REGISTRY is registry_module.plugin_registry


def test_fsrc_no_arg_bootstrap_preserves_singleton_class_bindings() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_plugins = importlib.import_module("prism.scanner_plugins")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        comment_doc_module = importlib.import_module(
            "prism.scanner_plugins.parsers.comment_doc.role_notes_parser"
        )
        ansible_plugins = importlib.import_module("prism.scanner_plugins.ansible")

    first_bootstrap = scanner_plugins.bootstrap_default_plugins()
    second_bootstrap = scanner_plugins.bootstrap_default_plugins()

    assert first_bootstrap is registry_module.plugin_registry
    assert second_bootstrap is registry_module.plugin_registry
    assert (
        registry_module.plugin_registry.get_comment_driven_doc_plugin("default")
        is comment_doc_module.CommentDrivenDocumentationParser
    )
    assert (
        registry_module.plugin_registry.get_scan_pipeline_plugin("ansible")
        is ansible_plugins.AnsibleScanPipelinePlugin
    )


def test_fsrc_default_plugin_bootstrap_is_idempotent_for_required_keys() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_plugins = importlib.import_module("prism.scanner_plugins")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        policies_module = importlib.import_module("prism.scanner_plugins.policies")
        comment_doc_module = importlib.import_module(
            "prism.scanner_plugins.parsers.comment_doc.role_notes_parser"
        )
        ansible_plugins = importlib.import_module("prism.scanner_plugins.ansible")

    registry = registry_module.PluginRegistry()
    first_bootstrap = scanner_plugins.bootstrap_default_plugins(registry)
    before_second_bootstrap = {
        "comment_doc": set(registry.list_comment_driven_doc_plugins()),
        "scan_pipeline": set(registry.list_scan_pipeline_plugins()),
    }

    second_bootstrap = scanner_plugins.bootstrap_default_plugins(registry)
    after_second_bootstrap = {
        "comment_doc": set(registry.list_comment_driven_doc_plugins()),
        "scan_pipeline": set(registry.list_scan_pipeline_plugins()),
    }

    assert first_bootstrap is registry
    assert second_bootstrap is registry
    assert before_second_bootstrap == after_second_bootstrap
    assert {"default"}.issubset(after_second_bootstrap["comment_doc"])
    assert {"default", "ansible"}.issubset(after_second_bootstrap["scan_pipeline"])
    assert (
        registry.get_comment_driven_doc_plugin("default")
        is comment_doc_module.CommentDrivenDocumentationParser
    )
    assert (
        registry.get_scan_pipeline_plugin("default")
        is policies_module.DefaultScanPipelinePlugin
    )
    assert (
        registry.get_scan_pipeline_plugin("ansible")
        is ansible_plugins.AnsibleScanPipelinePlugin
    )


def test_fsrc_required_ansible_scan_pipeline_plugin_process_contract() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_plugins = importlib.import_module("prism.scanner_plugins")

    plugin_class = scanner_plugins.DEFAULT_PLUGIN_REGISTRY.get_scan_pipeline_plugin(
        "ansible"
    )
    assert plugin_class is not None

    plugin_instance = plugin_class()
    result = plugin_instance.process_scan_pipeline(
        scan_options={"role_path": "/tmp/example-role"},
        scan_context={"existing": True},
    )

    assert result["existing"] is True
    assert result["plugin_platform"] == "ansible"
    assert isinstance(result["ansible_plugin_enabled"], bool)
    assert result["role_path"] == "/tmp/example-role"


def test_fsrc_kernel_route_orchestration_uses_registry_plugin_context(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )

    class _DisabledPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options
            del scan_context
            return {"ansible_plugin_enabled": False}

    class _EnabledPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options
            del scan_context
            return {"ansible_plugin_enabled": True}

    def _legacy_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "legacy", "role_path": role_path, "scan_options": scan_options}

    def _kernel_orchestrator(
        *,
        role_path: str,
        scan_options: dict[str, object],
        route_preflight_runtime=None,
    ) -> dict[str, object]:
        return {
            "lane": "kernel",
            "role_path": role_path,
            "scan_options": scan_options,
            "route_preflight_runtime": route_preflight_runtime,
        }

    class _DisabledRegistry:
        def get_scan_pipeline_plugin(self, _name: str):
            return _DisabledPlugin

    monkeypatch.setattr(
        orchestrator_module, "DEFAULT_PLUGIN_REGISTRY", _DisabledRegistry()
    )
    legacy_result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"x": 1},
        legacy_orchestrator_fn=_legacy_orchestrator,
        kernel_orchestrator_fn=_kernel_orchestrator,
    )

    class _EnabledRegistry:
        def get_scan_pipeline_plugin(self, _name: str):
            return _EnabledPlugin

    monkeypatch.setattr(
        orchestrator_module, "DEFAULT_PLUGIN_REGISTRY", _EnabledRegistry()
    )
    kernel_result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"x": 1},
        legacy_orchestrator_fn=_legacy_orchestrator,
        kernel_orchestrator_fn=_kernel_orchestrator,
    )

    assert legacy_result["lane"] == "legacy"
    assert kernel_result["lane"] == "kernel"
    assert "_scan_pipeline_preflight_context" not in kernel_result["scan_options"]
    carrier = kernel_result["route_preflight_runtime"]
    assert carrier is not None
    assert carrier.preflight_context["ansible_plugin_enabled"] is True
    assert carrier.preflight_context["plugin_name"] == "default"
    assert carrier.routing == {
        "mode": "scan_pipeline_plugin",
        "selected_plugin": "default",
        "selection_order": [
            "request.option.scan_pipeline_plugin",
            "policy_context.selection.plugin",
            "platform",
            "registry_default",
        ],
    }


def test_fsrc_kernel_route_orchestration_default_unavailable_raises_when_strict(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    def _legacy_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "legacy", "role_path": role_path, "scan_options": scan_options}

    def _kernel_orchestrator(
        *,
        role_path: str,
        scan_options: dict[str, object],
        route_preflight_runtime=None,
    ) -> dict[str, object]:
        return {
            "lane": "kernel",
            "role_path": role_path,
            "scan_options": scan_options,
            "route_preflight_runtime": route_preflight_runtime,
        }

    class _MissingRegistry:
        def get_scan_pipeline_plugin(self, _name: str):
            return None

    monkeypatch.setattr(
        orchestrator_module, "DEFAULT_PLUGIN_REGISTRY", _MissingRegistry()
    )
    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"x": 1, "strict_phase_failures": True},
            legacy_orchestrator_fn=_legacy_orchestrator,
            kernel_orchestrator_fn=_kernel_orchestrator,
        )

    assert exc_info.value.code == "scan_pipeline_default_unavailable"
    assert exc_info.value.detail == {
        "metadata": {
            "routing": {
                "mode": "legacy_orchestrator",
                "selection_order": [
                    "request.option.scan_pipeline_plugin",
                    "policy_context.selection.plugin",
                    "platform",
                    "registry_default",
                ],
                "failure_mode": "registry_default_plugin_unavailable",
            }
        }
    }


def test_fsrc_kernel_route_orchestration_plugin_error_raises_when_strict(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    def _legacy_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "legacy", "role_path": role_path, "scan_options": scan_options}

    def _kernel_orchestrator(
        *,
        role_path: str,
        scan_options: dict[str, object],
        route_preflight_runtime=None,
    ) -> dict[str, object]:
        return {
            "lane": "kernel",
            "role_path": role_path,
            "scan_options": scan_options,
            "route_preflight_runtime": route_preflight_runtime,
        }

    class _FailingPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options
            del scan_context
            raise RuntimeError("router boom")

    class _FailingRegistry:
        def get_scan_pipeline_plugin(self, _name: str):
            return _FailingPlugin

    monkeypatch.setattr(
        orchestrator_module, "DEFAULT_PLUGIN_REGISTRY", _FailingRegistry()
    )

    with pytest.raises(errors_module.PrismRuntimeError):
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"x": 1, "strict_phase_failures": True},
            legacy_orchestrator_fn=_legacy_orchestrator,
            kernel_orchestrator_fn=_kernel_orchestrator,
        )


def test_fsrc_kernel_route_orchestration_plugin_error_falls_back_when_not_strict(
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

    class _FailingPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options
            del scan_context
            raise RuntimeError("router boom")

    class _FailingRegistry:
        def get_scan_pipeline_plugin(self, _name: str):
            return _FailingPlugin

    monkeypatch.setattr(
        orchestrator_module, "DEFAULT_PLUGIN_REGISTRY", _FailingRegistry()
    )

    result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"x": 1, "strict_phase_failures": False},
        legacy_orchestrator_fn=_legacy_orchestrator,
        kernel_orchestrator_fn=_kernel_orchestrator,
    )

    assert result["lane"] == "legacy"


def test_fsrc_kernel_route_orchestration_registry_error_raises_when_strict(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    def _legacy_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "legacy", "role_path": role_path, "scan_options": scan_options}

    def _kernel_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "kernel", "role_path": role_path, "scan_options": scan_options}

    class _FailingRegistry:
        def get_scan_pipeline_plugin(self, _name: str):
            raise RuntimeError("registry boom")

    monkeypatch.setattr(
        orchestrator_module, "DEFAULT_PLUGIN_REGISTRY", _FailingRegistry()
    )

    with pytest.raises(errors_module.PrismRuntimeError):
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"x": 1, "strict_phase_failures": True},
            legacy_orchestrator_fn=_legacy_orchestrator,
            kernel_orchestrator_fn=_kernel_orchestrator,
        )


def test_fsrc_kernel_route_orchestration_registry_error_falls_back_when_not_strict(
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

    class _FailingRegistry:
        def get_scan_pipeline_plugin(self, _name: str):
            raise RuntimeError("registry boom")

    monkeypatch.setattr(
        orchestrator_module, "DEFAULT_PLUGIN_REGISTRY", _FailingRegistry()
    )

    result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"x": 1, "strict_phase_failures": False},
        legacy_orchestrator_fn=_legacy_orchestrator,
        kernel_orchestrator_fn=_kernel_orchestrator,
    )

    assert result["lane"] == "legacy"


def test_fsrc_kernel_route_orchestration_default_unavailable_warns_with_contract_metadata(
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

    class _DefaultUnavailableRegistry:
        @staticmethod
        def list_scan_pipeline_plugins() -> list[str]:
            return []

        @staticmethod
        def get_scan_pipeline_plugin(_name: str):
            return None

    monkeypatch.setattr(
        orchestrator_module, "DEFAULT_PLUGIN_REGISTRY", _DefaultUnavailableRegistry()
    )

    result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"strict_phase_failures": False},
        legacy_orchestrator_fn=_legacy_orchestrator,
        kernel_orchestrator_fn=_kernel_orchestrator,
    )

    assert result["lane"] == "legacy"
    assert result["metadata"]["routing"] == {
        "mode": "legacy_orchestrator",
        "selection_order": [
            "request.option.scan_pipeline_plugin",
            "policy_context.selection.plugin",
            "platform",
            "registry_default",
        ],
        "failure_mode": "registry_default_plugin_unavailable",
        "fallback_reason": "registry_default_plugin_unavailable",
        "fallback_applied": True,
    }
    assert result["metadata"]["plugin_runtime_warnings"] == [
        {
            "code": "scan_pipeline_default_unavailable",
            "message": "no scan-pipeline plugin default is registered",
            "metadata": {
                "routing": {
                    "mode": "legacy_orchestrator",
                    "selection_order": [
                        "request.option.scan_pipeline_plugin",
                        "policy_context.selection.plugin",
                        "platform",
                        "registry_default",
                    ],
                    "failure_mode": "registry_default_plugin_unavailable",
                    "fallback_reason": "registry_default_plugin_unavailable",
                    "fallback_applied": True,
                }
            },
        }
    ]


def test_fsrc_kernel_route_orchestration_selected_plugin_missing_warns_with_metadata(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )

    def _legacy_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "legacy", "metadata": {"features": {"task_files_scanned": 1}}}

    def _kernel_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "kernel", "role_path": role_path, "scan_options": scan_options}

    class _MissingRegistry:
        @staticmethod
        def get_scan_pipeline_plugin(_name: str):
            return None

    monkeypatch.setattr(
        orchestrator_module, "DEFAULT_PLUGIN_REGISTRY", _MissingRegistry()
    )
    result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"scan_pipeline_plugin": "custom", "strict_phase_failures": False},
        legacy_orchestrator_fn=_legacy_orchestrator,
        kernel_orchestrator_fn=_kernel_orchestrator,
    )

    assert result["lane"] == "legacy"
    assert result["metadata"]["routing"] == {
        "mode": "legacy_orchestrator",
        "selection_order": [
            "request.option.scan_pipeline_plugin",
            "policy_context.selection.plugin",
            "platform",
            "registry_default",
        ],
        "failure_mode": "selected_plugin_missing",
        "fallback_reason": "selected_plugin_missing",
        "fallback_applied": True,
        "selected_plugin": "custom",
    }
    assert result["metadata"]["plugin_runtime_warnings"] == [
        {
            "code": "scan_pipeline_plugin_missing",
            "message": "selected scan-pipeline plugin is not registered",
            "metadata": {
                "routing": {
                    "mode": "legacy_orchestrator",
                    "selection_order": [
                        "request.option.scan_pipeline_plugin",
                        "policy_context.selection.plugin",
                        "platform",
                        "registry_default",
                    ],
                    "failure_mode": "selected_plugin_missing",
                    "fallback_reason": "selected_plugin_missing",
                    "fallback_applied": True,
                    "selected_plugin": "custom",
                }
            },
        }
    ]


def test_fsrc_kernel_route_orchestration_preflight_failure_warns_with_contract_metadata(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )

    def _legacy_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "legacy", "metadata": {"features": {"task_files_scanned": 1}}}

    def _kernel_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "kernel", "role_path": role_path, "scan_options": scan_options}

    class _FailingPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options
            del scan_context
            raise RuntimeError("preflight boom")

    class _Registry:
        @staticmethod
        def get_scan_pipeline_plugin(_name: str):
            return _FailingPlugin

    monkeypatch.setattr(orchestrator_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
    result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"scan_pipeline_plugin": "custom", "strict_phase_failures": False},
        legacy_orchestrator_fn=_legacy_orchestrator,
        kernel_orchestrator_fn=_kernel_orchestrator,
    )

    assert result["lane"] == "legacy"
    assert result["metadata"]["routing"] == {
        "mode": "legacy_orchestrator",
        "selection_order": [
            "request.option.scan_pipeline_plugin",
            "policy_context.selection.plugin",
            "platform",
            "registry_default",
        ],
        "failure_mode": "preflight_execution_exception",
        "fallback_reason": "preflight_execution_exception",
        "fallback_applied": True,
        "selected_plugin": "custom",
        "preflight_stage": "process_scan_pipeline",
    }
    assert result["metadata"]["plugin_runtime_warnings"][0]["code"] == (
        "scan_pipeline_router_failed"
    )


def test_fsrc_repo_and_collection_context_builders_gate_on_kernel_flag(
    tmp_path: Path,
    monkeypatch,
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

        monkeypatch.setenv("PRISM_KERNEL_ENABLED", "0")
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

        monkeypatch.setenv("PRISM_KERNEL_ENABLED", "1")
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
        monkeypatch.delenv("PRISM_KERNEL_ENABLED", raising=False)


def test_fsrc_scanner_plugins_package_does_not_import_readme_or_reporting() -> None:
    plugin_root = FSRC_SOURCE_ROOT / "prism" / "scanner_plugins"
    violations: list[str] = []
    for plugin_file in sorted(plugin_root.rglob("*.py")):
        imports = [
            line.strip()
            for line in plugin_file.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("from ") or line.strip().startswith("import ")
        ]
        bad = [
            line
            for line in imports
            if "prism.scanner_readme" in line or "prism.scanner_reporting" in line
        ]
        for line in bad:
            relative = plugin_file.relative_to(FSRC_SOURCE_ROOT).as_posix()
            violations.append(f"{relative}: {line}")

    assert not violations, "\n".join(violations)


def test_fsrc_kernel_route_orchestration_uses_scan_pipeline_plugin_selector() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )

    class _CustomPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_context
            assert scan_options.get("scan_pipeline_plugin") == "custom"
            return {"plugin_enabled": True, "plugin_runtime_marker": "custom"}

    class _Registry:
        def get_scan_pipeline_plugin(self, name: str):
            if name == "custom":
                return _CustomPlugin
            return None

    def _legacy_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "legacy", "role_path": role_path, "scan_options": scan_options}

    def _kernel_orchestrator(
        *,
        role_path: str,
        scan_options: dict[str, object],
        route_preflight_runtime=None,
    ) -> dict[str, object]:
        return {
            "lane": "kernel",
            "role_path": role_path,
            "scan_options": scan_options,
            "route_preflight_runtime": route_preflight_runtime,
        }

    original_registry = orchestrator_module.DEFAULT_PLUGIN_REGISTRY
    orchestrator_module.DEFAULT_PLUGIN_REGISTRY = _Registry()
    try:
        result = orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"scan_pipeline_plugin": "custom"},
            legacy_orchestrator_fn=_legacy_orchestrator,
            kernel_orchestrator_fn=_kernel_orchestrator,
        )
    finally:
        orchestrator_module.DEFAULT_PLUGIN_REGISTRY = original_registry

    assert result["lane"] == "kernel"
    carrier = result.get("route_preflight_runtime")
    assert carrier is not None
    assert carrier.plugin_name == "custom"
    assert carrier.preflight_context["plugin_runtime_marker"] == "custom"
    assert carrier.routing == {
        "mode": "scan_pipeline_plugin",
        "selected_plugin": "custom",
        "selection_order": [
            "request.option.scan_pipeline_plugin",
            "policy_context.selection.plugin",
            "platform",
            "registry_default",
        ],
    }


def test_fsrc_kernel_route_orchestration_uses_policy_context_selection_plugin() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )

    class _CustomPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_context
            assert scan_options.get("scan_pipeline_plugin") is None
            policy_context = scan_options.get("policy_context")
            assert isinstance(policy_context, dict)
            assert policy_context.get("selection") == {"plugin": "custom"}
            return {"plugin_enabled": True, "plugin_runtime_marker": "custom"}

    class _Registry:
        def get_scan_pipeline_plugin(self, name: str):
            if name == "custom":
                return _CustomPlugin
            return None

    def _legacy_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "legacy", "role_path": role_path, "scan_options": scan_options}

    def _kernel_orchestrator(
        *,
        role_path: str,
        scan_options: dict[str, object],
        route_preflight_runtime=None,
    ) -> dict[str, object]:
        return {
            "lane": "kernel",
            "role_path": role_path,
            "scan_options": scan_options,
            "route_preflight_runtime": route_preflight_runtime,
        }

    original_registry = orchestrator_module.DEFAULT_PLUGIN_REGISTRY
    orchestrator_module.DEFAULT_PLUGIN_REGISTRY = _Registry()
    try:
        result = orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={
                "policy_context": {"selection": {"plugin": "custom"}},
                "platform": "ansible",
            },
            legacy_orchestrator_fn=_legacy_orchestrator,
            kernel_orchestrator_fn=_kernel_orchestrator,
        )
    finally:
        orchestrator_module.DEFAULT_PLUGIN_REGISTRY = original_registry

    assert result["lane"] == "kernel"
    assert "_scan_pipeline_preflight_context" not in result["scan_options"]
    carrier = result["route_preflight_runtime"]
    assert carrier is not None
    assert carrier.plugin_name == "custom"
    assert carrier.preflight_context["plugin_runtime_marker"] == "custom"


def test_fsrc_kernel_route_orchestration_prefers_explicit_selector_over_policy() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )

    class _ExplicitPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_context
            assert scan_options.get("scan_pipeline_plugin") == "explicit"
            return {"plugin_enabled": True, "plugin_runtime_marker": "explicit"}

    class _PolicyPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options
            del scan_context
            raise AssertionError("explicit selector should win over policy context")

    class _Registry:
        def get_scan_pipeline_plugin(self, name: str):
            if name == "explicit":
                return _ExplicitPlugin
            if name == "policy":
                return _PolicyPlugin
            return None

    def _legacy_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "legacy", "role_path": role_path, "scan_options": scan_options}

    def _kernel_orchestrator(
        *,
        role_path: str,
        scan_options: dict[str, object],
        route_preflight_runtime=None,
    ) -> dict[str, object]:
        return {
            "lane": "kernel",
            "role_path": role_path,
            "scan_options": scan_options,
            "route_preflight_runtime": route_preflight_runtime,
        }

    original_registry = orchestrator_module.DEFAULT_PLUGIN_REGISTRY
    orchestrator_module.DEFAULT_PLUGIN_REGISTRY = _Registry()
    try:
        result = orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={
                "scan_pipeline_plugin": "explicit",
                "policy_context": {"selection": {"plugin": "policy"}},
            },
            legacy_orchestrator_fn=_legacy_orchestrator,
            kernel_orchestrator_fn=_kernel_orchestrator,
        )
    finally:
        orchestrator_module.DEFAULT_PLUGIN_REGISTRY = original_registry

    assert result["lane"] == "kernel"
    assert "_scan_pipeline_preflight_context" not in result["scan_options"]
    carrier = result["route_preflight_runtime"]
    assert carrier is not None
    assert carrier.plugin_name == "explicit"
    assert carrier.preflight_context["plugin_runtime_marker"] == "explicit"
