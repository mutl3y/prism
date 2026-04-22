"""Kubernetes reserved target plugin ownership seam."""

from __future__ import annotations

from typing import Any, cast

PLUGIN_CONTRACT_VERSION = {"major": 1, "minor": 0}

UNSUPPORTED_TARGET_CAPABILITY_ERROR_CODE = "target_capability_unsupported"

KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY: dict[str, object] = {
    "target_type": "kubernetes_manifest",
    "plugin_id": "prism.kubernetes.v1",
    "support_state": "unsupported",
    "matchers": [{"kind": "file_name", "pattern": "kustomization.yaml"}],
}

KUBERNETES_RESERVED_TARGET_PLUGIN_MANIFEST: dict[str, object] = {
    "plugin_id": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["plugin_id"],
    "target_type": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["target_type"],
    "support_state": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["support_state"],
    "contract_version": dict(PLUGIN_CONTRACT_VERSION),
}


def build_reserved_target_classifier_entry() -> dict[str, object]:
    return {
        "target_type": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["target_type"],
        "plugin_id": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["plugin_id"],
        "support_state": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["support_state"],
        "matchers": list(
            cast(list[Any], KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["matchers"])
        ),
    }


def build_reserved_target_capability_response() -> dict[str, object]:
    return {
        "target_type": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["target_type"],
        "support_state": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["support_state"],
        "degraded_success": False,
        "summary": "Kubernetes scanning is not available.",
        "guidance": (
            "The reserved Kubernetes package can classify manifests, but it "
            "does not provide scan execution yet."
        ),
        "plugin_id": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["plugin_id"],
        "error_code": UNSUPPORTED_TARGET_CAPABILITY_ERROR_CODE,
    }


def build_unsupported_scan_pipeline_outcome() -> dict[str, object]:
    return {
        "target_type": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["target_type"],
        "support_state": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["support_state"],
        "outcome": "PLATFORM_NOT_SUPPORTED",
        "supported": False,
        "summary": "Kubernetes scanning is not available.",
        "guidance": (
            "The reserved Kubernetes package can classify manifests, but it "
            "does not provide scan execution yet."
        ),
        "plugin_id": KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["plugin_id"],
        "error_code": UNSUPPORTED_TARGET_CAPABILITY_ERROR_CODE,
    }


__all__ = [
    "KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY",
    "KUBERNETES_RESERVED_TARGET_PLUGIN_MANIFEST",
    "build_reserved_target_capability_response",
    "build_reserved_target_classifier_entry",
    "build_unsupported_scan_pipeline_outcome",
]
