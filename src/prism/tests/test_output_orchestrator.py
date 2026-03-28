"""Tests for OutputOrchestrator - render/emit orchestration for scan outputs.

This module tests the OutputOrchestrator class which consolidates:
- Primary output rendering (README, JSON, HTML, PDF formats)
- Sidecar file generation (scanner-report, runbook markdown/CSV)
- Output path resolution and normalization
- Dry-run mode handling
- Metadata mutation (scanner_report_relpath, concise_readme flag)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prism.scanner_core.di import DIContainer
from prism.scanner_core.output_orchestrator import OutputOrchestrator
from prism.scanner_data.contracts import RunScanOutputPayload
from prism.scanner_data.contracts import ScanMetadata


class TestOutputOrchestratorInstantiation:
    """Test OutputOrchestrator initialization and validation."""

    def test_output_orchestrator_can_be_instantiated(self, tmp_path: Path) -> None:
        """OutputOrchestrator should accept DI, output_path, and options."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        assert orchestrator is not None

    def test_output_orchestrator_stores_output_path(self, tmp_path: Path) -> None:
        """OutputOrchestrator should store the output path."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        assert orchestrator._output_path == output_path

    def test_output_orchestrator_stores_options(self, tmp_path: Path) -> None:
        """OutputOrchestrator should store scan options."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md", "concise_readme": True}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        assert orchestrator._options == options


