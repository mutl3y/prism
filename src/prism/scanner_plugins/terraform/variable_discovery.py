"""TerraformVariableDiscoveryPlugin — Terraform-specific variable discovery logic."""

from __future__ import annotations

from typing import ClassVar

from prism.scanner_data.contracts_request import DIContainer, ScanOptionsDict
from prism.scanner_data.contracts_variables import VariableRow
from prism.scanner_plugins.interfaces import VariableDiscoveryPlugin


class TerraformVariableDiscoveryPlugin:
    """Terraform-specific variable discovery plugin (fail-closed).

    Implements the VariableDiscoveryPlugin protocol with stateless,
    contract-valid behavior. Currently returns no discovered variables
    since Terraform variable scanning is not yet implemented.
    """

    PLUGIN_IS_STATELESS: ClassVar[bool] = True

    def __init__(self, di: object | None = None) -> None:
        self._di = di if isinstance(di, DIContainer) else None

    def discover(
        self,
        role_path: str,
        scan_options: ScanOptionsDict,
    ) -> tuple[VariableRow, ...]:
        """Discover Terraform module variables (fail-closed: returns empty).

        Args:
            role_path: Path to the Terraform module being scanned
            scan_options: Scan configuration options

        Returns:
            Empty tuple (fail-closed behavior: no variables discovered yet)
        """
        del role_path, scan_options
        return ()
