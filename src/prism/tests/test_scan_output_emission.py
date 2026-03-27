"""Focused tests for scan output sidecar orchestration helpers."""

from pathlib import Path

from prism import scanner
from prism.scanner_submodules import scan_output_emission


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


def test_scanner_wrapper_write_concise_scanner_report_if_enabled_delegates(monkeypatch):
    captured = {}

    def fake_write(**kwargs):
        captured.update(kwargs)
        return Path("/tmp/report.md")

    monkeypatch.setattr(
        scanner,
        "_scan_output_write_concise_scanner_report_if_enabled",
        fake_write,
    )

    result = scanner._write_concise_scanner_report_if_enabled(
        concise_readme=True,
        scanner_report_output="scan.md",
        out_path=Path("/tmp/README.md"),
        include_scanner_report_link=True,
        role_name="demo",
        description="desc",
        display_variables={"x": 1},
        requirements_display=["dep"],
        undocumented_default_filters=[],
        metadata={},
        dry_run=False,
    )

    assert result == Path("/tmp/report.md")
    assert captured["concise_readme"] is True
    assert captured["scanner_report_output"] == "scan.md"
    assert (
        captured["build_scanner_report_markdown"]
        is scanner._build_scanner_report_markdown
    )


def test_scanner_wrapper_write_optional_runbook_outputs_delegates(monkeypatch):
    captured = {}

    def fake_write(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        scanner,
        "_scan_output_write_optional_runbook_outputs",
        fake_write,
    )

    scanner._write_optional_runbook_outputs(
        runbook_output="RUNBOOK.md",
        runbook_csv_output="RUNBOOK.csv",
        role_name="demo",
        metadata={"x": 1},
    )

    assert captured["runbook_output"] == "RUNBOOK.md"
    assert captured["runbook_csv_output"] == "RUNBOOK.csv"
    assert captured["role_name"] == "demo"
    assert captured["metadata"] == {"x": 1}
    assert captured["render_runbook"] is scanner.render_runbook
    assert captured["render_runbook_csv"] is scanner.render_runbook_csv


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


def test_scanner_wrapper_emit_scan_outputs_delegates(monkeypatch):
    """_emit_scan_outputs scanner wrapper delegates to scan_output_emission.emit_scan_outputs."""
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

    monkeypatch.setattr(scanner, "_scan_output_emit_scan_outputs", fake_emit)

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

    result = scanner._emit_scan_outputs(fake_args)

    assert result == "delegated-result"
    assert captured["args"] is fake_args
    assert (
        captured["build_scanner_report_markdown"]
        is scanner._build_scanner_report_markdown
    )
    assert captured["render_and_write_output"] is scanner._render_and_write_scan_output
    assert captured["render_runbook_fn"] is scanner.render_runbook
    assert captured["render_runbook_csv_fn"] is scanner.render_runbook_csv
