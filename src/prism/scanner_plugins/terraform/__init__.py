"""Terraform reserved target plugin ownership seam."""

from __future__ import annotations

from typing import Any, cast

PLUGIN_CONTRACT_VERSION = {"major": 1, "minor": 0}

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
    "TERRAFORM_RESERVED_TARGET_CLASSIFIER_ENTRY",
    "TERRAFORM_RESERVED_TARGET_PLUGIN_MANIFEST",
    "build_reserved_target_capability_response",
    "build_reserved_target_classifier_entry",
    "build_unsupported_scan_pipeline_outcome",
]
