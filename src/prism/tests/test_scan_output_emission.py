"""Focused tests for scan output sidecar orchestration helpers."""

import importlib

import pytest

from prism.scanner_core import scan_runtime
from prism.scanner_io import scan_output_emission


def test_build_scanner_report_output_path_uses_default_suffix(tmp_path):
    out_path = tmp_path / "README.md"

    report_path = scan_output_emission.build_scanner_report_output_path(
        scanner_report_output=None,
        out_path=out_path,
    )

    assert report_path == tmp_path / "README.scan-report.md"


def test_build_scanner_report_output_path_respects_explicit_path(tmp_path):
    out_path = tmp_path / "README.md"
    explicit = tmp_path / "reports" / "scan.md"

    report_path = scan_output_emission.build_scanner_report_output_path(
        scanner_report_output=str(explicit),
        out_path=out_path,
    )

    assert report_path == explicit


def test_write_concise_scanner_report_if_enabled_dry_run_sets_flags_only(tmp_path):
    out_path = tmp_path / "docs" / "README.md"
    metadata = {}

    report_path = scan_output_emission.write_concise_scanner_report_if_enabled(
        concise_readme=True,
        scanner_report_output=None,
        out_path=out_path,
        include_scanner_report_link=False,
        role_name="demo",
        description="desc",
        display_variables={"x": 1},
        requirements_display=["dep"],
        undocumented_default_filters=[],
        metadata=metadata,
        dry_run=True,
        build_scanner_report_markdown=lambda **kwargs: "should-not-write",
    )

    assert report_path == tmp_path / "docs" / "README.scan-report.md"
    assert metadata["concise_readme"] is True
    assert metadata["include_scanner_report_link"] is False
    assert "scanner_report_relpath" not in metadata
    assert not report_path.exists()


def test_write_concise_scanner_report_if_enabled_writes_report_and_relpath(tmp_path):
    out_path = tmp_path / "docs" / "README.md"
    explicit_report = tmp_path / "reports" / "scanner.md"
    metadata = {}
    captured = {}

    def fake_build_scanner_report_markdown(**kwargs):
        captured["kwargs"] = kwargs
        return "scanner-report-content\n"

    report_path = scan_output_emission.write_concise_scanner_report_if_enabled(
        concise_readme=True,
        scanner_report_output=str(explicit_report),
        out_path=out_path,
        include_scanner_report_link=True,
        role_name="demo",
        description="desc",
        display_variables={"x": 1},
        requirements_display=["dep"],
        undocumented_default_filters=[{"match": "default"}],
        metadata=metadata,
        dry_run=False,
        build_scanner_report_markdown=fake_build_scanner_report_markdown,
    )

    assert report_path == explicit_report
    assert report_path.read_text(encoding="utf-8") == "scanner-report-content\n"
    assert metadata["scanner_report_relpath"] == "../reports/scanner.md"
    assert captured["kwargs"]["role_name"] == "demo"
    assert captured["kwargs"]["metadata"] is metadata


def test_write_optional_runbook_outputs_writes_requested_sidecars(tmp_path):
    metadata = {"task_catalog": [{"name": "deploy"}]}
    runbook_out = tmp_path / "sidecars" / "RUNBOOK.md"
    runbook_csv_out = tmp_path / "sidecars" / "RUNBOOK.csv"

    scan_output_emission.write_optional_runbook_outputs(
        runbook_output=str(runbook_out),
        runbook_csv_output=str(runbook_csv_out),
        role_name="demo",
        metadata=metadata,
        render_runbook=lambda role_name, metadata: f"runbook::{role_name}::{len(metadata)}\n",
        render_runbook_csv=lambda metadata: f"csv::{len(metadata)}\n",
    )

    assert runbook_out.read_text(encoding="utf-8") == "runbook::demo::1\n"
    assert runbook_csv_out.read_text(encoding="utf-8") == "csv::1\n"


def test_emit_scan_outputs_dry_run_returns_rendered_result(tmp_path):
    """emit_scan_outputs dry-run returns rendered content without writing sidecars."""
    out_md = tmp_path / "README.md"
    args = {
        "output": str(out_md),
        "output_format": "md",
        "concise_readme": False,
        "scanner_report_output": None,
        "include_scanner_report_link": True,
        "role_name": "dry_role",
        "description": "dry desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
        "template": None,
        "dry_run": True,
        "runbook_output": None,
        "runbook_csv_output": None,
    }

    result = scan_output_emission.emit_scan_outputs(
        args,
        build_scanner_report_markdown=lambda **kw: "report",
        render_and_write_output=lambda **kw: "rendered-md",
        render_runbook_fn=lambda role, meta: "runbook",
        render_runbook_csv_fn=lambda meta: "csv",
    )

    assert result == "rendered-md"
    assert not out_md.exists()


def test_emit_scan_outputs_non_dry_run_writes_sidecars(tmp_path):
    """emit_scan_outputs non-dry-run writes optional runbook sidecars when requested."""
    out_md = tmp_path / "README.md"
    runbook_out = tmp_path / "sidecars" / "RUNBOOK.md"
    args = {
        "output": str(out_md),
        "output_format": "md",
        "concise_readme": False,
        "scanner_report_output": None,
        "include_scanner_report_link": True,
        "role_name": "live_role",
        "description": "live desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
        "template": None,
        "dry_run": False,
        "runbook_output": str(runbook_out),
        "runbook_csv_output": None,
    }

    result = scan_output_emission.emit_scan_outputs(
        args,
        build_scanner_report_markdown=lambda **kw: "report",
        render_and_write_output=lambda **kw: "written-md",
        render_runbook_fn=lambda role, meta: f"runbook::{role}\n",
        render_runbook_csv_fn=lambda meta: "csv\n",
    )

    assert result == "written-md"
    assert runbook_out.read_text(encoding="utf-8") == "runbook::live_role\n"


