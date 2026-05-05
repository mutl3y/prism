"""Canonical ansible scanner plugin package for the fsrc lane."""

from __future__ import annotations

import copy
from typing import Any, ClassVar, cast

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
from prism.scanner_plugins.ansible.extract_policies import (
    AnsibleTaskTraversalPolicyPlugin,
)
from prism.scanner_plugins.ansible.extract_policies import (
    AnsibleVariableExtractorPolicyPlugin,
)
from prism.scanner_plugins.ansible.feature_detection import (
    AnsibleFeatureDetectionPlugin,
)
from prism.scanner_plugins.ansible.readme_renderer import AnsibleReadmeRendererPlugin
from prism.scanner_plugins.ansible.variable_discovery import (
    AnsibleVariableDiscoveryPlugin,
)
from prism.scanner_plugins.parsers.jinja import DefaultJinjaAnalysisPolicyPlugin
from prism.scanner_plugins.parsers.yaml import DefaultYAMLParsingPolicyPlugin
from prism.scanner_data.contracts_request import PreparedPolicyBundle
from prism.scanner_data.contracts_request import ScanMetadata, ScanOptionsDict
from prism.scanner_plugins.interfaces import (
    PlatformExecutionBundle,
    PlatformParticipants,
    ScanPipelinePayload,
    ScanPipelinePreflightContext,
)


class AnsibleScanPipelinePlugin:
    """Scan-pipeline plugin that annotates context with ansible kernel capability."""

    PLUGIN_IS_STATELESS: ClassVar[bool] = True

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
        scan_options: ScanOptionsDict,
        scan_context: ScanMetadata,
    ) -> ScanPipelinePreflightContext:
        context = cast(ScanPipelinePreflightContext, dict(scan_context))
        context.setdefault("plugin_platform", "ansible")
        context.setdefault("plugin_name", "ansible")
        # The default ansible routing path remains available without env gating.
        ansible_plugin_enabled = bool(is_ansible_plugin_enabled())
        context["plugin_enabled"] = True
        context["ansible_plugin_enabled"] = ansible_plugin_enabled
        if "role_path" in scan_options and "role_path" not in context:
            context["role_path"] = scan_options.get("role_path")
        return context

    def orchestrate_scan_payload(
        self,
        *,
        payload: ScanPipelinePayload,
        scan_options: ScanOptionsDict,
        strict_mode: bool,
        preflight_context: ScanMetadata | None = None,
    ) -> ScanPipelinePayload:
        del strict_mode
        metadata = payload.get("metadata")
        base_metadata = copy.deepcopy(metadata) if isinstance(metadata, dict) else {}

        if isinstance(preflight_context, dict):
            plugin_output: Any = dict(preflight_context)
        else:
            plugin_output = self.process_scan_pipeline(
                scan_options=copy.deepcopy(scan_options),
                scan_context=cast(ScanMetadata, copy.deepcopy(base_metadata)),
            )

        if not isinstance(plugin_output, dict):
            return payload

        payload["metadata"] = AnsibleScanPipelinePlugin._merge_preserving_existing(
            base_metadata,
            plugin_output,
        )
        return payload


def build_ansible_execution_bundle(
    scan_options: ScanOptionsDict | None = None,
) -> PlatformExecutionBundle:
    """Build the Ansible-owned platform execution bundle from a scan request.

    Produces a PlatformExecutionBundle carrying Ansible-native policy
    participant instances so scanner_core ingress can receive them through
    the generic contract without manufacturing Ansible defaults internally.
    """
    del scan_options
    task_line_parsing = AnsibleTaskLineParsingPolicyPlugin()
    jinja_analysis = DefaultJinjaAnalysisPolicyPlugin()
    task_traversal = AnsibleTaskTraversalPolicyPlugin()
    yaml_parsing = DefaultYAMLParsingPolicyPlugin()
    variable_extractor = AnsibleVariableExtractorPolicyPlugin()
    task_annotation_parsing = AnsibleTaskAnnotationPolicyPlugin()
    participants: PlatformParticipants = {
        "task_line_parsing": task_line_parsing,
        "jinja_analysis": jinja_analysis,
    }
    prepared_policy: PreparedPolicyBundle = {
        "task_line_parsing": task_line_parsing,
        "jinja_analysis": jinja_analysis,
        "task_traversal": task_traversal,
        "yaml_parsing": yaml_parsing,
        "variable_extractor": variable_extractor,
        "task_annotation_parsing": task_annotation_parsing,
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
    "AnsibleReadmeRendererPlugin",
    "AnsibleScanPipelinePlugin",
    "AnsibleVariableDiscoveryPlugin",
    "AnsibleTaskAnnotationPolicyPlugin",
    "build_ansible_execution_bundle",
    "is_ansible_plugin_enabled",
    "load_ansible_kernel_plugin",
]
