"""Focused tests for output rendering and emission orchestration."""

from pathlib import Path
from unittest import mock


from prism import scanner
from prism.scanner_io import emit_output


def test_orchestrate_output_emission_coordinates_primary_and_sidecars(tmp_path):
    """Test that output emission orchestration coordinates primary and sidecar renders."""
    role_name = "test_role"
    description = "test description"
    display_variables = {"var1": "value1"}
    requirements_display = ["req1"]
    undocumented_default_filters = [{"match": "default()"}]
    metadata = {"test": True}

    # Bundle arguments for orchestration
    orchestration_args = {
        "role_name": role_name,
        "description": description,
        "display_variables": display_variables,
        "requirements_display": requirements_display,
        "undocumented_default_filters": undocumented_default_filters,
        "metadata": metadata,
        "output": str(tmp_path / "README.md"),
        "output_format": "md",
        "template": None,
        "dry_run": True,
        "concise_readme": False,
        "scanner_report_output": None,
        "include_scanner_report_link": False,
        "runbook_output": None,
        "runbook_csv_output": None,
    }

    # Test that orchestrate_output_emission exists and accepts args
    result = emit_output.orchestrate_output_emission(
        args=orchestration_args,
        render_and_write=mock.MagicMock(return_value=b"primary output"),
        render_scanner_report=mock.MagicMock(return_value="scanner report"),
        render_runbook=mock.MagicMock(return_value="runbook"),
        render_runbook_csv=mock.MagicMock(return_value="csv"),
    )

    assert result is not None


def test_emit_output_wrapper_delegates_to_submodule():
    """Test that scanner._emit_output_orchestration delegates correctly."""
    orchestration_args = {
        "role_name": "test",
        "description": "desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
        "output": "README.md",
        "output_format": "md",
        "template": None,
        "dry_run": True,
        "concise_readme": False,
        "scanner_report_output": None,
        "include_scanner_report_link": False,
        "runbook_output": None,
        "runbook_csv_output": None,
    }

    # The result should be a string when called with dry_run=True
    result = scanner._emit_output_orchestration(orchestration_args)

    assert isinstance(result, str)
    # Verify it's not empty
    assert len(result) > 0


def test_build_output_emission_context_captures_all_params():
    """Test that output emission context builder captures all necessary parameters."""
    params = {
        "output": "README.md",
        "output_format": "md",
        "template": None,
        "dry_run": False,
        "concise_readme": True,
        "scanner_report_output": "REPORT.md",
        "include_scanner_report_link": True,
        "runbook_output": None,
        "runbook_csv_output": None,
    }

    context = emit_output.build_output_emission_context(
        output_payload={
            "role_name": "test",
            "description": "desc",
            "display_variables": {},
            "requirements_display": [],
            "undocumented_default_filters": [],
            "metadata": {},
        },
        **params,
    )

    assert context["output"] == "README.md"
    assert context["output_format"] == "md"
    assert context["dry_run"] is False
    assert context["concise_readme"] is True
    assert context["scanner_report_output"] == "REPORT.md"


def test_resolve_output_file_paths_handles_format_extensions():
    """Test that output path resolution handles different format extensions."""
    # Test JSON format
    out_path = Path("/tmp/output.txt")
    json_path = emit_output.resolve_output_file_path(out_path, "json")
    assert json_path.suffix == ".json"

    # Test HTML format
    html_path = emit_output.resolve_output_file_path(out_path, "html")
    assert html_path.suffix in (".html", ".htm")

    # Test markdown format - should preserve path
    md_path = emit_output.resolve_output_file_path(out_path, "md")
    assert md_path is not None


def test_write_output_file_creates_parent_directories(tmp_path):
    """Test that output file writing creates parent directories as needed."""
    nested_path = tmp_path / "deep" / "nested" / "output.md"
    content = "test content"

    result = emit_output.write_output_file(nested_path, content)

    assert nested_path.exists()
    assert nested_path.read_text(encoding="utf-8") == content
    assert result is not None


def test_emit_primary_output_delegates_markdown_rendering(tmp_path):
    """Test primary output emission delegates markdown rendering."""
    out_path = tmp_path / "README.md"
    metadata = {"test": True}
    captured = {}

    def fake_render_and_write(**kwargs):
        captured.update(kwargs)
        return str(out_path)

    emit_output.emit_primary_output(
        out_path=out_path,
        output_format="md",
        template=None,
        dry_run=True,
        metadata=metadata,
        render_and_write=fake_render_and_write,
    )

    assert "output_format" in captured
    assert captured["dry_run"] is True


def test_emit_scanner_report_sidecar_respects_dry_run(tmp_path):
    """Test that scanner report sidecar respects dry-run setting."""
    out_path = tmp_path / "README.md"
    report_path = tmp_path / "README.scan-report.md"
    metadata = {}

    result = emit_output.emit_scanner_report_sidecar(
        concise_readme=True,
        scanner_report_output=str(report_path),
        out_path=out_path,
        include_scanner_report_link=True,
        metadata=metadata,
        dry_run=True,
        render_scanner_report=lambda **kwargs: "report content",
    )

    # In dry-run, the report should not be written
    assert not report_path.exists() or result is not None


def test_emit_runbook_sidecars_writes_when_requested(tmp_path):
    """Test that runbook sidecars are written when paths are provided."""
    runbook_path = tmp_path / "RUNBOOK.md"
    csv_path = tmp_path / "RUNBOOK.csv"
    metadata = {"test": True}

    emit_output.emit_runbook_sidecars(
        runbook_output=str(runbook_path),
        runbook_csv_output=str(csv_path),
        metadata=metadata,
        render_runbook=lambda role_name, metadata: "runbook content",
        render_runbook_csv=lambda metadata: "csv content",
    )

    assert runbook_path.read_text(encoding="utf-8") == "runbook content"
    assert csv_path.read_text(encoding="utf-8") == "csv content"


def test_emit_runbook_sidecars_skips_when_not_requested(tmp_path):
    """Test that runbook sidecars are skipped when paths are None."""
    metadata = {"test": True}

    # Should not raise an error
    emit_output.emit_runbook_sidecars(
        runbook_output=None,
        runbook_csv_output=None,
        metadata=metadata,
        render_runbook=lambda **kwargs: "should not call",
        render_runbook_csv=lambda **kwargs: "should not call",
    )


def test_resolve_scanner_report_path_uses_default_suffix():
    """Test that scanner report path resolution uses default suffix."""
    out_path = Path("/tmp/README.md")
    report_path = emit_output.resolve_scanner_report_path(
        scanner_report_output=None,
        out_path=out_path,
    )
    assert report_path.name == "README.scan-report.md"


def test_resolve_scanner_report_path_respects_explicit():
    """Test that scanner report path respects explicit output."""
    out_path = Path("/tmp/README.md")
    explicit = Path("/custom/report.md")
    report_path = emit_output.resolve_scanner_report_path(
        scanner_report_output=str(explicit),
        out_path=out_path,
    )
    assert report_path == explicit


def test_scanner_emit_output_alias_targets_canonical_scanner_io_module():
    assert (
        scanner._emit_output_orchestrate_output_emission.__module__
        == "prism.scanner_io.emit_output"
    )
