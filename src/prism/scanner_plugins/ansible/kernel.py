"""Ansible kernel plugin contract and loader for the fsrc lane."""

from __future__ import annotations

import types

from prism.scanner_plugins.interfaces import (
    KernelPhaseOutput,
    KernelRequest,
    KernelResponse,
    KernelScanPayloadOrchestrator,
)
from prism.scanner_data.contracts_output import RunScanOutputPayload


PLUGIN_CONTRACT_VERSION: types.MappingProxyType[str, int] = types.MappingProxyType(
    {"major": 1, "minor": 0}
)


class AnsibleBaselineKernelPlugin:
    """Baseline contract-v1 plugin for ansible scan orchestration."""

    PLUGIN_IS_STATELESS = True

    contract_v1: types.MappingProxyType[str, object] = types.MappingProxyType(
        {
            "plugin_id": "prism.ansible.baseline.v1",
            "contract_version": dict(PLUGIN_CONTRACT_VERSION),
            "capabilities": {
                "platform": "ansible",
                "supports_provenance": True,
                "supports_dry_run": True,
                "supports_incremental": False,
            },
            "lifecycle_phases": ["prepare", "scan", "analyze", "finalize"],
        }
    )

    def __init__(
        self,
        *,
        orchestrate_scan_payload_fn: KernelScanPayloadOrchestrator | None = None,
    ) -> None:
        self._orchestrate_scan_payload_fn = orchestrate_scan_payload_fn

    def prepare(self, request: KernelRequest) -> KernelPhaseOutput:
        return {
            "metadata": {
                "plugin_id": self.contract_v1["plugin_id"],
                "platform": request.get("platform", "ansible"),
            }
        }

    def scan(self, request: KernelRequest) -> KernelPhaseOutput:
        if callable(self._orchestrate_scan_payload_fn):
            payload = self._orchestrate_scan_payload_fn(
                role_path=str(request.get("target_path") or ""),
                scan_options=request.get("options"),
            )
        else:
            payload = _empty_run_scan_output_payload()
        return {
            "payload": payload,
            "metadata": {
                "plugin_id": self.contract_v1["plugin_id"],
                "scan_id": request.get("scan_id"),
            },
        }

    def analyze(
        self,
        request: KernelRequest,
        response: KernelResponse,
    ) -> KernelPhaseOutput:
        return {
            "metadata": {
                "plugin_analyze": "completed",
                "scan_id": request.get("scan_id"),
                "phase_results": list((response.get("phase_results") or {}).keys()),
            }
        }

    def finalize(
        self,
        request: KernelRequest,
        response: KernelResponse,
    ) -> KernelPhaseOutput:
        return {
            "metadata": {
                "plugin_finalize": "completed",
                "scan_id": request.get("scan_id"),
                "has_payload": isinstance(response.get("payload"), dict),
            }
        }


def _empty_run_scan_output_payload() -> RunScanOutputPayload:
    return {
        "role_name": "",
        "description": "",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }


ANSIBLE_KERNEL_PLUGIN_MANIFEST: dict[str, object] = dict(
    AnsibleBaselineKernelPlugin.contract_v1
)


def load_ansible_kernel_plugin(
    *,
    orchestrate_scan_payload_fn: KernelScanPayloadOrchestrator | None = None,
) -> AnsibleBaselineKernelPlugin:
    """Return a baseline ansible plugin instance."""
    return AnsibleBaselineKernelPlugin(
        orchestrate_scan_payload_fn=orchestrate_scan_payload_fn,
    )
