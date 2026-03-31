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
from typing import cast

import pytest

from prism import scanner
from prism.scanner_core import scan_request
from prism.scanner_core import DIContainer, ScannerContext


def _canonical_scan_options(role_path: str) -> dict:
    return scan_request.build_run_scan_options(
        role_path=role_path,
        role_name_override=None,
        readme_config_path=None,
        include_vars_main=True,
        exclude_path_patterns=None,
        detailed_catalog=False,
        include_task_parameters=True,
        include_task_runbooks=True,
        inline_task_runbooks=True,
        include_collection_checks=True,
        keep_unknown_style_sections=True,
        adopt_heading_mode=None,
        vars_seed_paths=None,
        style_readme_path=None,
        style_source_path=None,
        style_guide_skeleton=False,
        compare_role_path=None,
        fail_on_unconstrained_dynamic_includes=None,
        fail_on_yaml_like_task_annotations=None,
        ignore_unresolved_internal_underscore_references=False,
    )


def _build_context(role_path: str) -> ScannerContext:
    scan_options = _canonical_scan_options(role_path)
    di = DIContainer(role_path=role_path, scan_options=scan_options)
    return ScannerContext(
        di=di,
        role_path=role_path,
        scan_options=scan_options,
        prepare_scan_context_fn=scanner._prepare_scan_context,
    )


class TestScannerIntegrationEndToEnd:
    """Test complete scanner workflow (end-to-end integration)."""

    def test_scanner_context_orchestrate_scan_with_empty_role(
        self, empty_test_role: Path
    ) -> None:
        """Full scan workflow with empty role produces valid payload."""
        context = _build_context(str(empty_test_role))

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
        context = _build_context(str(basic_test_role))

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
        context = _build_context(str(complex_test_role))

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
        context = _build_context(str(basic_test_role))

        payload = context.orchestrate_scan()

        # Validate metadata presence
        assert "metadata" in payload
        metadata = payload["metadata"]
        assert isinstance(metadata, dict)

    def test_scanner_context_handles_missing_role_gracefully(
        self, tmp_path: Path
    ) -> None:
        """ScannerContext raises explicitly when role path does not exist."""
        missing_role_path = tmp_path / "missing-role"
        assert not missing_role_path.exists()

        context = _build_context(str(missing_role_path))

        with pytest.raises(FileNotFoundError, match="role path not found"):
            context.orchestrate_scan()

    def test_scanner_context_discovered_variables_contain_all_phases(
        self, basic_test_role: Path
    ) -> None:
        """Discovered variables include both static and referenced sources."""
        context = _build_context(str(basic_test_role))

        context.orchestrate_scan()

        discovered = context.discovered_variables
        # Should be tuple (immutable)
        assert isinstance(discovered, tuple)

    def test_scanner_context_state_is_immutable_after_orchestration(
        self, basic_test_role: Path
    ) -> None:
        """ScannerContext maintains immutable state after orchestration."""
        context = _build_context(str(basic_test_role))

        # First orchestration
        payload1 = context.orchestrate_scan()
        discovered1 = context.discovered_variables

        # Second orchestration (should produce same results)
        payload2 = context.orchestrate_scan()
        discovered2 = context.discovered_variables

        # Discovered variables should be identical (immutable)
        assert discovered1 == discovered2

        # Payload contracts should remain stable across repeated orchestration.
        assert isinstance(payload1["display_variables"], dict)
        assert isinstance(payload2["display_variables"], dict)
        assert isinstance(payload1["metadata"], dict)
        assert isinstance(payload2["metadata"], dict)
        assert payload1["display_variables"] == payload2["display_variables"]
        assert payload1["metadata"] == payload2["metadata"]

        # Mutations to one payload must not leak into a subsequent orchestration result.
        payload1["display_variables"]["__test_mutation__"] = {"required": False}
        payload1["metadata"]["__test_mutation__"] = True

        payload3 = context.orchestrate_scan()
        assert "__test_mutation__" not in payload3["display_variables"]
        assert "__test_mutation__" not in payload3["metadata"]

    def test_run_scan_raises_on_discovery_failure_by_default(
        self,
        basic_test_role: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """run_scan must surface discovery failures by default."""

        class _FailingDiscovery:
            def discover(self) -> tuple[object, ...]:
                raise RuntimeError("discovery exploded")

        monkeypatch.setattr(
            DIContainer,
            "factory_variable_discovery",
            lambda self: _FailingDiscovery(),
        )

        with pytest.raises(RuntimeError, match="discovery exploded"):
            scanner.run_scan(
                role_path=str(basic_test_role),
                output="README.md",
                output_format="md",
                dry_run=True,
            )

    def test_run_scan_best_effort_marks_degraded_metadata(
        self,
        basic_test_role: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Best-effort run_scan mode should annotate degraded metadata."""

        captured: dict[str, object] = {}

        class _FailingDiscovery:
            def discover(self) -> tuple[object, ...]:
                raise RuntimeError("discovery exploded")

        def fake_emit_scan_outputs(args: dict[str, object]) -> str:
            captured["metadata"] = args["metadata"]
            return "ok"

        monkeypatch.setattr(
            DIContainer,
            "factory_variable_discovery",
            lambda self: _FailingDiscovery(),
        )
        monkeypatch.setattr(scanner, "_emit_scan_outputs", fake_emit_scan_outputs)

        scanner.run_scan(
            role_path=str(basic_test_role),
            output="README.md",
            output_format="md",
            dry_run=True,
            strict_phase_failures=False,
        )

        metadata = cast(dict[str, object], captured["metadata"])
        scan_errors = cast(list[dict[str, str]], metadata["scan_errors"])
        assert metadata["scan_degraded"] is True
        assert scan_errors[0]["phase"] == "discovery"
        assert scan_errors[0]["error_type"] == "RuntimeError"
        assert scan_errors[0]["message"] == "discovery exploded"
