"""Focused parity tests for fsrc scanner reporting renderers."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_SOURCE_ROOT = PROJECT_ROOT / "src"
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_package_root_on_sys_path(package_root: Path) -> object:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(package_root))
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


def _load_module(module_name: str, package_root: Path) -> Any:
    with _prefer_package_root_on_sys_path(package_root):
        return importlib.import_module(module_name)


def _render_section_body(
    section_id: str,
    role_name: str,
    description: str,
    variables: dict[str, Any],
    requirements: list[Any],
    default_filters: list[Any],
    metadata: dict[str, Any],
) -> str:
    _ = role_name, description, variables, requirements, default_filters, metadata
    if section_id == "task_summary":
        return "Task summary body"
    if section_id == "features":
        return "Features body"
    return ""


def test_fsrc_scanner_report_markdown_shape_parity_against_src() -> None:
    src_report_module = _load_module("prism.scanner_reporting.report", SRC_SOURCE_ROOT)
    fsrc_report_module = _load_module(
        "prism.scanner_reporting.report", FSRC_SOURCE_ROOT
    )

    metadata = {
        "variable_insights": [
            {
                "name": "documented_var",
                "documented": True,
                "required": True,
                "is_unresolved": False,
                "is_ambiguous": False,
                "secret": False,
                "provenance_confidence": 0.95,
            },
            {
                "name": "missing_var",
                "documented": False,
                "required": False,
                "is_unresolved": True,
                "is_ambiguous": False,
                "secret": False,
                "provenance_confidence": 0.65,
                "uncertainty_reason": "No static definition found.",
            },
            {
                "name": "ambiguous_var",
                "documented": False,
                "required": False,
                "is_unresolved": False,
                "is_ambiguous": True,
                "secret": False,
                "provenance_confidence": 0.72,
                "uncertainty_reason": "May come from include_vars at runtime.",
            },
        ],
        "features": {
            "included_role_calls": 2,
            "dynamic_included_role_calls": 1,
            "disabled_task_annotations": 1,
            "yaml_like_task_annotations": 1,
        },
        "yaml_parse_failures": [
            {
                "file": "tasks/main.yml",
                "line": 6,
                "column": 3,
                "error": "mapping values are not allowed here",
            }
        ],
    }

    kwargs = {
        "role_name": "demo_role",
        "description": "Scanner sidecar demo.",
        "variables": {},
        "requirements": [],
        "default_filters": [{"target": "demo_var", "line": 5}],
        "metadata": metadata,
        "render_section_body": _render_section_body,
    }

    src_markdown = src_report_module.build_scanner_report_markdown(**kwargs)
    fsrc_markdown = fsrc_report_module.build_scanner_report_markdown(**kwargs)

    for required_section in (
        "Summary",
        "Variable provenance issues",
        "YAML parse failures",
        "Task/module usage summary",
        "Auto-detected role features",
    ):
        assert required_section in src_markdown
        assert required_section in fsrc_markdown

    assert src_markdown.count("**Total variables**") == 1
    assert fsrc_markdown.count("**Total variables**") == 1
    assert src_markdown.count("Unresolved variables:") == 1
    assert fsrc_markdown.count("Unresolved variables:") == 1
    assert src_markdown.count("Ambiguous variables:") == 1
    assert fsrc_markdown.count("Ambiguous variables:") == 1


def test_fsrc_runbook_rows_and_csv_shape_parity_against_src() -> None:
    src_runbook_module = _load_module(
        "prism.scanner_reporting.runbook", SRC_SOURCE_ROOT
    )
    fsrc_runbook_module = _load_module(
        "prism.scanner_reporting.runbook", FSRC_SOURCE_ROOT
    )

    metadata = {
        "task_catalog": [
            {
                "file": "tasks/main.yml",
                "name": "Install package",
                "annotations": [
                    {"kind": "runbook", "text": "Install dependencies."},
                    {"kind": "warning", "text": "Requires root access."},
                ],
            },
            {
                "file": "tasks/cleanup.yml",
                "name": "Cleanup",
                "annotations": [{"kind": "note", "text": "Post-deploy cleanup."}],
            },
        ]
    }

    src_rows = src_runbook_module.build_runbook_rows(metadata)
    fsrc_rows = fsrc_runbook_module.build_runbook_rows(metadata)
    assert src_rows == fsrc_rows
    assert len(fsrc_rows) == 3

    src_csv = src_runbook_module.render_runbook_csv(metadata)
    fsrc_csv = fsrc_runbook_module.render_runbook_csv(metadata)
    assert src_csv == fsrc_csv
    csv_lines = [line for line in fsrc_csv.strip().splitlines() if line]
    assert csv_lines[0] == "file,task_name,step"
    assert len(csv_lines) == 4


def test_w2_t01_scanner_reporting_import_boundary() -> None:
    runbook_module = _load_module("prism.scanner_reporting.runbook", FSRC_SOURCE_ROOT)

    imports = set(runbook_module.__dict__.get("__imports__", []))
    if not imports:
        imports = {
            line.strip()
            for line in Path(runbook_module.__file__)
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip().startswith("from ") or line.strip().startswith("import ")
        }

    forbidden = [
        line
        for line in imports
        if "prism.scanner_readme." in line
        and "prism.scanner_data.rendering_seams" not in line
    ]

    assert not forbidden
