"""TerraformFeatureDetectionPlugin — Terraform-specific feature detection logic."""

from __future__ import annotations

from typing import ClassVar

from prism.scanner_data.contracts_request import DIContainer, FeaturesContext, ScanOptionsDict
from prism.scanner_plugins.terraform.execution_bundle import (
    extract_terraform_module_metadata,
)


class TerraformFeatureDetectionPlugin:
    """Terraform-specific feature detection plugin.

    Implements the FeatureDetectionPlugin protocol with stateless,
    contract-valid behavior. Uses deterministic Terraform metadata
    extraction under role_path without claiming full parser support.
    """

    PLUGIN_IS_STATELESS: ClassVar[bool] = True

    def __init__(self, di: object | None = None) -> None:
        self._di = di if isinstance(di, DIContainer) else None

    def detect_features(
        self,
        role_path: str,
        scan_options: ScanOptionsDict,
    ) -> FeaturesContext:
        """Detect Terraform module features from deterministic Terraform signals.

        Args:
            role_path: Path to the Terraform module being scanned
            scan_options: Scan configuration options

        Returns:
            FeaturesContext populated from deterministic Terraform metadata when
            available, otherwise fail-closed zeros.
        """
        del scan_options
        metadata = extract_terraform_module_metadata(role_path)
        managed_resources = metadata.get("managed_resources")
        data_sources = metadata.get("data_sources")
        providers = metadata.get("providers")
        module_calls = metadata.get("module_calls")

        resource_names = managed_resources if isinstance(managed_resources, list) else []
        data_source_names = data_sources if isinstance(data_sources, list) else []
        provider_names = providers if isinstance(providers, list) else []
        included_modules = module_calls if isinstance(module_calls, list) else []
        terraform_files_scanned = metadata.get("terraform_files_scanned", 0)
        files_scanned_count = (
            terraform_files_scanned if isinstance(terraform_files_scanned, int) else 0
        )

        return {
            "task_files_scanned": files_scanned_count,
            "tasks_scanned": len(resource_names) + len(data_source_names),
            "recursive_task_includes": len(included_modules),
            "unique_modules": ", ".join(resource_names) if resource_names else "none",
            "external_collections": ", ".join(provider_names) if provider_names else "none",
            "handlers_notified": "none",
            "privileged_tasks": 0,
            "conditional_tasks": 0,
            "tagged_tasks": 0,
            "included_role_calls": len(included_modules),
            "included_roles": ", ".join(included_modules) if included_modules else "none",
            "dynamic_included_role_calls": 0,
            "dynamic_included_roles": "none",
            "disabled_task_annotations": 0,
            "yaml_like_task_annotations": 0,
        }