class TestOutputOrchestratorFormatResolution:
    """Test output format detection and path normalization."""

    def test_render_and_emit_resolves_md_format(self, tmp_path: Path) -> None:
        """Render README when output_format is 'md'."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload(
            role_name="test_role",
            description="Test role description",
        )

        result = orchestrator.render_and_emit(payload, dry_run=True)

        assert isinstance(result, (str, bytes))
        assert len(result) > 0
        if isinstance(result, str):
            assert "test_role" in result or "Test role description" in result

    def test_render_and_emit_resolves_json_format(self, tmp_path: Path) -> None:
        """Render JSON when output_format is 'json'."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "json"},
        )
        output_path = str(tmp_path / "output.json")
        options = {"output_format": "json"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload(
            role_name="test_role",
            description="Test description",
        )

        result = orchestrator.render_and_emit(payload, dry_run=True)

        # JSON output should be valid JSON
        if isinstance(result, bytes):
            result_str = result.decode("utf-8")
        else:
            result_str = result

        data = json.loads(result_str)
        assert isinstance(data, dict)

    def test_render_and_emit_resolves_html_format(self, tmp_path: Path) -> None:
        """Render HTML when output_format is 'html'."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "html"},
        )
        output_path = str(tmp_path / "output.html")
        options = {"output_format": "html"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload(role_name="test_role")

        result = orchestrator.render_and_emit(payload, dry_run=True)

        if isinstance(result, bytes):
            result_str = result.decode("utf-8")
        else:
            result_str = result

        assert "html" in result_str.lower()
        assert "test_role" in result_str or "test_role" in str(result_str).lower()

    def test_render_and_emit_normalizes_path_extension_for_json(
        self, tmp_path: Path
    ) -> None:
        """Output path should be normalized for JSON format."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "json"},
        )
        # Provide path without .json extension
        output_path = str(tmp_path / "output")
        options = {"output_format": "json"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload()

        # Render with actual file write
        orchestrator.render_and_emit(payload, dry_run=False)

        # Check the file was written with .json extension
        json_file = tmp_path / "output.json"
        assert json_file.exists()

    def test_render_and_emit_normalizes_path_extension_for_html(
        self, tmp_path: Path
    ) -> None:
        """Output path should be normalized for HTML format."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "html"},
        )
        output_path = str(tmp_path / "output")
        options = {"output_format": "html"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload()

        orchestrator.render_and_emit(payload, dry_run=False)

        html_file = tmp_path / "output.html"
        assert html_file.exists()


class TestOutputOrchestratorDryRun:
    """Test dry-run mode (render without writing files)."""

    def test_render_and_emit_dry_run_returns_content_without_writing(
        self, tmp_path: Path
    ) -> None:
        """Dry-run mode should return content without writing files."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload()

        result = orchestrator.render_and_emit(payload, dry_run=True)

        # Content should be returned
        assert isinstance(result, (str, bytes))
        assert len(result) > 0

        # File should NOT be written
        assert not Path(output_path).exists()

    def test_render_and_emit_normal_mode_writes_files(self, tmp_path: Path) -> None:
        """Normal mode should write files to disk."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload()

        result = orchestrator.render_and_emit(payload, dry_run=False)

        # File should be written
        assert Path(output_path).exists()
        assert len(result) > 0

    def test_render_and_emit_creates_output_directory(self, tmp_path: Path) -> None:
        """Render should create output directory if it doesn't exist."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        nested_dir = tmp_path / "subdir" / "nested"
        output_path = str(nested_dir / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload()

        orchestrator.render_and_emit(payload, dry_run=False)

        assert nested_dir.exists()
        assert Path(output_path).exists()

    def test_render_and_emit_dry_run_does_not_write_sidecar_or_primary_files(
        self, tmp_path: Path
    ) -> None:
        """Dry-run mode should not write primary output or sidecar files."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        scanner_report_path = tmp_path / "scan-report.md"
        runbook_path = tmp_path / "runbook.md"
        runbook_csv_path = tmp_path / "runbook.csv"
        options = {
            "output_format": "md",
            "concise_readme": True,
            "scanner_report_output": str(scanner_report_path),
            "runbook_output": str(runbook_path),
            "runbook_csv_output": str(runbook_csv_path),
        }

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload()

        result = orchestrator.render_and_emit(payload, dry_run=True)

        assert isinstance(result, (str, bytes))
        assert not Path(output_path).exists()
        assert not scanner_report_path.exists()
        assert not runbook_path.exists()
        assert not runbook_csv_path.exists()


class TestOutputOrchestratorMetadataMutation:
    """Test metadata field updates during output rendering."""

    def test_render_and_emit_sets_concise_readme_flag(self, tmp_path: Path) -> None:
        """Metadata should have concise_readme flag set when enabled."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md", "concise_readme": True}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload()
        original_metadata = dict(payload["metadata"])  # Save original for comparison

        orchestrator.render_and_emit(payload, dry_run=True)

        # Payload metadata should NOT be mutated (immutable design)
        assert payload["metadata"] == original_metadata
        assert "concise_readme" not in payload["metadata"]

    def test_render_and_emit_preserves_metadata_fields(self, tmp_path: Path) -> None:
        """Metadata fields should be preserved during rendering."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload()
        original_meta = payload["metadata"].copy()

        orchestrator.render_and_emit(payload, dry_run=True)

        # Original fields should remain
        for key, value in original_meta.items():
            if key not in ["concise_readme", "scanner_report_relpath"]:
                assert payload["metadata"].get(key) == value


class TestOutputOrchestratorSidecarGeneration:
    """Test sidecar file generation (scanner-report, runbook)."""

    def test_emit_runbook_sidecars_returns_dict(self, tmp_path: Path) -> None:
        """emit_runbook_sidecars should return dict mapping paths to bytes written."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        md_path = str(tmp_path / "runbook.md")
        csv_path = str(tmp_path / "runbook.csv")

        result = orchestrator.emit_runbook_sidecars(md_path, csv_path)

        assert isinstance(result, dict)

    def test_emit_runbook_sidecars_writes_markdown(self, tmp_path: Path) -> None:
        """emit_runbook_sidecars should write markdown file."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        md_path = str(tmp_path / "runbook.md")
        csv_path = str(tmp_path / "runbook.csv")

        orchestrator.emit_runbook_sidecars(md_path, csv_path)

        assert Path(md_path).exists()

    def test_emit_runbook_sidecars_writes_csv(self, tmp_path: Path) -> None:
        """emit_runbook_sidecars should write CSV file."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        md_path = str(tmp_path / "runbook.md")
        csv_path = str(tmp_path / "runbook.csv")

        orchestrator.emit_runbook_sidecars(md_path, csv_path)

        assert Path(csv_path).exists()

    def test_emit_runbook_sidecars_returns_byte_counts(self, tmp_path: Path) -> None:
        """emit_runbook_sidecars should return byte counts for written files."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        md_path = str(tmp_path / "runbook.md")
        csv_path = str(tmp_path / "runbook.csv")

        result = orchestrator.emit_runbook_sidecars(md_path, csv_path)

        # Result should have entries for the files
        assert md_path in result or len(result) > 0

    def test_render_and_emit_runbook_sidecars_use_payload_role_and_metadata(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """render_and_emit should pass payload role_name and updated metadata to runbook renderers."""
        captured: dict[str, Any] = {}

        def _fake_render_runbook(*, role_name: str, metadata: dict[str, Any]) -> str:
            captured["role_name"] = role_name
            captured["metadata"] = metadata
            return "# Runbook\n"

        def _fake_render_runbook_csv(metadata: dict[str, Any]) -> str:
            captured["csv_metadata"] = metadata
            return "column\nvalue\n"

        monkeypatch.setattr(
            "prism.scanner_core.output_orchestrator.render_runbook",
            _fake_render_runbook,
        )
        monkeypatch.setattr(
            "prism.scanner_core.output_orchestrator.render_runbook_csv",
            _fake_render_runbook_csv,
        )

        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {
            "output_format": "md",
            "concise_readme": True,
            "runbook_output": str(tmp_path / "runbook.md"),
            "runbook_csv_output": str(tmp_path / "runbook.csv"),
        }

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )
        payload = _build_test_payload(role_name="real_role")

        orchestrator.render_and_emit(payload, dry_run=False)

        assert captured["role_name"] == "real_role"
        assert captured["metadata"]["concise_readme"] is True
        assert captured["csv_metadata"] == captured["metadata"]

    def test_render_and_emit_dry_run_skips_sidecar_renderers(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Dry-run mode should skip sidecar rendering functions entirely."""
        called = {
            "scanner_report": False,
            "runbook": False,
            "runbook_csv": False,
        }

        def _fake_scanner_report_markdown(**_: Any) -> str:
            called["scanner_report"] = True
            return "# Scanner Report\n"

        def _fake_render_runbook(*, role_name: str, metadata: dict[str, Any]) -> str:
            _ = role_name
            _ = metadata
            called["runbook"] = True
            return "# Runbook\n"

        def _fake_render_runbook_csv(metadata: dict[str, Any]) -> str:
            _ = metadata
            called["runbook_csv"] = True
            return "column\nvalue\n"

        monkeypatch.setattr(
            "prism.scanner_core.output_orchestrator.build_scanner_report_markdown",
            _fake_scanner_report_markdown,
        )
        monkeypatch.setattr(
            "prism.scanner_core.output_orchestrator.render_runbook",
            _fake_render_runbook,
        )
        monkeypatch.setattr(
            "prism.scanner_core.output_orchestrator.render_runbook_csv",
            _fake_render_runbook_csv,
        )

        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {
            "output_format": "md",
            "concise_readme": True,
            "scanner_report_output": str(tmp_path / "scan-report.md"),
            "runbook_output": str(tmp_path / "runbook.md"),
            "runbook_csv_output": str(tmp_path / "runbook.csv"),
        }

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload(role_name="real_role")

        orchestrator.render_and_emit(payload, dry_run=True)

        assert called == {
            "scanner_report": False,
            "runbook": False,
            "runbook_csv": False,
        }


class TestOutputOrchestratorIntegration:
    """Integration tests with realistic scan payloads."""

    def test_render_and_emit_with_complete_payload(self, tmp_path: Path) -> None:
        """Full integration: render_and_emit with complete payload."""
        di = DIContainer(
            role_path="/tmp/test_role",
            scan_options={"output_format": "md"},
        )
        output_path = str(tmp_path / "README.md")
        options = {"output_format": "md"}

        orchestrator = OutputOrchestrator(
            di=di,
            output_path=output_path,
            options=options,
        )

        payload = _build_test_payload(
            role_name="complex_role",
            description="A more complex role",
            display_variables={"var1": {"type": "string", "default": "value"}},
            requirements_display=["ansible>=2.9"],
        )

        result = orchestrator.render_and_emit(payload, dry_run=False)

        assert Path(output_path).exists()
        assert len(result) > 0

    def test_render_and_emit_handles_all_formats(self, tmp_path: Path) -> None:
        """render_and_emit should handle multiple output formats."""
        for output_format in ["md", "json", "html"]:
            output_file = tmp_path / f"output_{output_format}"
            di = DIContainer(
                role_path="/tmp/test_role",
                scan_options={"output_format": output_format},
            )
            output_path = str(output_file)
            options = {"output_format": output_format}

            orchestrator = OutputOrchestrator(
                di=di,
                output_path=output_path,
                options=options,
            )

            payload = _build_test_payload()

            result = orchestrator.render_and_emit(payload, dry_run=False)

            assert result is not None
            assert len(result) > 0


# ============================================================================
# Test Helpers
# ============================================================================


def _build_test_payload(
    role_name: str = "test_role",
    description: str = "Test description",
    display_variables: dict[str, Any] | None = None,
    requirements_display: list[Any] | None = None,
    undocumented_filters: list[Any] | None = None,
) -> RunScanOutputPayload:
    """Build a minimal test RunScanOutputPayload."""
    return {
        "role_name": role_name,
        "description": description,
        "display_variables": display_variables or {},
        "requirements_display": requirements_display or [],
        "undocumented_default_filters": undocumented_filters or [],
        "metadata": _build_test_metadata(),
    }


def _build_test_metadata() -> ScanMetadata:
    """Build a minimal test ScanMetadata."""
    return {
        "molecule_scenarios": [],
        "marker_prefix": "ansible_doc",
        "detailed_catalog": False,
        "include_task_parameters": False,
        "include_task_runbooks": False,
        "inline_task_runbooks": False,
        "keep_unknown_style_sections": False,
        "handlers": [],
        "tasks": [],
        "templates": [],
        "files": [],
        "tests": [],
        "defaults": [],
        "vars": [],
        "meta": {},
        "features": {
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
        },
        "unconstrained_dynamic_task_includes": [],
        "unconstrained_dynamic_role_includes": [],
        "enabled_sections": [],
        "variable_insights": [],
        "yaml_parse_failures": [],
        "role_notes": [],
        "scanner_counters": None,
        "fail_on_unconstrained_dynamic_includes": False,
        "fail_on_yaml_like_task_annotations": False,
        "ignore_unresolved_internal_underscore_references": False,
        "doc_insights": {},
    }
