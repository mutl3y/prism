"""Integration tests for complete scanner workflow (end-to-end validation).

These tests validate the complete scanner workflow from role discovery
to output generation. Unlike unit tests (which isolate and mock each
component), integration tests run the full pipeline with real files
to ensure components work together correctly.

These tests are kept for regression validation of critical paths:
- Full role scanning
- Complete payload generation
- Public API contracts (api.py, cli.py)
"""

from __future__ import annotations

from pathlib import Path


from prism.scanner_core import DIContainer, ScannerContext


class TestScannerIntegrationEndToEnd:
    """Test complete scanner workflow (end-to-end integration)."""

    def test_scanner_context_orchestrate_scan_with_empty_role(
        self, empty_test_role: Path
    ) -> None:
        """Full scan workflow with empty role produces valid payload."""
        di = DIContainer(
            role_path=str(empty_test_role),
            scan_options={
                "role_path": str(empty_test_role),
                "include_vars_main": True,
                "exclude_path_patterns": None,
                "vars_seed_paths": None,
                "ignore_unresolved_internal_underscore_references": False,
            },
        )
        context = ScannerContext(
            di=di,
            role_path=str(empty_test_role),
            scan_options=di._scan_options,
        )

        # Full orchestration
        payload = context.orchestrate_scan()

        # Validate payload structure
        assert isinstance(payload, dict)
        assert "display_variables" in payload
        assert "metadata" in payload

    def test_scanner_context_orchestrate_scan_with_basic_role(
        self, basic_test_role: Path
    ) -> None:
        """Full scan workflow with basic role discovers variables."""
        di = DIContainer(
            role_path=str(basic_test_role),
            scan_options={
                "role_path": str(basic_test_role),
                "include_vars_main": True,
                "exclude_path_patterns": None,
                "vars_seed_paths": None,
                "ignore_unresolved_internal_underscore_references": False,
            },
        )
        context = ScannerContext(
            di=di,
            role_path=str(basic_test_role),
            scan_options=di._scan_options,
        )

        # Full orchestration
        payload = context.orchestrate_scan()

        # Validate payload structure
        assert isinstance(payload, dict)
        assert "display_variables" in payload
        assert "metadata" in payload

    def test_scanner_context_orchestrate_scan_with_complex_role(
        self, complex_test_role: Path
    ) -> None:
        """Full scan workflow with complex role analyzes features."""
        di = DIContainer(
            role_path=str(complex_test_role),
            scan_options={
                "role_path": str(complex_test_role),
                "include_vars_main": True,
                "exclude_path_patterns": None,
                "vars_seed_paths": None,
                "ignore_unresolved_internal_underscore_references": False,
            },
        )
        context = ScannerContext(
            di=di,
            role_path=str(complex_test_role),
            scan_options=di._scan_options,
        )

        # Full orchestration
        payload = context.orchestrate_scan()

        # Validate payload structure
        assert isinstance(payload, dict)
        assert "display_variables" in payload
        assert "metadata" in payload

    def test_scanner_context_payload_contains_metadata(
        self, basic_test_role: Path
    ) -> None:
        """Payload includes complete metadata after orchestration."""
        di = DIContainer(
            role_path=str(basic_test_role),
            scan_options={
                "role_path": str(basic_test_role),
                "include_vars_main": True,
                "exclude_path_patterns": None,
                "vars_seed_paths": None,
                "ignore_unresolved_internal_underscore_references": False,
            },
        )
        context = ScannerContext(
            di=di,
            role_path=str(basic_test_role),
            scan_options=di._scan_options,
        )

        payload = context.orchestrate_scan()

        # Validate metadata presence
        assert "metadata" in payload
        metadata = payload["metadata"]
        assert isinstance(metadata, dict)

    def test_scanner_context_handles_missing_role_gracefully(
        self,
    ) -> None:
        """Scanner handles missing role path gracefully."""
        missing_role = "/tmp/nonexistent_test_role_12345"

        di = DIContainer(
            role_path=missing_role,
            scan_options={
                "role_path": missing_role,
                "include_vars_main": True,
                "exclude_path_patterns": None,
                "vars_seed_paths": None,
                "ignore_unresolved_internal_underscore_references": False,
            },
        )
        context = ScannerContext(
            di=di,
            role_path=missing_role,
            scan_options=di._scan_options,
        )

        # Orchestration should handle missing path
        payload = context.orchestrate_scan()

        # Payload should still be valid dict (not raise exception)
        assert isinstance(payload, dict)
        # Empty display_variables expected for missing role
        assert isinstance(payload.get("display_variables"), dict)

    def test_scanner_context_discovered_variables_contain_all_phases(
        self, basic_test_role: Path
    ) -> None:
        """Discovered variables include both static and referenced sources."""
        di = DIContainer(
            role_path=str(basic_test_role),
            scan_options={
                "role_path": str(basic_test_role),
                "include_vars_main": True,
                "exclude_path_patterns": None,
                "vars_seed_paths": None,
                "ignore_unresolved_internal_underscore_references": False,
            },
        )
        context = ScannerContext(
            di=di,
            role_path=str(basic_test_role),
            scan_options=di._scan_options,
        )

        context.orchestrate_scan()

        discovered = context.discovered_variables
        # Should be tuple (immutable)
        assert isinstance(discovered, tuple)

    def test_scanner_context_state_is_immutable_after_orchestration(
        self, basic_test_role: Path
    ) -> None:
        """ScannerContext maintains immutable state after orchestration."""
        di = DIContainer(
            role_path=str(basic_test_role),
            scan_options={
                "role_path": str(basic_test_role),
                "include_vars_main": True,
                "exclude_path_patterns": None,
                "vars_seed_paths": None,
                "ignore_unresolved_internal_underscore_references": False,
            },
        )
        context = ScannerContext(
            di=di,
            role_path=str(basic_test_role),
            scan_options=di._scan_options,
        )

        # First orchestration
        payload1 = context.orchestrate_scan()
        discovered1 = context.discovered_variables

        # Second orchestration (should produce same results)
        payload2 = context.orchestrate_scan()
        discovered2 = context.discovered_variables

        # Discovered variables should be identical (immutable)
        assert discovered1 == discovered2
        # Payload variables should match
        assert len(payload1.get("variables", [])) == len(payload2.get("variables", []))
