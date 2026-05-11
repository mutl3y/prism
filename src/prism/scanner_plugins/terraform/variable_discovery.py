"""TerraformVariableDiscoveryPlugin — Terraform-specific variable discovery logic."""

from __future__ import annotations

from typing import ClassVar

from prism.scanner_data.contracts_request import DIContainer, ScanOptionsDict
from prism.scanner_data.contracts_variables import VariableRow
from prism.scanner_plugins.terraform.execution_bundle import (
    extract_terraform_variable_rows,
)


class TerraformVariableDiscoveryPlugin:
    """Terraform-specific variable discovery plugin.

    Implements the VariableDiscoveryPlugin protocol with stateless,
    contract-valid behavior. Uses deterministic variable block discovery
    without claiming full Terraform evaluation support.
    """

    PLUGIN_IS_STATELESS: ClassVar[bool] = True

    def __init__(self, di: object | None = None) -> None:
        self._di = di if isinstance(di, DIContainer) else None

    def discover(
        self,
        role_path: str,
        scan_options: ScanOptionsDict,
    ) -> tuple[VariableRow, ...]:
        """Discover Terraform module variables from root-level variable blocks.

        Args:
            role_path: Path to the Terraform module being scanned
            scan_options: Scan configuration options

        Returns:
            Deterministic VariableRow entries for root-level variable blocks,
            or an empty tuple when no Terraform files are available.
        """
        del scan_options
        return extract_terraform_variable_rows(role_path)
