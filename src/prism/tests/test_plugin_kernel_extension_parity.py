"""Parity checks for fsrc scanner plugin/kernel ownership seams."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> Iterator[None]:
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


def test_fsrc_scanner_data_exports_collection_runtime_contract_components() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_data = importlib.import_module("prism.scanner_data")

    expected_exports = {
        "CollectionDependencies",
        "CollectionFailureRecord",
        "CollectionIdentity",
        "CollectionPluginCatalog",
        "CollectionRoleEntry",
        "CollectionScanResult",
        "CollectionSummary",
    }

    assert expected_exports.issubset(set(scanner_data.__all__))
    assert expected_exports.issubset(set(dir(scanner_data)))


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
        def __init__(self, *, di=None) -> None:
            self.di = di

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


def test_fsrc_defaults_non_strict_shape_validation_raises_for_malformed_plugin() -> (
    None
):
    class _MalformedTaskLinePlugin:
        pass

    class _DI:
        def factory_task_line_parsing_policy_plugin(self) -> _MalformedTaskLinePlugin:
            return _MalformedTaskLinePlugin()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        default_policies_module = importlib.import_module(
            "prism.scanner_plugins.ansible.default_policies"
        )
        plugin = defaults_module.resolve_task_line_parsing_policy_plugin(
            _DI(),
            strict_mode=False,
        )

    assert isinstance(
        plugin,
        default_policies_module.AnsibleDefaultTaskLineParsingPolicyPlugin,
    )


def test_fsrc_default_plugin_registry_bootstrap_registers_required_plugins() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_plugins = importlib.import_module("prism.scanner_plugins")
        ansible_plugins = importlib.import_module("prism.scanner_plugins.ansible")
        default_pipeline_module = importlib.import_module(
            "prism.scanner_plugins.default_scan_pipeline"
        )
        comment_doc_module = importlib.import_module(
            "prism.scanner_plugins.parsers.comment_doc.role_notes_parser"
        )
        registry = scanner_plugins.get_default_plugin_registry()

        assert "default" in set(registry.list_comment_driven_doc_plugins())
        assert "default" in set(registry.list_scan_pipeline_plugins())
        assert "ansible" in set(registry.list_scan_pipeline_plugins())
        assert (
            registry.get_comment_driven_doc_plugin("default")
            is comment_doc_module.CommentDrivenDocumentationParser
        )
        assert (
            registry.get_scan_pipeline_plugin("default")
            is default_pipeline_module.DefaultScanPipelinePlugin
        )
        assert (
            registry.get_scan_pipeline_plugin("ansible")
            is ansible_plugins.AnsibleScanPipelinePlugin
        )


def test_fsrc_default_plugin_registry_aligns_with_canonical_singleton() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_plugins = importlib.import_module("prism.scanner_plugins")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        assert (
            scanner_plugins.get_default_plugin_registry()
            is registry_module.plugin_registry
        )


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
        default_pipeline_module = importlib.import_module(
            "prism.scanner_plugins.default_scan_pipeline"
        )
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

    registered_comment_doc = registry.get_comment_driven_doc_plugin("default")
    registered_default_pipeline = registry.get_scan_pipeline_plugin("default")
    registered_ansible_pipeline = registry.get_scan_pipeline_plugin("ansible")

    assert registered_comment_doc is not None
    assert registered_default_pipeline is not None
    assert registered_ansible_pipeline is not None
    assert registered_comment_doc.__module__ == comment_doc_module.__name__
    assert (
        registered_comment_doc.__name__
        == comment_doc_module.CommentDrivenDocumentationParser.__name__
    )
    assert registered_default_pipeline.__module__ == default_pipeline_module.__name__
    assert (
        registered_default_pipeline.__name__
        == default_pipeline_module.DefaultScanPipelinePlugin.__name__
    )
    assert registered_ansible_pipeline.__module__ == ansible_plugins.__name__
    assert (
        registered_ansible_pipeline.__name__
        == ansible_plugins.AnsibleScanPipelinePlugin.__name__
    )


def test_fsrc_required_ansible_scan_pipeline_plugin_process_contract() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_plugins = importlib.import_module("prism.scanner_plugins")

    plugin_class = (
        scanner_plugins.get_default_plugin_registry().get_scan_pipeline_plugin(
            "ansible"
        )
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
        errors_module = importlib.import_module("prism.errors")

    class _DisabledPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options
            del scan_context
            return {"plugin_enabled": False}

    class _EnabledPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options
            del scan_context
            return {"plugin_enabled": True}

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
        def get_default_platform_key(self) -> str:
            return "ansible"

        def get_scan_pipeline_plugin(self, name: str):
            assert name == "ansible"
            return _DisabledPlugin

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"x": 1},
            kernel_orchestrator_fn=_kernel_orchestrator,
            registry=_DisabledRegistry(),
        )

    assert exc_info.value.code == "scan_pipeline_plugin_disabled"

    class _EnabledRegistry:
        def get_default_platform_key(self) -> str:
            return "ansible"

        def get_scan_pipeline_plugin(self, name: str):
            assert name == "ansible"
            return _EnabledPlugin

    kernel_result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"x": 1},
        kernel_orchestrator_fn=_kernel_orchestrator,
        registry=_EnabledRegistry(),
    )

    assert kernel_result["lane"] == "kernel"
    assert "_scan_pipeline_preflight_context" not in kernel_result["scan_options"]
    carrier = kernel_result["route_preflight_runtime"]
    assert carrier is not None
    assert carrier.preflight_context["plugin_enabled"] is True
    assert carrier.preflight_context["plugin_name"] == "ansible"
    assert carrier.routing == {
        "mode": "scan_pipeline_plugin",
        "selected_plugin": "ansible",
        "selection_order": [
            "request.option.scan_pipeline_plugin",
            "policy_context.selection.plugin",
            "platform",
            "registry_default",
        ],
    }


def test_fsrc_kernel_route_orchestration_rejects_non_bool_plugin_enabled() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    class _MalformedPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options
            del scan_context
            return {"plugin_enabled": "yes"}

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

    class _MalformedRegistry:
        def get_default_platform_key(self) -> str:
            return "ansible"

        def get_scan_pipeline_plugin(self, name: str):
            assert name == "ansible"
            return _MalformedPlugin

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"x": 1},
            kernel_orchestrator_fn=_kernel_orchestrator,
            registry=_MalformedRegistry(),
        )

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.detail == {
        "metadata": {
            "routing": {
                "mode": "scan_pipeline_plugin",
                "selected_plugin": "ansible",
                "failure_mode": "invalid_preflight_contract",
            }
        }
    }


def test_fsrc_kernel_route_orchestration_rejects_missing_plugin_enabled() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    class _MissingPluginEnabledPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options
            del scan_context
            return {"plugin_name": "ansible"}

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

    class _MalformedRegistry:
        def get_default_platform_key(self) -> str:
            return "ansible"

        def get_scan_pipeline_plugin(self, name: str):
            assert name == "ansible"
            return _MissingPluginEnabledPlugin

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"x": 1},
            kernel_orchestrator_fn=_kernel_orchestrator,
            registry=_MalformedRegistry(),
        )

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.detail == {
        "metadata": {
            "routing": {
                "mode": "scan_pipeline_plugin",
                "selected_plugin": "ansible",
                "failure_mode": "invalid_preflight_contract",
            }
        }
    }


def test_fsrc_kernel_route_orchestration_default_unavailable_raises_when_strict(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

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
        def get_default_platform_key(self) -> None:
            return None

        def get_scan_pipeline_plugin(self, _name: str):
            return None

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"x": 1, "strict_phase_failures": True},
            kernel_orchestrator_fn=_kernel_orchestrator,
            registry=_MissingRegistry(),
        )

    assert exc_info.value.code == "scan_pipeline_default_unavailable"


def test_fsrc_kernel_route_orchestration_plugin_error_raises(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

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
        def get_default_platform_key(self) -> str:
            return "ansible"

        def get_scan_pipeline_plugin(self, name: str):
            assert name == "ansible"
            return _FailingPlugin

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"x": 1, "strict_phase_failures": True},
            kernel_orchestrator_fn=_kernel_orchestrator,
            registry=_FailingRegistry(),
        )

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.message == "scan-pipeline preflight execution failed"
    assert exc_info.value.detail["metadata"]["routing"] == {
        "mode": "scan_pipeline_plugin",
        "selected_plugin": "ansible",
        "failure_mode": "preflight_execution_exception",
    }


def test_fsrc_kernel_route_orchestration_registry_error_raises(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    def _kernel_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "kernel", "role_path": role_path, "scan_options": scan_options}

    class _FailingRegistry:
        def get_default_platform_key(self) -> str:
            return "ansible"

        def get_scan_pipeline_plugin(self, name: str):
            assert name == "ansible"
            raise RuntimeError("registry boom")

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"x": 1, "strict_phase_failures": True},
            kernel_orchestrator_fn=_kernel_orchestrator,
            registry=_FailingRegistry(),
        )

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.message == "scan-pipeline preflight execution failed"
    assert exc_info.value.detail["metadata"]["routing"] == {
        "mode": "scan_pipeline_plugin",
        "failure_mode": "preflight_resolution_exception",
    }


def test_fsrc_kernel_route_orchestration_missing_plugin_raises(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    def _kernel_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "kernel", "role_path": role_path, "scan_options": scan_options}

    class _MissingRegistry:
        @staticmethod
        def get_scan_pipeline_plugin(_name: str):
            return None

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={
                "scan_pipeline_plugin": "custom",
                "strict_phase_failures": False,
            },
            kernel_orchestrator_fn=_kernel_orchestrator,
            registry=_MissingRegistry(),
        )

    assert exc_info.value.code == "platform_not_registered"


def test_fsrc_kernel_route_orchestration_selected_plugin_missing_raises_with_metadata(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    def _kernel_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "kernel", "role_path": role_path, "scan_options": scan_options}

    class _MissingRegistry:
        @staticmethod
        def get_scan_pipeline_plugin(_name: str):
            return None

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={
                "scan_pipeline_plugin": "custom",
                "strict_phase_failures": False,
            },
            kernel_orchestrator_fn=_kernel_orchestrator,
            registry=_MissingRegistry(),
        )

    assert exc_info.value.code == "platform_not_registered"
    routing = exc_info.value.detail.get("metadata", {}).get("routing", {})
    assert routing == {
        "mode": "unsupported",
        "selection_order": [
            "request.option.scan_pipeline_plugin",
            "policy_context.selection.plugin",
            "platform",
            "registry_default",
        ],
        "failure_mode": "platform_not_registered",
        "selected_plugin": "custom",
    }


def test_fsrc_kernel_route_orchestration_preflight_failure_raises(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

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

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={
                "scan_pipeline_plugin": "custom",
                "strict_phase_failures": False,
            },
            kernel_orchestrator_fn=_kernel_orchestrator,
            registry=_Registry(),
        )

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.message == "scan-pipeline preflight execution failed"
    assert exc_info.value.detail["metadata"]["routing"] == {
        "mode": "scan_pipeline_plugin",
        "selected_plugin": "custom",
        "failure_mode": "preflight_execution_exception",
    }


def test_fsrc_kernel_route_orchestration_invalid_preflight_output_raises_contract_error(
    monkeypatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    def _kernel_orchestrator(
        *, role_path: str, scan_options: dict[str, object]
    ) -> dict[str, object]:
        return {"lane": "kernel", "role_path": role_path, "scan_options": scan_options}

    class _InvalidPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> object:
            del scan_options
            del scan_context
            return ["invalid"]

    class _Registry:
        @staticmethod
        def get_scan_pipeline_plugin(_name: str):
            return _InvalidPlugin

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={
                "scan_pipeline_plugin": "custom",
                "strict_phase_failures": False,
            },
            kernel_orchestrator_fn=_kernel_orchestrator,
            registry=_Registry(),
        )

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.message == (
        "scan-pipeline plugin 'custom' returned invalid preflight output "
        "type 'list'; expected dict"
    )
    assert exc_info.value.detail == {
        "metadata": {
            "routing": {
                "mode": "scan_pipeline_plugin",
                "selected_plugin": "custom",
                "failure_mode": "invalid_preflight_output",
            }
        }
    }


def test_fsrc_scan_pipeline_runtime_constructor_failure_raises_contract_error() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    class _CtorFailurePlugin:
        def __init__(self) -> None:
            raise ValueError("ctor boom")

    class _Registry:
        @staticmethod
        def get_scan_pipeline_plugin(name: str):
            if name == "custom":
                return _CtorFailurePlugin
            return None

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.orchestrate_scan_payload_with_selected_plugin(
            build_payload_fn=lambda: {"metadata": {"existing": True}},
            scan_options={"scan_pipeline_plugin": "custom"},
            strict_mode=False,
            registry=_Registry(),
        )

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.message == "scan-pipeline runtime execution failed"
    assert exc_info.value.detail["metadata"]["routing"] == {
        "mode": "scan_pipeline_plugin",
        "selected_plugin": "custom",
        "failure_mode": "constructor_exception",
    }


def test_fsrc_scan_pipeline_runtime_invalid_output_raises_contract_error() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    class _InvalidPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> object:
            assert scan_options.get("scan_pipeline_plugin") == "custom"
            assert scan_context == {"existing": True}
            return "invalid-output"

    class _Registry:
        @staticmethod
        def get_scan_pipeline_plugin(name: str):
            if name == "custom":
                return _InvalidPlugin
            return None

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.orchestrate_scan_payload_with_selected_plugin(
            build_payload_fn=lambda: {"metadata": {"existing": True}},
            scan_options={"scan_pipeline_plugin": "custom"},
            strict_mode=False,
            registry=_Registry(),
        )

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.message == (
        "scan-pipeline plugin 'custom' returned invalid runtime output "
        "type 'str'; expected dict"
    )
    assert exc_info.value.detail == {
        "metadata": {
            "routing": {
                "mode": "scan_pipeline_plugin",
                "selected_plugin": "custom",
                "failure_mode": "invalid_plugin_output",
            }
        }
    }


def test_fsrc_scan_pipeline_runtime_dict_output_preserves_existing_metadata() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )

    class _ValidPlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            assert scan_options.get("scan_pipeline_plugin") == "custom"
            assert scan_context == {
                "existing": True,
                "nested": {"from_payload": True},
            }
            return {
                "existing": False,
                "nested": {"from_plugin": True},
                "plugin_runtime_marker": "custom",
            }

    class _Registry:
        @staticmethod
        def get_scan_pipeline_plugin(name: str):
            if name == "custom":
                return _ValidPlugin
            return None

    result = orchestrator_module.orchestrate_scan_payload_with_selected_plugin(
        build_payload_fn=lambda: {
            "metadata": {
                "existing": True,
                "nested": {"from_payload": True},
            }
        },
        scan_options={"scan_pipeline_plugin": "custom"},
        strict_mode=False,
        registry=_Registry(),
    )

    assert result == {
        "metadata": {
            "existing": True,
            "nested": {
                "from_payload": True,
                "from_plugin": True,
            },
            "plugin_runtime_marker": "custom",
        }
    }


def test_fsrc_scan_pipeline_direct_runtime_invalid_output_raises_contract_error() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )
        errors_module = importlib.import_module("prism.errors")

    class _InvalidDirectPlugin:
        def orchestrate_scan_payload(
            self,
            *,
            payload: dict[str, object],
            scan_options: dict[str, object],
            strict_mode: bool,
            preflight_context: dict[str, object] | None = None,
        ) -> object:
            assert payload == {"metadata": {"existing": True}}
            assert scan_options.get("scan_pipeline_plugin") == "custom"
            assert strict_mode is False
            assert preflight_context is None
            return "invalid-output"

    class _Registry:
        @staticmethod
        def get_scan_pipeline_plugin(name: str):
            if name == "custom":
                return _InvalidDirectPlugin
            return None

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator_module.orchestrate_scan_payload_with_selected_plugin(
            build_payload_fn=lambda: {"metadata": {"existing": True}},
            scan_options={"scan_pipeline_plugin": "custom"},
            strict_mode=False,
            registry=_Registry(),
        )

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.message == (
        "scan-pipeline plugin 'custom' returned invalid runtime output "
        "type 'str'; expected dict"
    )
    assert exc_info.value.detail == {
        "metadata": {
            "routing": {
                "mode": "scan_pipeline_plugin",
                "selected_plugin": "custom",
                "failure_mode": "invalid_plugin_output",
            }
        }
    }


def test_fsrc_scan_pipeline_direct_runtime_dict_output_passes_through() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )

    class _DirectPlugin:
        def orchestrate_scan_payload(
            self,
            *,
            payload: dict[str, object],
            scan_options: dict[str, object],
            strict_mode: bool,
            preflight_context: dict[str, object] | None = None,
        ) -> dict[str, object]:
            assert payload == {"metadata": {"existing": True}}
            assert scan_options.get("scan_pipeline_plugin") == "custom"
            assert strict_mode is False
            assert preflight_context is None
            return {
                "metadata": {
                    "existing": False,
                    "direct_plugin_marker": "custom",
                },
                "role_name": "direct-plugin-role",
            }

    class _Registry:
        @staticmethod
        def get_scan_pipeline_plugin(name: str):
            if name == "custom":
                return _DirectPlugin
            return None

    result = orchestrator_module.orchestrate_scan_payload_with_selected_plugin(
        build_payload_fn=lambda: {"metadata": {"existing": True}},
        scan_options={"scan_pipeline_plugin": "custom"},
        strict_mode=False,
        registry=_Registry(),
    )

    assert result == {
        "metadata": {
            "existing": False,
            "direct_plugin_marker": "custom",
        },
        "role_name": "direct-plugin-role",
    }


def test_fsrc_scan_pipeline_runtime_uses_preflight_selected_factory_when_registry_mutates() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator_module = importlib.import_module(
            "prism.scanner_kernel.orchestrator"
        )

    class _PluginA:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options, scan_context
            return {
                "plugin_enabled": True,
                "plugin_name": "custom",
                "preflight_marker": "A",
            }

        def orchestrate_scan_payload(
            self,
            *,
            payload: dict[str, object],
            scan_options: dict[str, object],
            strict_mode: bool,
            preflight_context: dict[str, object] | None = None,
        ) -> dict[str, object]:
            del scan_options, strict_mode
            payload.setdefault("metadata", {})["runtime_marker"] = "A"
            payload["metadata"]["preflight_marker_seen"] = (
                preflight_context.get("preflight_marker")
                if isinstance(preflight_context, dict)
                else None
            )
            return payload

    class _PluginB:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, object],
            scan_context: dict[str, object],
        ) -> dict[str, object]:
            del scan_options, scan_context
            return {
                "plugin_enabled": True,
                "plugin_name": "custom",
                "preflight_marker": "B",
            }

        def orchestrate_scan_payload(
            self,
            *,
            payload: dict[str, object],
            scan_options: dict[str, object],
            strict_mode: bool,
            preflight_context: dict[str, object] | None = None,
        ) -> dict[str, object]:
            del scan_options, strict_mode
            payload.setdefault("metadata", {})["runtime_marker"] = "B"
            payload["metadata"]["preflight_marker_seen"] = (
                preflight_context.get("preflight_marker")
                if isinstance(preflight_context, dict)
                else None
            )
            return payload

    class _Registry:
        def __init__(self) -> None:
            self._plugin = _PluginA

        def get_scan_pipeline_plugin(self, name: str):
            if name == "custom":
                return self._plugin
            return None

        def mutate(self) -> None:
            self._plugin = _PluginB

    registry = _Registry()
    carrier_holder: dict[str, object] = {}

    def _kernel_orchestrator(
        *,
        role_path: str,
        scan_options: dict[str, object],
        route_preflight_runtime=None,
    ) -> dict[str, object]:
        del role_path, scan_options
        carrier_holder["carrier"] = route_preflight_runtime
        return {
            "role_name": "demo",
            "description": "x",
            "display_variables": {},
            "requirements_display": [],
            "undocumented_default_filters": [],
            "metadata": {},
        }

    orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"scan_pipeline_plugin": "custom"},
        kernel_orchestrator_fn=_kernel_orchestrator,
        registry=registry,
    )
    registry.mutate()

    result = orchestrator_module.orchestrate_scan_payload_with_selected_plugin(
        build_payload_fn=lambda: {
            "role_name": "demo",
            "description": "x",
            "display_variables": {},
            "requirements_display": [],
            "undocumented_default_filters": [],
            "metadata": {},
        },
        scan_options={"scan_pipeline_plugin": "custom"},
        strict_mode=True,
        route_preflight_runtime=carrier_holder["carrier"],
        registry=registry,
    )

    assert result["metadata"]["runtime_marker"] == "A"
    assert result["metadata"]["preflight_marker_seen"] == "A"


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


def test_fsrc_scanner_plugins_package_does_not_import_scanner_core() -> None:
    """g34-M-006: scanner_plugins must not import scanner_core directly.

    Plugin layer depends only on scanner_data for shared type contracts.
    Cross-layer wiring must flow through DI, not direct imports.
    """
    plugin_root = FSRC_SOURCE_ROOT / "prism" / "scanner_plugins"
    violations: list[str] = []
    for plugin_file in sorted(plugin_root.rglob("*.py")):
        for line in plugin_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not (stripped.startswith("from ") or stripped.startswith("import ")):
                continue
            if "prism.scanner_core" in stripped:
                relative = plugin_file.relative_to(FSRC_SOURCE_ROOT).as_posix()
                violations.append(f"{relative}: {stripped}")

    assert not violations, (
        "scanner_plugins must not import scanner_core (g34-M-006); "
        "use scanner_data contracts or DI injection instead:\n" + "\n".join(violations)
    )


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

    result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"scan_pipeline_plugin": "custom"},
        kernel_orchestrator_fn=_kernel_orchestrator,
        registry=_Registry(),
    )

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

    result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={
            "policy_context": {"selection": {"plugin": "custom"}},
            "platform": "ansible",
        },
        kernel_orchestrator_fn=_kernel_orchestrator,
        registry=_Registry(),
    )

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

    result = orchestrator_module.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={
            "scan_pipeline_plugin": "explicit",
            "policy_context": {"selection": {"plugin": "policy"}},
        },
        kernel_orchestrator_fn=_kernel_orchestrator,
        registry=_Registry(),
    )

    assert result["lane"] == "kernel"
    assert "_scan_pipeline_preflight_context" not in result["scan_options"]
    carrier = result["route_preflight_runtime"]
    assert carrier is not None
    assert carrier.plugin_name == "explicit"
    assert carrier.preflight_context["plugin_runtime_marker"] == "explicit"
