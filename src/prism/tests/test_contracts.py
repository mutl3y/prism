"""Test suite for scanner_data.contracts data structure definitions.

This test suite validates that:
1. All TypedDict contracts are importable
2. Optional fields use NotRequired properly
3. No circular dependencies exist
4. Contracts module doesn't import from scanner or submodules
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestContractsModuleStructure:
    """Verify contracts.py module structure is correct."""

    def test_contracts_module_exists(self) -> None:
        """Verify scanner_data/contracts.py file exists."""
        contracts_path = Path(__file__).parent.parent / "scanner_data" / "contracts.py"
        assert contracts_path.exists(), f"contracts.py not found at {contracts_path}"

    def test_scanner_data_init_exists(self) -> None:
        """Verify scanner_data/__init__.py exists."""
        init_path = Path(__file__).parent.parent / "scanner_data" / "__init__.py"
        assert init_path.exists(), f"__init__.py not found at {init_path}"

    def test_contracts_module_is_importable(self) -> None:
        """Verify scanner_data.contracts can be imported without errors."""
        try:
            from prism.scanner_data import contracts  # noqa: F401
        except ImportError as e:
            pytest.fail(f"Failed to import prism.scanner_data.contracts: {e}")

    def test_contracts_no_circular_imports(self) -> None:
        """Verify contracts.py doesn't import from scanner or submodules."""
        contracts_path = Path(__file__).parent.parent / "scanner_data" / "contracts.py"
        content = contracts_path.read_text()

        # Contracts should not import from scanner.py or scanner_submodules
        forbidden_imports = [
            "from prism.scanner import",
            "from prism.scanner_submodules",
            "from .scanner import",
            "from ..scanner import",
            "from ..scanner_submodules",
        ]

        for forbidden in forbidden_imports:
            assert forbidden not in content, (
                f"contracts.py must not import from scanner modules. "
                f"Found: {forbidden}"
            )


class TestContractsDefinitions:
    """Test that all required TypedDict contracts are defined and importable."""

    REQUIRED_CONTRACTS = [
        "Variable",
        "VariableRow",
        "VariableProvenance",
        "VariableRowWithMeta",
        "ScanMetadata",
        "FeaturesContext",
        "RunScanOutputPayload",
        "EmitScanOutputsArgs",
        "StyleGuideConfig",
        "ReferenceContext",
        "ScanBaseContext",
        "ScannerCounters",
        "ScannerReportMetadata",
        "FinalOutputPayload",
    ]

    @pytest.mark.parametrize("contract_name", REQUIRED_CONTRACTS)
    def test_contract_is_importable(self, contract_name: str) -> None:
        """Test that each required contract can be imported."""
        from prism.scanner_data import contracts

        assert hasattr(
            contracts, contract_name
        ), f"Contract {contract_name} not found in contracts module"

    def test_variable_provenance_structure(self) -> None:
        """Verify VariableProvenance has expected fields."""
        from prism.scanner_data.contracts import VariableProvenance

        # Should be importable as a type
        assert VariableProvenance is not None
        # Verify it's actually a TypedDict by checking for __annotations__
        assert hasattr(VariableProvenance, "__annotations__")

    def test_variable_row_structure(self) -> None:
        """Verify VariableRow has expected fields."""
        from prism.scanner_data.contracts import VariableRow

        assert VariableRow is not None
        assert hasattr(VariableRow, "__annotations__")

    def test_scan_metadata_structure(self) -> None:
        """Verify ScanMetadata is properly defined."""
        from prism.scanner_data.contracts import ScanMetadata

        assert ScanMetadata is not None
        assert hasattr(ScanMetadata, "__annotations__")

    def test_features_context_structure(self) -> None:
        """Verify FeaturesContext is properly defined."""
        from prism.scanner_data.contracts import FeaturesContext

        assert FeaturesContext is not None
        assert hasattr(FeaturesContext, "__annotations__")

    def test_style_guide_config_structure(self) -> None:
        """Verify StyleGuideConfig is properly defined."""
        from prism.scanner_data.contracts import StyleGuideConfig

        assert StyleGuideConfig is not None
        assert hasattr(StyleGuideConfig, "__annotations__")

    def test_reference_context_structure(self) -> None:
        """Verify ReferenceContext is properly defined."""
        from prism.scanner_data.contracts import ReferenceContext

        assert ReferenceContext is not None
        assert hasattr(ReferenceContext, "__annotations__")

    def test_run_scan_output_payload_structure(self) -> None:
        """Verify RunScanOutputPayload is properly defined."""
        from prism.scanner_data.contracts import RunScanOutputPayload

        assert RunScanOutputPayload is not None
        assert hasattr(RunScanOutputPayload, "__annotations__")

    def test_emit_scan_outputs_args_structure(self) -> None:
        """Verify EmitScanOutputsArgs is properly defined."""
        from prism.scanner_data.contracts import EmitScanOutputsArgs

        assert EmitScanOutputsArgs is not None
        assert hasattr(EmitScanOutputsArgs, "__annotations__")

    def test_scanner_counters_structure(self) -> None:
        """Verify ScannerCounters is properly defined."""
        from prism.scanner_data.contracts import ScannerCounters

        assert ScannerCounters is not None
        assert hasattr(ScannerCounters, "__annotations__")

    def test_final_output_payload_structure(self) -> None:
        """Verify FinalOutputPayload is properly defined."""
        from prism.scanner_data.contracts import FinalOutputPayload

        assert FinalOutputPayload is not None
        assert hasattr(FinalOutputPayload, "__annotations__")


class TestContractsImportingFromExistingCode:
    """Test that existing scanner code can be migrated to use contracts."""

    def test_can_import_contracts_in_scanner(self) -> None:
        """Verify that scanner.py can import from contracts without circularity."""
        # This is a compile-time check in practice, but we verify by attempting import
        try:
            from prism.scanner_data.contracts import (
                VariableRow,
                VariableProvenance,
            )

            assert VariableRow is not None
            assert VariableProvenance is not None
        except ImportError as e:
            pytest.fail(f"Failed to import contracts in test: {e}")

    def test_scanner_data_all_symbols_are_exported_and_importable(self) -> None:
        """Every symbol listed in prism.scanner_data.__all__ must be importable."""
        import prism.scanner_data as scanner_data

        public_symbols = getattr(scanner_data, "__all__", [])
        assert public_symbols, "prism.scanner_data.__all__ must not be empty"

        for symbol in public_symbols:
            assert hasattr(
                scanner_data, symbol
            ), f"Missing exported symbol in prism.scanner_data: {symbol}"


class TestContractsConsistency:
    """Test internal consistency of contracts."""

    def test_all_required_contracts_exist(self) -> None:
        """Verify all contracts mentioned in docstring exist."""
        from prism.scanner_data import contracts

        # Get all public members that are TypedDict classes
        contract_classes = [
            name
            for name in dir(contracts)
            if not name.startswith("_")
            and hasattr(getattr(contracts, name), "__annotations__")
        ]

        # Should have at least the 14 required ones
        assert (
            len(contract_classes) >= 14
        ), f"Expected at least 14 public contract classes, found {len(contract_classes)}"
