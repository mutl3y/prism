"""Tests that platform routing fails closed for unsupported and unregistered platforms."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

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


def _legacy_fn(role_path: str, scan_options: dict[str, Any]) -> dict[str, Any]:
    return {"role_name": "legacy_fallback_role", "metadata": {"legacy": True}}


def test_kubernetes_platform_produces_explicit_not_supported_outcome() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")

    result = orchestrator.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"platform": "kubernetes", "strict_phase_failures": False},
        legacy_orchestrator_fn=_legacy_fn,
        kernel_orchestrator_fn=lambda **kw: {},
    )

    assert (
        result.get("role_name") != "legacy_fallback_role"
    ), "kubernetes routing must not fall back to legacy"
    outcome = result.get("metadata", {}).get("platform_routing_outcome", {})
    assert outcome.get("outcome") == "PLATFORM_NOT_SUPPORTED"
    assert outcome.get("platform") == "kubernetes"
    assert outcome.get("supported") is False


def test_terraform_platform_produces_explicit_not_supported_outcome() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")

    result = orchestrator.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"platform": "terraform", "strict_phase_failures": False},
        legacy_orchestrator_fn=_legacy_fn,
        kernel_orchestrator_fn=lambda **kw: {},
    )

    assert (
        result.get("role_name") != "legacy_fallback_role"
    ), "terraform routing must not fall back to legacy"
    outcome = result.get("metadata", {}).get("platform_routing_outcome", {})
    assert outcome.get("outcome") == "PLATFORM_NOT_SUPPORTED"
    assert outcome.get("platform") == "terraform"
    assert outcome.get("supported") is False


def test_unregistered_explicit_platform_produces_explicit_not_registered_outcome() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

    empty_registry = registry_module.PluginRegistry()

    result = orchestrator.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={
            "platform": "unknown_platform_xyz",
            "strict_phase_failures": False,
        },
        legacy_orchestrator_fn=_legacy_fn,
        kernel_orchestrator_fn=lambda **kw: {},
        registry=empty_registry,
    )

    assert (
        result.get("role_name") != "legacy_fallback_role"
    ), "unregistered explicit platform must not fall back to legacy"
    outcome = result.get("metadata", {}).get("platform_routing_outcome", {})
    assert outcome.get("outcome") == "PLATFORM_NOT_REGISTERED"
    assert outcome.get("platform") == "unknown_platform_xyz"
    assert outcome.get("supported") is False


def test_unregistered_explicit_scan_pipeline_plugin_produces_not_registered_outcome() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        registry_module = importlib.import_module("prism.scanner_plugins.registry")

    empty_registry = registry_module.PluginRegistry()

    result = orchestrator.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={
            "scan_pipeline_plugin": "no_such_plugin",
            "strict_phase_failures": False,
        },
        legacy_orchestrator_fn=_legacy_fn,
        kernel_orchestrator_fn=lambda **kw: {},
        registry=empty_registry,
    )

    assert result.get("role_name") != "legacy_fallback_role"
    outcome = result.get("metadata", {}).get("platform_routing_outcome", {})
    assert outcome.get("outcome") == "PLATFORM_NOT_REGISTERED"
    assert outcome.get("platform") == "no_such_plugin"
    assert outcome.get("supported") is False


def test_kubernetes_strict_mode_raises_platform_not_supported() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        errors_module = importlib.import_module("prism.errors")

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"platform": "kubernetes", "strict_phase_failures": True},
            legacy_orchestrator_fn=_legacy_fn,
            kernel_orchestrator_fn=lambda **kw: {},
        )

    assert exc_info.value.code == "platform_not_supported"


def test_terraform_strict_mode_raises_platform_not_supported() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")
        errors_module = importlib.import_module("prism.errors")

    with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
        orchestrator.route_scan_payload_orchestration(
            role_path="/tmp/role",
            scan_options={"platform": "terraform", "strict_phase_failures": True},
            legacy_orchestrator_fn=_legacy_fn,
            kernel_orchestrator_fn=lambda **kw: {},
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
            legacy_orchestrator_fn=_legacy_fn,
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
        legacy_orchestrator_fn=_legacy_fn,
        kernel_orchestrator_fn=_ansible_kernel,
        registry=registry,
    )

    assert received_route.get(
        "called"
    ), "kernel_orchestrator_fn must be called for ansible"
    assert (
        result.get("metadata", {}).get("platform_routing_outcome") is None
    ), "normal ansible routing must not produce an unsupported outcome"


def test_no_legacy_fallback_for_kubernetes_regardless_of_strict_mode() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        orchestrator = importlib.import_module("prism.scanner_kernel.orchestrator")

    legacy_was_called = []

    def _tracking_legacy(
        role_path: str, scan_options: dict[str, Any]
    ) -> dict[str, Any]:
        legacy_was_called.append(True)
        return {"role_name": "legacy_role", "metadata": {}}

    result = orchestrator.route_scan_payload_orchestration(
        role_path="/tmp/role",
        scan_options={"platform": "kubernetes", "strict_phase_failures": False},
        legacy_orchestrator_fn=_tracking_legacy,
        kernel_orchestrator_fn=lambda **kw: {},
    )

    assert (
        not legacy_was_called
    ), "legacy orchestrator must NOT be called for kubernetes"
    outcome = result.get("metadata", {}).get("platform_routing_outcome", {})
    assert outcome.get("outcome") == "PLATFORM_NOT_SUPPORTED"


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
