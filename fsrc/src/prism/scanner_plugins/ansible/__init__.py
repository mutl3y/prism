"""Canonical ansible scanner plugin package for the fsrc lane."""

from __future__ import annotations

import copy
from typing import Any

from prism.scanner_plugins.ansible.feature_flags import (
    ANSIBLE_PLUGIN_ENABLED_ENV_VAR,
)
from prism.scanner_plugins.ansible.feature_flags import is_ansible_plugin_enabled
from prism.scanner_plugins.ansible.kernel import ANSIBLE_KERNEL_PLUGIN_MANIFEST
from prism.scanner_plugins.ansible.kernel import AnsibleBaselineKernelPlugin
from prism.scanner_plugins.ansible.kernel import load_ansible_kernel_plugin
from prism.scanner_plugins.ansible.extract_policies import (
    AnsibleTaskAnnotationPolicyPlugin,
)
from prism.scanner_plugins.ansible.extract_policies import (
    AnsibleTaskLineParsingPolicyPlugin,
)
from prism.scanner_plugins.ansible.jinja_analyzer import (
    AnsibleJinjaAnalysisPolicyPlugin,
)
from prism.scanner_plugins.ansible.yaml_parsing import (
    AnsibleYAMLParsingPolicyPlugin,
)
from prism.scanner_data.contracts_request import PreparedPolicyBundle
from prism.scanner_plugins.interfaces import (
    PlatformExecutionBundle,
    PlatformParticipants,
)


class AnsibleScanPipelinePlugin:
    """Scan-pipeline plugin that annotates context with ansible kernel capability."""

    @staticmethod
    def _merge_preserving_existing(
        existing: dict[str, Any],
        incoming: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(existing)
        for key, value in incoming.items():
            if key not in merged:
                merged[key] = value
                continue
            existing_value = merged[key]
            if isinstance(existing_value, dict) and isinstance(value, dict):
                merged[key] = AnsibleScanPipelinePlugin._merge_preserving_existing(
                    existing_value,
                    value,
                )
        return merged

    def process_scan_pipeline(
        self,
        scan_options: dict,
        scan_context: dict,
    ) -> dict:
        context = dict(scan_context)
        context.setdefault("plugin_platform", "ansible")
        context.setdefault("plugin_name", "ansible")
        plugin_enabled = bool(is_ansible_plugin_enabled())
        context["plugin_enabled"] = plugin_enabled
        context["ansible_plugin_enabled"] = plugin_enabled
        if "role_path" in scan_options and "role_path" not in context:
            context["role_path"] = scan_options.get("role_path")
        return context

    def orchestrate_scan_payload(
        self,
        *,
        payload: dict[str, Any],
        scan_options: dict[str, Any],
        strict_mode: bool,
        preflight_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = payload.get("metadata")
        base_metadata = copy.deepcopy(metadata) if isinstance(metadata, dict) else {}

        if isinstance(preflight_context, dict):
            plugin_output: Any = dict(preflight_context)
        else:
            plugin_output = self.process_scan_pipeline(
                scan_options=copy.deepcopy(scan_options),
                scan_context=copy.deepcopy(base_metadata),
            )

        if not isinstance(plugin_output, dict):
            return payload

        payload["metadata"] = AnsibleScanPipelinePlugin._merge_preserving_existing(
            base_metadata,
            plugin_output,
        )
        return payload


def build_ansible_execution_bundle(
    scan_options: dict[str, Any] | None = None,
) -> PlatformExecutionBundle:
    """Build the Ansible-owned platform execution bundle from a scan request.

    Produces a PlatformExecutionBundle carrying Ansible-native policy
    participant instances so scanner_core ingress can receive them through
    the generic contract without manufacturing Ansible defaults internally.
    """
    task_line_parsing = AnsibleTaskLineParsingPolicyPlugin()
    jinja_analysis = AnsibleJinjaAnalysisPolicyPlugin()
    participants: PlatformParticipants = {
        "task_line_parsing": task_line_parsing,
        "jinja_analysis": jinja_analysis,
    }
    prepared_policy: PreparedPolicyBundle = {
        "task_line_parsing": task_line_parsing,
        "jinja_analysis": jinja_analysis,
    }
    return PlatformExecutionBundle(
        prepared_policy=prepared_policy,
        platform_participants=participants,
    )


__all__ = [
    "ANSIBLE_PLUGIN_ENABLED_ENV_VAR",
    "ANSIBLE_KERNEL_PLUGIN_MANIFEST",
    "AnsibleBaselineKernelPlugin",
    "AnsibleFeatureDetectionPlugin",
    "AnsibleScanPipelinePlugin",
    "AnsibleVariableDiscoveryPlugin",
    "AnsibleYAMLParsingPolicyPlugin",
    "AnsibleJinjaAnalysisPolicyPlugin",
    "AnsibleTaskAnnotationPolicyPlugin",
    "build_ansible_execution_bundle",
    "is_ansible_plugin_enabled",
    "load_ansible_kernel_plugin",
]
