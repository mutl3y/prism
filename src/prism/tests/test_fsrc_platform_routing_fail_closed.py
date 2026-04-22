"""Tests that platform routing fails closed for unsupported and unregistered platforms."""

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


def test_kubernetes_platform_raises_not_supported_in_non_strict_mode() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        errors_module = importlib.import_module("prism.errors")
        scanner_plugins = importlib.import_module("prism.scanner_plugins")

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"platform": "kubernetes", "strict_phase_failures": False},
            kernel_orchestrator_fn=lambda **kw: {},
            registry=scanner_plugins.DEFAULT_PLUGIN_REGISTRY,
        )

    assert exc_info.value.code == "platform_not_supported"


def test_terraform_platform_raises_not_supported_in_non_strict_mode() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        errors_module = importlib.import_module("prism.errors")
        scanner_plugins = importlib.import_module("prism.scanner_plugins")

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"platform": "terraform", "strict_phase_failures": False},
            kernel_orchestrator_fn=lambda **kw: {},
            registry=scanner_plugins.DEFAULT_PLUGIN_REGISTRY,
        )

    assert exc_info.value.code == "platform_not_supported"


def test_unregistered_explicit_platform_raises_not_registered_in_non_strict_mode() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        errors_module = importlib.import_module("prism.errors")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

    empty_registry = registry_module.PluginRegistry()

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={
                "platform": "unknown_platform_xyz",
                "strict_phase_failures": False,
            },
            kernel_orchestrator_fn=lambda **kw: {},
            registry=empty_registry,
        )

    assert exc_info.value.code == "platform_not_registered"


def test_unregistered_explicit_scan_pipeline_plugin_raises_not_registered_in_non_strict_mode() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        errors_module = importlib.import_module("prism.errors")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

    empty_registry = registry_module.PluginRegistry()

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={
                "scan_pipeline_plugin": "no_such_plugin",
                "strict_phase_failures": False,
            },
            kernel_orchestrator_fn=lambda **kw: {},
            registry=empty_registry,
        )

    assert exc_info.value.code == "platform_not_registered"


def test_kubernetes_strict_mode_raises_platform_not_supported() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        errors_module = importlib.import_module("prism.errors")
        scanner_plugins = importlib.import_module("prism.scanner_plugins")

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"platform": "kubernetes", "strict_phase_failures": True},
            kernel_orchestrator_fn=lambda **kw: {},
            registry=scanner_plugins.DEFAULT_PLUGIN_REGISTRY,
        )

    assert exc_info.value.code == "platform_not_supported"


def test_terraform_strict_mode_raises_platform_not_supported() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        errors_module = importlib.import_module("prism.errors")
        scanner_plugins = importlib.import_module("prism.scanner_plugins")

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"platform": "terraform", "strict_phase_failures": True},
            kernel_orchestrator_fn=lambda **kw: {},
            registry=scanner_plugins.DEFAULT_PLUGIN_REGISTRY,
        )

    assert exc_info.value.code == "platform_not_supported"


def test_unregistered_explicit_platform_strict_mode_raises_platform_not_registered() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")
        errors_module = importlib.import_module("prism.errors")

    empty_registry = registry_module.PluginRegistry()

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={
                "platform": "unknown_platform_xyz",
                "strict_phase_failures": True,
            },
            kernel_orchestrator_fn=lambda **kw: {},
            registry=empty_registry,
        )

    assert exc_info.value.code == "platform_not_registered"


def test_ansible_platform_routing_outcome_absent_on_normal_path() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

    class _MockAnsiblePlugin:
        def process_scan_pipeline(
            self,
            scan_options: dict[str, Any],
            scan_context: dict[str, Any],
        ) -> dict[str, Any]:
            return {"plugin_enabled": True, "ansible_plugin_enabled": True}

    registry = registry_module.PluginRegistry()
    registry.register_scan_pipeline_plugin("ansible", _MockAnsiblePlugin)

    received_route: dict[str, Any] = {}

    def _ansible_kernel(**kw: Any) -> dict[str, Any]:
        received_route["called"] = True
        return {"role_name": "ansible_role", "metadata": {}}

    result = orchestrator.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"platform": "ansible", "strict_phase_failures": False},
        kernel_orchestrator_fn=_ansible_kernel,
        registry=registry,
    )

    assert received_route.get(
        "called"
    ), "kernel_orchestrator_fn must be called for ansible"
    assert (
        result.get("metadata", {}).get("platform_routing_outcome") is None
    ), "normal ansible routing must not produce an unsupported outcome"


def test_kubernetes_stub_unsupported_scan_pipeline_outcome_shape() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        kubernetes_module = importlib.import_module("prism.scanner_plugins.kubernetes")

    outcome = kubernetes_module.build_unsupported_scan_pipeline_outcome()

    assert outcome["outcome"] == "PLATFORM_NOT_SUPPORTED"
    assert outcome["supported"] is False
    assert outcome.get("degraded_success") is not True


def test_terraform_stub_unsupported_scan_pipeline_outcome_shape() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        terraform_module = importlib.import_module("prism.scanner_plugins.terraform")

    outcome = terraform_module.build_unsupported_scan_pipeline_outcome()

    assert outcome["outcome"] == "PLATFORM_NOT_SUPPORTED"
    assert outcome["supported"] is False
    assert outcome.get("degraded_success") is not True


def test_kubernetes_stub_reserved_capability_response_no_longer_degraded_success() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        kubernetes_module = importlib.import_module("prism.scanner_plugins.kubernetes")

    response = kubernetes_module.build_reserved_target_capability_response()

    assert response.get("degraded_success") is not True


def test_terraform_stub_reserved_capability_response_no_longer_degraded_success() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        terraform_module = importlib.import_module("prism.scanner_plugins.terraform")

    response = terraform_module.build_reserved_target_capability_response()

    assert response.get("degraded_success") is not True