def test_emit_scan_outputs_dry_run_preserves_binary_bytes_for_pdf(tmp_path):
    """Dry-run binary formats should preserve bytes (no UTF-8 coercion)."""
    out_pdf = tmp_path / "scan.pdf"
    args = {
        "output": str(out_pdf),
        "output_format": "pdf",
        "concise_readme": False,
        "scanner_report_output": None,
        "include_scanner_report_link": False,
        "role_name": "pdf_role",
        "description": "pdf desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
        "template": None,
        "dry_run": True,
        "runbook_output": None,
        "runbook_csv_output": None,
    }

    result = scan_output_emission.emit_scan_outputs(
        args,
        build_scanner_report_markdown=lambda **kw: "report",
        render_and_write_output=lambda **kw: b"%PDF-1.7\nmock\n",
        render_runbook_fn=lambda role, meta: "runbook",
        render_runbook_csv_fn=lambda meta: "csv",
    )

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")


def test_emit_scan_outputs_uses_canonical_emit_output_orchestrator(monkeypatch):
    captured = {}

    def fake_orchestrate_output_emission(**kwargs):
        captured.update(kwargs)
        return "canonical-result"

    monkeypatch.setattr(
        scan_output_emission,
        "_orchestrate_output_emission",
        fake_orchestrate_output_emission,
    )

    args = {
        "output": "README.md",
        "output_format": "md",
        "concise_readme": True,
        "scanner_report_output": "SCAN.md",
        "include_scanner_report_link": True,
        "role_name": "demo_role",
        "description": "demo desc",
        "display_variables": {"var": {"required": True}},
        "requirements_display": ["req"],
        "undocumented_default_filters": [{"match": "default()"}],
        "metadata": {"existing": True},
        "template": "template.j2",
        "dry_run": False,
        "runbook_output": "RUNBOOK.md",
        "runbook_csv_output": "RUNBOOK.csv",
    }

    result = scan_output_emission.emit_scan_outputs(
        args,
        build_scanner_report_markdown=lambda **_kw: "report",
        render_and_write_output=lambda **_kw: "rendered",
        render_runbook_fn=lambda _role, _meta: "runbook",
        render_runbook_csv_fn=lambda _meta: "csv",
    )

    assert result == "canonical-result"
    assert captured["args"]["role_name"] == "demo_role"
    assert captured["args"]["concise_readme"] is True
    assert callable(captured["render_and_write"])
    assert callable(captured["render_scanner_report"])
    assert callable(captured["render_runbook"])
    assert callable(captured["render_runbook_csv"])


def test_scan_runtime_emit_scan_outputs_delegates_to_emission_function():
    captured = {}

    def fake_emit(
        args,
        *,
        build_scanner_report_markdown,
        render_and_write_output,
        render_runbook_fn,
        render_runbook_csv_fn,
    ):
        captured["args"] = args
        captured["build_scanner_report_markdown"] = build_scanner_report_markdown
        captured["render_and_write_output"] = render_and_write_output
        captured["render_runbook_fn"] = render_runbook_fn
        captured["render_runbook_csv_fn"] = render_runbook_csv_fn
        return "delegated-result"

    fake_args = {
        "output": "README.md",
        "output_format": "md",
        "concise_readme": False,
        "scanner_report_output": None,
        "include_scanner_report_link": True,
        "role_name": "r",
        "description": "d",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
        "template": None,
        "dry_run": True,
        "runbook_output": None,
        "runbook_csv_output": None,
    }

    result = scan_runtime.emit_scan_outputs(
        fake_args,
        emit_scan_outputs_fn=fake_emit,
        build_scanner_report_markdown=lambda **_kwargs: "report",
        render_and_write_scan_output=lambda **_kwargs: "ok",
        render_runbook=lambda role_name, metadata: f"runbook::{role_name}::{len(metadata)}",
        render_runbook_csv=lambda metadata: f"csv::{len(metadata)}",
    )

    assert result == "delegated-result"
    assert captured["args"] is fake_args
    assert callable(captured["build_scanner_report_markdown"])
    assert callable(captured["render_and_write_output"])
    assert callable(captured["render_runbook_fn"])
    assert callable(captured["render_runbook_csv_fn"])


def test_scan_runtime_emit_scan_outputs_forwards_runtime_dependencies():
    fake_args = {
        "output": "README.md",
        "output_format": "md",
        "concise_readme": False,
        "scanner_report_output": None,
        "include_scanner_report_link": False,
        "role_name": "r",
        "description": "d",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
        "template": None,
        "dry_run": True,
        "runbook_output": None,
        "runbook_csv_output": None,
    }

    captured = {}

    def fake_emit(args: dict, **kwargs: object) -> str:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "runtime-delegated"

    result = scan_runtime.emit_scan_outputs(
        fake_args,
        emit_scan_outputs_fn=fake_emit,
        build_scanner_report_markdown=lambda **_kwargs: "report",
        render_and_write_scan_output=lambda **_kwargs: "rendered",
        render_runbook=lambda _role_name, _metadata: "runbook",
        render_runbook_csv=lambda _metadata: "csv",
    )

    assert result == "runtime-delegated"
    assert captured["args"] is fake_args
    assert "render_and_write_output" in captured["kwargs"]


def test_scan_output_emission_compat_module_retired():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("prism.scanner_submodules.scan_output_emission")
