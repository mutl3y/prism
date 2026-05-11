"""Kubernetes plugin package with error adapter support."""

from __future__ import annotations

import copy
import types
from pathlib import Path
from typing import Any, ClassVar, Collection, cast

from prism.scanner_plugins.kubernetes.error_adapter import (
    build_k8s_error_detail,
    classify_k8s_error,
)
from prism.scanner_plugins.kubernetes.error_codes import (
    K8S_CONFIG_MISSING,
    K8S_DEPLOYMENT_FAILED,
    K8S_ERROR_CATEGORY_MAP,
    K8S_ERROR_CODES,
    K8S_POD_FAILED,
    K8S_POD_NOT_FOUND,
    K8S_POD_PENDING,
    K8S_QUOTA_EXCEEDED,
    K8S_RBAC_DENIED,
    K8S_REPLICAS_NOT_READY,
    K8S_SECRET_NOT_FOUND,
    K8S_SERVICE_ENDPOINT_EMPTY,
    K8S_SERVICE_NOT_FOUND,
    K8S_TRANSIENT_ERRORS,
)
from prism.scanner_plugins.kubernetes.readme_renderer import (
    KubernetesReadmeRendererPlugin,
)
from prism.scanner_plugins.kubernetes.feature_detection import (
    KubernetesFeatureDetectionPlugin,
    collect_manifest_inventory,
)
from prism.scanner_plugins.kubernetes.variable_discovery import (
    KubernetesVariableDiscoveryPlugin,
)
from prism.scanner_data.contracts_request import PreparedPolicyBundle
from prism.scanner_data.contracts_request import ScanMetadata, ScanOptionsDict
from prism.scanner_data.contracts_request import TaskAnnotation, TaskMapping
from prism.scanner_data.contracts_request import YamlParseFailure
from prism.scanner_plugins.interfaces import (
    PlatformExecutionBundle,
    PlatformParticipants,
    ScanPipelinePayload,
    ScanPipelinePreflightContext,
)

PLUGIN_CONTRACT_VERSION: types.MappingProxyType[str, int] = types.MappingProxyType(
    {"major": 1, "minor": 0}
)

_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE = (
    "kubernetes execution bundle is not executable yet; "
    "bootstrap-only prepared-policy stubs fail closed"
)

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
            merged[key] = _merge_preserving_existing(existing_value, value)
    return merged


class _KubernetesTaskLineParsingPolicyStub:
    TASK_INCLUDE_KEYS: Collection[str] = frozenset()
    ROLE_INCLUDE_KEYS: Collection[str] = frozenset()
    INCLUDE_VARS_KEYS: Collection[str] = frozenset()
    SET_FACT_KEYS: Collection[str] = frozenset()
    TASK_BLOCK_KEYS: Collection[str] = frozenset()
    TASK_META_KEYS: Collection[str] = frozenset()

    def detect_task_module(self, task: TaskMapping) -> str | None:
        del task
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)


class _KubernetesJinjaAnalysisPolicyStub:
    def collect_undeclared_jinja_variables(self, text: str) -> set[str]:
        del text
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)


class _KubernetesTaskTraversalPolicyStub:
    def iter_task_mappings(self, data: object) -> list[TaskMapping]:
        del data
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def iter_task_include_targets(self, data: object) -> list[str]:
        del data
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def iter_task_include_edges(self, data: object) -> list[dict[str, str]]:
        del data
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def expand_include_target_candidates(
        self,
        task: TaskMapping,
        include_target: str,
    ) -> list[str]:
        del task, include_target
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def iter_role_include_targets(self, task: TaskMapping) -> list[str]:
        del task
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def iter_dynamic_role_include_targets(self, task: TaskMapping) -> list[str]:
        del task
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def collect_unconstrained_dynamic_task_includes(
        self,
        *,
        role_root: object,
        task_files: list[object],
        load_yaml_file: object,
    ) -> list[dict[str, str]]:
        del role_root, task_files, load_yaml_file
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def collect_unconstrained_dynamic_role_includes(
        self,
        *,
        role_root: object,
        task_files: list[object],
        load_yaml_file: object,
    ) -> list[dict[str, str]]:
        del role_root, task_files, load_yaml_file
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)


class _KubernetesYamlParsingPolicyStub:
    def load_yaml_file(self, path: str | Path) -> object:
        del path
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def parse_yaml_candidate(
        self,
        candidate: str | Path,
        role_root: str | Path,
    ) -> YamlParseFailure | None:
        del candidate, role_root
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)


class _KubernetesVariableExtractorPolicyStub:
    def collect_include_vars_files(
        self,
        *,
        role_path: str,
        exclude_paths: list[str] | None,
        collect_task_files: object,
        load_yaml_file: object,
    ) -> list[object]:
        del role_path, exclude_paths, collect_task_files, load_yaml_file
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)


