"""Focused fsrc tests for output rendering and emission foundations."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> object:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(FSRC_SOURCE_ROOT))
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        yield
    finally:
        sys.path[:] = original_path
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        sys.modules.update(original_modules)


def test_fsrc_output_module_resolve_and_render_foundation() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        output_module = importlib.import_module("prism.scanner_io.output")

    assert output_module.resolve_output_path("/tmp/README", "md").name == "README"
    assert (
        output_module.resolve_output_path("/tmp/README", "json").suffix.lower()
        == ".json"
    )
    assert (
        output_module.resolve_output_path("/tmp/README", "html").suffix.lower()
        == ".html"
    )

    rendered = output_module.render_final_output(
        "# Demo",
        "json",
        "demo",
        payload={"role_name": "demo"},
    )
    assert isinstance(rendered, str)
    assert '"role_name": "demo"' in rendered


def test_fsrc_orchestrate_output_emission_dry_run_skips_file_writes(
    tmp_path: Path,
) -> None:
    output_target = tmp_path / "README.md"
    scanner_sidecar = tmp_path / "README.scan.md"
    runbook_md = tmp_path / "runbook.md"
    runbook_csv = tmp_path / "runbook.csv"
    metadata: dict[str, Any] = {}
    seen_metadata: dict[str, Any] = {}

    with _prefer_fsrc_prism_on_sys_path():
        emit_module = importlib.import_module("prism.scanner_io.emit_output")

        result = emit_module.orchestrate_output_emission(
            args={
                "role_name": "demo_role",
                "description": "demo description",
                "display_variables": {"demo": {"default": "x"}},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": metadata,
                "output": str(output_target),
                "output_format": "md",
                "template": None,
                "dry_run": True,
                "concise_readme": True,
                "scanner_report_output": str(scanner_sidecar),
                "include_scanner_report_link": True,
                "runbook_output": str(runbook_md),
                "runbook_csv_output": str(runbook_csv),
            },
            render_and_write=lambda **kwargs: seen_metadata.update(kwargs["metadata"])
            or "DRY-RUN",
            render_scanner_report=lambda **_kwargs: "SCANNER-REPORT",
            render_runbook=lambda _role_name, _metadata: "RUNBOOK",
            render_runbook_csv=lambda _metadata: "RUNBOOK_CSV",
        )

    assert result == "DRY-RUN"
    assert output_target.exists() is False
    assert scanner_sidecar.exists() is False
    assert runbook_md.exists() is False
    assert runbook_csv.exists() is False
    assert metadata == {}
    assert seen_metadata["concise_readme"] is True
    assert seen_metadata["include_scanner_report_link"] is True
    assert "scanner_report_relpath" not in seen_metadata


def test_fsrc_orchestrate_output_emission_write_mode_writes_sidecars(
    tmp_path: Path,
) -> None:
    output_target = tmp_path / "README.md"
    scanner_sidecar = tmp_path / "README.scan.md"
    runbook_md = tmp_path / "runbook.md"
    runbook_csv = tmp_path / "runbook.csv"
    metadata: dict[str, Any] = {}
    seen_metadata: dict[str, Any] = {}

    with _prefer_fsrc_prism_on_sys_path():
        emit_module = importlib.import_module("prism.scanner_io.emit_output")

        def _render_and_write(**kwargs: Any) -> str:
            out_path = Path(kwargs["out_path"])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("PRIMARY", encoding="utf-8")
            seen_metadata.update(kwargs["metadata"])
            return str(out_path)

        result = emit_module.orchestrate_output_emission(
            args={
                "role_name": "demo_role",
                "description": "demo description",
                "display_variables": {"demo": {"default": "x"}},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": metadata,
                "output": str(output_target),
                "output_format": "md",
                "template": None,
                "dry_run": False,
                "concise_readme": True,
                "scanner_report_output": str(scanner_sidecar),
                "include_scanner_report_link": True,
                "runbook_output": str(runbook_md),
                "runbook_csv_output": str(runbook_csv),
            },
            render_and_write=_render_and_write,
            render_scanner_report=lambda **_kwargs: "SCANNER-REPORT",
            render_runbook=lambda _role_name, _metadata: "RUNBOOK",
            render_runbook_csv=lambda _metadata: "RUNBOOK_CSV",
        )

    assert str(output_target) == result
    assert output_target.read_text(encoding="utf-8") == "PRIMARY"
    assert scanner_sidecar.read_text(encoding="utf-8") == "SCANNER-REPORT"
    assert runbook_md.read_text(encoding="utf-8") == "RUNBOOK"
    assert runbook_csv.read_text(encoding="utf-8") == "RUNBOOK_CSV"
    assert metadata == {}
    assert seen_metadata["concise_readme"] is True
    assert seen_metadata["include_scanner_report_link"] is True
    assert seen_metadata["scanner_report_relpath"] == "README.scan.md"
