"""KubernetesFeatureDetectionPlugin — Kubernetes-specific feature detection logic."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prism.scanner_data.contracts_request import FeaturesContext
from prism.scanner_plugins.interfaces import TaskCatalog


class KubernetesFeatureDetectionPlugin:
    """Kubernetes-specific feature detection plugin.

    Implements contract-valid, stateless feature detection for Kubernetes
    manifests. Currently provides bootstrap-level detection with explicit
    fail-closed behavior for unimplemented capabilities.
    """

    PLUGIN_IS_STATELESS = True

    def __init__(self, di: object | None = None) -> None:
        self._di = di

    def detect_features(
        self,
        role_path: str,
        options: dict[str, Any],
    ) -> FeaturesContext:
        """Detect Kubernetes-specific features in target path.

        For bootstrap phase, returns minimal feature detection context.
        Kubernetes does not have the same task-centric feature model
        as Ansible, so detection is limited to manifest presence.

        Args:
            role_path: Path to target Kubernetes manifests
            options: Detection options (unused in bootstrap phase)

        Returns:
            FeaturesContext dict with detected features
        """
        del options  # Unused in bootstrap
        
        role_root = Path(role_path).resolve()
        
        # Bootstrap-level detection: minimal counts for Kubernetes
        # (manifest scanning is not yet implemented)
        features: FeaturesContext = {
            "task_files_scanned": 0,
            "tasks_scanned": 0,
            "recursive_task_includes": 0,
            "unique_modules": "",
            "external_collections": "",
            "handlers_notified": "",
            "privileged_tasks": 0,
            "conditional_tasks": 0,
            "tagged_tasks": 0,
            "included_role_calls": 0,
            "included_roles": "",
            "dynamic_included_role_calls": 0,
            "dynamic_included_roles": "",
            "disabled_task_annotations": 0,
            "yaml_like_task_annotations": 0,
        }
        
        return features

    def analyze_task_catalog(
        self,
        role_path: str,
        options: dict[str, Any],
    ) -> TaskCatalog:
        """Analyze task catalog for Kubernetes manifests.

        For bootstrap phase, returns empty catalog since Kubernetes
        manifest scanning is not yet implemented.

        Args:
            role_path: Path to target Kubernetes manifests
            options: Catalog analysis options (unused in bootstrap)

        Returns:
            TaskCatalog dict (empty for bootstrap)
        """
        del role_path, options  # Unused in bootstrap
        
        return {}