class _KubernetesTaskAnnotationPolicyStub:
    def split_task_annotation_label(self, text: str) -> tuple[str, str]:
        del text
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def split_task_target_payload(self, text: str) -> tuple[str, str]:
        del text
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def annotation_payload_looks_yaml(self, payload: str) -> bool:
        del payload
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def normalize_marker_prefix(self, marker_prefix: str | None) -> str:
        del marker_prefix
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def get_marker_line_re(self, marker_prefix: str = "prism") -> object:
        del marker_prefix
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def extract_task_annotations_for_file(
        self,
        lines: list[str],
        marker_prefix: str = "prism",
        include_task_index: bool = False,
    ) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
        del lines, marker_prefix, include_task_index
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)

    def task_anchor(self, file_path: str, task_name: str, index: int) -> str:
        del file_path, task_name, index
        raise ValueError(_FAIL_CLOSED_KUBERNETES_BUNDLE_MESSAGE)


class KubernetesScanPipelinePlugin:
    """Bootstrap scan-pipeline plugin for the Kubernetes support lane."""

    PRISM_PLUGIN_API_VERSION: ClassVar[tuple[int, int]] = (1, 0)
    PLUGIN_IS_STATELESS: ClassVar[bool] = True

    def process_scan_pipeline(
        self,
        scan_options: ScanOptionsDict,
        scan_context: ScanMetadata,
    ) -> ScanPipelinePreflightContext:
        context = dict(scan_context)
        context.setdefault("plugin_platform", "kubernetes")
        context.setdefault("plugin_name", "kubernetes")
        context.setdefault("plugin_support_state", "bootstrap")
        context["plugin_enabled"] = True
        context["kubernetes_plugin_enabled"] = True
        if "role_path" in scan_options and "role_path" not in context:
            context["role_path"] = scan_options["role_path"]

        inventory = collect_manifest_inventory(str(scan_options.get("role_path", "")))

        if "resource_kinds" not in context:
            context["resource_kinds"] = list(inventory.resource_kinds)
        if "operational_notes" not in context:
            context["operational_notes"] = list(inventory.operational_notes)

        return cast(ScanPipelinePreflightContext, context)

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

        plugin_output: ScanPipelinePreflightContext
        if isinstance(preflight_context, dict):
            plugin_output = cast(ScanPipelinePreflightContext, dict(preflight_context))
        else:
            plugin_output = self.process_scan_pipeline(
                scan_options=copy.deepcopy(scan_options),
                scan_context=cast(ScanMetadata, copy.deepcopy(base_metadata)),
            )

        payload["metadata"] = _merge_preserving_existing(
            base_metadata,
            cast(dict[str, Any], plugin_output),
        )
        return payload


def build_kubernetes_execution_bundle(
    scan_options: ScanOptionsDict | None = None,
) -> PlatformExecutionBundle:
    task_line_parsing = _KubernetesTaskLineParsingPolicyStub()
    jinja_analysis = _KubernetesJinjaAnalysisPolicyStub()
    task_traversal = _KubernetesTaskTraversalPolicyStub()
    yaml_parsing = _KubernetesYamlParsingPolicyStub()
    variable_extractor = _KubernetesVariableExtractorPolicyStub()
    task_annotation_parsing = _KubernetesTaskAnnotationPolicyStub()
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
        "comment_doc_marker_prefix": (
            str(scan_options.get("comment_doc_marker_prefix"))
            if isinstance(scan_options, dict)
            and isinstance(scan_options.get("comment_doc_marker_prefix"), str)
            and scan_options.get("comment_doc_marker_prefix")
            else "prism"
        ),
        "ignore_unresolved_internal_underscore_references": (
            bool(scan_options.get("ignore_unresolved_internal_underscore_references"))
            if isinstance(scan_options, dict)
            else False
        ),
    }
    return PlatformExecutionBundle(
        prepared_policy=prepared_policy,
        platform_participants=participants,
    )


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
    "KubernetesReadmeRendererPlugin",
    "KubernetesScanPipelinePlugin",
    "KubernetesFeatureDetectionPlugin",
    "KubernetesVariableDiscoveryPlugin",
    "KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY",
    "KUBERNETES_RESERVED_TARGET_PLUGIN_MANIFEST",
    "build_kubernetes_execution_bundle",
    "build_reserved_target_capability_response",
    "build_reserved_target_classifier_entry",
    "build_unsupported_scan_pipeline_outcome",
    # Error adapter exports
    "build_k8s_error_detail",
    "classify_k8s_error",
    # Error code exports
    "K8S_CONFIG_MISSING",
    "K8S_DEPLOYMENT_FAILED",
    "K8S_ERROR_CATEGORY_MAP",
    "K8S_ERROR_CODES",
    "K8S_POD_FAILED",
    "K8S_POD_NOT_FOUND",
    "K8S_POD_PENDING",
    "K8S_QUOTA_EXCEEDED",
    "K8S_RBAC_DENIED",
    "K8S_REPLICAS_NOT_READY",
    "K8S_SECRET_NOT_FOUND",
    "K8S_SERVICE_ENDPOINT_EMPTY",
    "K8S_SERVICE_NOT_FOUND",
    "K8S_TRANSIENT_ERRORS",
]
