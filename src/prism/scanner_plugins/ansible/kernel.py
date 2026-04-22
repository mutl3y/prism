"""Ansible kernel plugin contract and loader for the fsrc lane."""

from __future__ import annotations

from typing import Any, Callable


PLUGIN_CONTRACT_VERSION = {"major": 1, "minor": 0}


class AnsibleBaselineKernelPlugin:
    """Baseline contract-v1 plugin for ansible scan orchestration."""

    contract_v1: dict[str, Any] = {
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

    def __init__(
        self,
        *,
        orchestrate_scan_payload_fn: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self._orchestrate_scan_payload_fn = orchestrate_scan_payload_fn

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        return {
            "metadata": {
                "plugin_id": self.contract_v1["plugin_id"],
                "platform": request.get("platform", "ansible"),
            }
        }

    def scan(self, request: dict[str, Any]) -> dict[str, Any]:
        if callable(self._orchestrate_scan_payload_fn):
            payload = self._orchestrate_scan_payload_fn(
                role_path=str(request.get("target_path") or ""),
                scan_options=dict(request.get("options") or {}),
            )
        else:
            payload = {
                "role_name": "",
                "description": "",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {},
            }
        return {
            "payload": payload,
            "metadata": {
                "plugin_id": self.contract_v1["plugin_id"],
                "scan_id": request.get("scan_id"),
            },
        }

    def analyze(
        self,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "metadata": {
                "plugin_analyze": "completed",
                "scan_id": request.get("scan_id"),
                "phase_results": list((response.get("phase_results") or {}).keys()),
            }
        }

    def finalize(
        self,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "metadata": {
                "plugin_finalize": "completed",
                "scan_id": request.get("scan_id"),
                "has_payload": isinstance(response.get("payload"), dict),
            }
        }


ANSIBLE_KERNEL_PLUGIN_MANIFEST: dict[str, Any] = dict(
    AnsibleBaselineKernelPlugin.contract_v1
)


def load_ansible_kernel_plugin(
    *,
    orchestrate_scan_payload_fn: Callable[..., dict[str, Any]] | None = None,
) -> AnsibleBaselineKernelPlugin:
    """Return a baseline ansible plugin instance."""
    return AnsibleBaselineKernelPlugin(
        orchestrate_scan_payload_fn=orchestrate_scan_payload_fn,
    )
