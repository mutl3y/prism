"""TerraformFeatureDetectionPlugin — Terraform-specific feature detection logic."""

from __future__ import annotations

from typing import Any, ClassVar

from prism.scanner_data.contracts_request import DIContainer, FeaturesContext, ScanOptionsDict
from prism.scanner_plugins.interfaces import FeatureDetectionPlugin


class TerraformFeatureDetectionPlugin:
    """Terraform-specific feature detection plugin (fail-closed).

    Implements the FeatureDetectionPlugin protocol with stateless,
    contract-valid behavior. Currently returns zero-valued features
    since Terraform resource scanning is not yet implemented.
    """

    PLUGIN_IS_STATELESS: ClassVar[bool] = True

    def __init__(self, di: object | None = None) -> None:
        self._di = di if isinstance(di, DIContainer) else None

    def detect_features(
        self,
        role_path: str,
        scan_options: ScanOptionsDict,
    ) -> FeaturesContext:
        """Detect Terraform module features (fail-closed: returns zeros).

        Args:
            role_path: Path to the Terraform module being scanned
            scan_options: Scan configuration options

        Returns:
            FeaturesContext with all counters set to zero (fail-closed behavior)
        """
        del role_path, scan_options
        return {
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
