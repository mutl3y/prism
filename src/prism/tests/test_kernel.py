"""Unit tests for prism.scanner_plugins.ansible.kernel (FIND-13 closure)."""

from __future__ import annotations

from prism.scanner_core.protocols_runtime import (
    KernelLifecyclePlugin,
    KernelRequest,
    KernelResponse,
)
from prism.scanner_data.contracts_output import RunScanOutputPayload
from prism.scanner_data.contracts_request import ScanOptionsDict

from prism.scanner_plugins.ansible.kernel import (
    ANSIBLE_KERNEL_PLUGIN_MANIFEST,
    AnsibleBaselineKernelPlugin,
    PLUGIN_CONTRACT_VERSION,
    load_ansible_kernel_plugin,
)


def test_plugin_contract_version_is_v1() -> None:
    assert PLUGIN_CONTRACT_VERSION["major"] == 1
    assert PLUGIN_CONTRACT_VERSION["minor"] == 0


def test_load_returns_baseline_plugin_instance() -> None:
    plugin = load_ansible_kernel_plugin()
    assert isinstance(plugin, AnsibleBaselineKernelPlugin)


def test_plugin_satisfies_runtime_lifecycle_protocol() -> None:
    plugin = load_ansible_kernel_plugin()
    assert isinstance(plugin, KernelLifecyclePlugin)


def test_manifest_exposes_plugin_id_and_capabilities() -> None:
    assert ANSIBLE_KERNEL_PLUGIN_MANIFEST["plugin_id"] == "prism.ansible.baseline.v1"
    capabilities = ANSIBLE_KERNEL_PLUGIN_MANIFEST["capabilities"]
    assert capabilities["platform"] == "ansible"
    assert capabilities["supports_provenance"] is True
    assert capabilities["supports_incremental"] is False


def test_prepare_includes_metadata() -> None:
    plugin = load_ansible_kernel_plugin()
    request: KernelRequest = {"platform": "ansible"}
    result = plugin.prepare(request)
    assert result["metadata"]["plugin_id"] == "prism.ansible.baseline.v1"
    assert result["metadata"]["platform"] == "ansible"


def test_prepare_defaults_platform_to_ansible_when_missing() -> None:
    plugin = load_ansible_kernel_plugin()
    result = plugin.prepare(KernelRequest())
    assert result["metadata"]["platform"] == "ansible"


def test_scan_without_orchestrator_returns_empty_payload_skeleton() -> None:
    plugin = load_ansible_kernel_plugin()
    request: KernelRequest = {"scan_id": "S1", "target_path": "/r"}
    response = plugin.scan(request)
    payload = response["payload"]
    assert payload["role_name"] == ""
    assert payload["display_variables"] == {}
    assert payload["requirements_display"] == []
    assert response["metadata"]["scan_id"] == "S1"


def test_scan_with_orchestrator_invokes_callable_with_role_path_and_options() -> None:
    captured: dict[str, object] = {}
    scan_options: ScanOptionsDict = {
        "role_path": "/role",
        "role_name_override": None,
        "readme_config_path": None,
        "policy_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": None,
        "detailed_catalog": True,
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

    def fake_orchestrator(
        *, role_path: str, scan_options: ScanOptionsDict | None
    ) -> RunScanOutputPayload:
        captured["role_path"] = role_path
        captured["scan_options"] = scan_options
        return {
            "role_name": "r",
            "description": "",
            "display_variables": {"a": {}},
            "requirements_display": [],
            "undocumented_default_filters": [],
            "metadata": {},
        }

    plugin = load_ansible_kernel_plugin(orchestrate_scan_payload_fn=fake_orchestrator)
    request: KernelRequest = {
        "scan_id": "S2",
        "target_path": "/role",
        "options": scan_options,
    }
    response = plugin.scan(request)
    assert captured == {
        "role_path": "/role",
        "scan_options": scan_options,
    }
    assert response["payload"]["role_name"] == "r"


def test_analyze_reports_phase_results_keys() -> None:
    plugin = load_ansible_kernel_plugin()
    request: KernelRequest = {"scan_id": "S3"}
    response: KernelResponse = {"phase_results": {"prepare": {}, "scan": {}}}
    response = plugin.analyze(
        request,
        response,
    )
    assert response["metadata"]["plugin_analyze"] == "completed"
    assert sorted(response["metadata"]["phase_results"]) == ["prepare", "scan"]


def test_finalize_reports_payload_presence() -> None:
    plugin = load_ansible_kernel_plugin()
    request: KernelRequest = {"scan_id": "S"}
    with_payload = plugin.finalize(request, {"payload": {"k": 1}})
    without_payload = plugin.finalize(request, KernelResponse())
    assert with_payload["metadata"]["has_payload"] is True
    assert without_payload["metadata"]["has_payload"] is False
