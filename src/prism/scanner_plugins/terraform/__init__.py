"""Terraform plugin package with kickoff execution-slice exports."""

from __future__ import annotations

import copy
import types
from typing import Any, ClassVar, cast

from prism.scanner_plugins.terraform.error_adapter import (
    build_terraform_error_detail,
    classify_terraform_error,
)
from prism.scanner_plugins.terraform.error_codes import (
    TF_APPLY_FAILED,
    TF_BACKEND_FAILED,
    TF_CREDENTIAL_FAILED,
    TF_ERROR_CATEGORY_MAP,
    TF_ERROR_CODES,
    TF_LOCK_FAILED,
    TF_MODULE_NOT_FOUND,
    TF_PLAN_FAILED,
    TF_RESOURCE_FAILED,
    TF_STATE_CORRUPTED,
    TF_TRANSIENT_ERRORS,
    TF_VALIDATION_FAILED,
    TF_VERSION_FAILED,
)
from prism.scanner_data.contracts_request import PreparedPolicyBundle
from prism.scanner_data.contracts_request import ScanMetadata, ScanOptionsDict
from prism.scanner_plugins.interfaces import (
    PlatformExecutionBundle,
    PlatformParticipants,
    ScanPipelinePayload,
    ScanPipelinePreflightContext,
)
from prism.scanner_plugins.terraform.execution_bundle import (
    build_fail_closed_participants,
    extract_terraform_module_metadata,
)
from prism.scanner_plugins.terraform.feature_detection import (
    TerraformFeatureDetectionPlugin,
)
from prism.scanner_plugins.terraform.variable_discovery import (
    TerraformVariableDiscoveryPlugin,
)
from prism.scanner_plugins.terraform.readme_renderer import (
    TerraformReadmeRendererPlugin,
)

PLUGIN_CONTRACT_VERSION: types.MappingProxyType[str, int] = types.MappingProxyType(
    {"major": 1, "minor": 0}
)

STUBBED_TARGET_CAPABILITY_ERROR_CODE = "target_capability_stubbed"

TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY: dict[str, object] = {
    "target_type": "terraform_module",
    "plugin_id": "prism.terraform.v1",
    "support_state": "stubbed",
    "matchers": [{"kind": "file_presence", "pattern": "main.tf"}],
}

TERRAFORM_RESERVED_TARGET_PLUGIN_MANIFEST: dict[str, object] = {
    "plugin_id": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["plugin_id"],
    "target_type": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["target_type"],
    "support_state": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["support_state"],
    "contract_version": dict(PLUGIN_CONTRACT_VERSION),
}


class TerraformScanPipelinePlugin:
    """Minimal Terraform scan-pipeline plugin for the first executable slice."""

    PLUGIN_IS_STATELESS: ClassVar[bool] = True

    def process_scan_pipeline(
        self,
        scan_options: ScanOptionsDict,
        scan_context: ScanMetadata,
    ) -> ScanPipelinePreflightContext:
        context = cast(
            ScanPipelinePreflightContext,
            {
                key: value
                for key, value in copy.copy(scan_context).items()
                if key
                in {"plugin_name", "plugin_platform", "plugin_enabled", "role_path"}
            },
        )
        context.setdefault("plugin_platform", "terraform")
        context.setdefault("plugin_name", "terraform")
        context["plugin_enabled"] = True
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
        merged_metadata = copy.copy(metadata) if isinstance(metadata, dict) else {}
        if isinstance(preflight_context, dict):
            merged_metadata.update(preflight_context)
        else:
            merged_metadata.update(
                self.process_scan_pipeline(
                    scan_options=scan_options,
                    scan_context=cast(ScanMetadata, merged_metadata),
                )
            )
        role_path = scan_options.get("role_path")
        if isinstance(role_path, str) and role_path:
            merged_metadata.update(extract_terraform_module_metadata(role_path))
        payload["metadata"] = merged_metadata
        return payload


def build_terraform_execution_bundle(
    scan_options: ScanOptionsDict | None = None,
) -> PlatformExecutionBundle:
    del scan_options
    participants_map = build_fail_closed_participants()
    participants: PlatformParticipants = {
        "task_line_parsing": participants_map["task_line_parsing"],
        "jinja_analysis": participants_map["jinja_analysis"],
    }
    prepared_policy: PreparedPolicyBundle = {
        "task_line_parsing": participants_map["task_line_parsing"],
        "jinja_analysis": participants_map["jinja_analysis"],
        "task_traversal": participants_map["task_traversal"],
        "yaml_parsing": participants_map["yaml_parsing"],
        "variable_extractor": participants_map["variable_extractor"],
        "task_annotation_parsing": participants_map["task_annotation_parsing"],
    }
    return PlatformExecutionBundle(
        prepared_policy=prepared_policy,
        platform_participants=participants,
    )


def build_reserved_target_classifier_entry() -> dict[str, object]:
    return {
        "target_type": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["target_type"],
        "plugin_id": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["plugin_id"],
        "support_state": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["support_state"],
        "matchers": list(
            cast(list[Any], TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["matchers"])
        ),
    }


def build_reserved_target_capability_response() -> dict[str, object]:
    return {
        "target_type": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["target_type"],
        "support_state": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["support_state"],
        "degraded_success": False,
        "summary": "Terraform support is reserved but not implemented.",
        "guidance": (
            "The reserved Terraform package exposes capability-only metadata; "
            "scanning is not implemented yet."
        ),
        "plugin_id": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["plugin_id"],
        "error_code": STUBBED_TARGET_CAPABILITY_ERROR_CODE,
    }


def build_unsupported_scan_pipeline_outcome() -> dict[str, object]:
    return {
        "target_type": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["target_type"],
        "support_state": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["support_state"],
        "outcome": "PLATFORM_NOT_SUPPORTED",
        "supported": False,
        "summary": "Terraform support is reserved but not implemented.",
        "guidance": (
            "The reserved Terraform package exposes capability-only metadata; "
            "scanning is not implemented yet."
        ),
        "plugin_id": TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY["plugin_id"],
        "error_code": STUBBED_TARGET_CAPABILITY_ERROR_CODE,
    }


__all__ = [
    "TerraformFeatureDetectionPlugin",
    "TerraformReadmeRendererPlugin",
    "TerraformScanPipelinePlugin",
    "TerraformVariableDiscoveryPlugin",
    "TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY",
    "TERRAFORM_RESERVED_TARGET_PLUGIN_MANIFEST",
    "build_terraform_execution_bundle",
    "build_reserved_target_capability_response",
    "build_reserved_target_classifier_entry",
    "build_unsupported_scan_pipeline_outcome",
    # Error adapter exports
    "build_terraform_error_detail",
    "classify_terraform_error",
    "TF_APPLY_FAILED",
    "TF_BACKEND_FAILED",
    "TF_CREDENTIAL_FAILED",
    "TF_ERROR_CATEGORY_MAP",
    "TF_ERROR_CODES",
    "TF_LOCK_FAILED",
    "TF_MODULE_NOT_FOUND",
    "TF_PLAN_FAILED",
    "TF_RESOURCE_FAILED",
    "TF_STATE_CORRUPTED",
    "TF_TRANSIENT_ERRORS",
    "TF_VALIDATION_FAILED",
    "TF_VERSION_FAILED",
]
