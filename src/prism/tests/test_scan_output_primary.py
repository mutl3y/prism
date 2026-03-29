"""Focused tests for primary scan output orchestration helpers."""

import importlib
from pathlib import Path
from typing import get_type_hints

import pytest

from prism import scanner
from prism.scanner_io import output
from prism.scanner_io import scan_output_primary


def test_render_and_write_scan_output_json_dry_run_skips_markdown_render(tmp_path):
    out_path = tmp_path / "README.json"
    captured = {}

    def fake_render_readme(*args, **kwargs):
        raise AssertionError("render_readme should not be called for json output")

    def fake_render_final_output(markdown_content, output_format, title, payload=None):
        captured["markdown_content"] = markdown_content
        captured["output_format"] = output_format
        captured["title"] = title
        captured["payload"] = payload
        return '{"role_name": "demo"}\n'

    result = scan_output_primary.render_and_write_scan_output(
        out_path=out_path,
        output_format="json",
        role_name="demo",
        description="desc",
        display_variables={"x": 1},
        requirements_display=["dep"],
        undocumented_default_filters=[],
        metadata={"features": {"tasks_scanned": 1}},
        template=None,
        dry_run=True,
        render_readme=fake_render_readme,
        render_final_output=fake_render_final_output,
        write_output=lambda _path, _content: "should-not-write",
    )

    assert result == '{"role_name": "demo"}\n'
    assert captured["markdown_content"] == ""
    assert captured["output_format"] == "json"
    assert captured["title"] == "demo"
    assert captured["payload"]["role_name"] == "demo"


def test_final_output_payload_contract_annotations_and_builder_shape():
    assert set(output.FinalOutputPayload.__annotations__) == {
        "role_name",
        "description",
        "variables",
        "requirements",
        "default_filters",
        "metadata",
    }

    render_hints = get_type_hints(output.render_final_output)
    assert "FinalOutputPayload" in str(render_hints["payload"])

    payload = output.build_final_output_payload(
        role_name="demo",
        description="desc",
        variables={"x": 1},
        requirements=["dep"],
        default_filters=[{"match": "x | default(1)"}],
        metadata={"features": {"tasks_scanned": 1}},
    )

    assert payload == {
        "role_name": "demo",
        "description": "desc",
        "variables": {"x": 1},
        "requirements": ["dep"],
        "default_filters": [{"match": "x | default(1)"}],
        "metadata": {"features": {"tasks_scanned": 1}},
    }


def test_render_and_write_scan_output_md_non_dry_run_writes(tmp_path):
    out_path = tmp_path / "README.md"
    captured = {}

    def fake_render_readme(*args, **kwargs):
        captured["render_readme_args"] = args
        captured["render_readme_kwargs"] = kwargs
        return "# Demo\n"

    def fake_render_final_output(markdown_content, output_format, title, payload=None):
        captured["render_final_output"] = {
            "markdown_content": markdown_content,
            "output_format": output_format,
            "title": title,
            "payload": payload,
        }
        return markdown_content

    def fake_write_output(path, content):
        captured["write_output"] = {
            "path": path,
            "content": content,
        }
        return str(path)

    result = scan_output_primary.render_and_write_scan_output(
        out_path=out_path,
        output_format="md",
        role_name="demo",
        description="desc",
        display_variables={"x": 1},
        requirements_display=["dep"],
        undocumented_default_filters=[{"match": "default"}],
        metadata={"features": {"tasks_scanned": 1}},
        template="template.md.j2",
        dry_run=False,
        render_readme=fake_render_readme,
        render_final_output=fake_render_final_output,
        write_output=fake_write_output,
    )

    assert result == str(out_path)
    assert captured["render_readme_args"][0] == str(out_path)
    assert captured["render_readme_args"][1] == "demo"
    assert captured["render_readme_kwargs"] == {"write": False}
    assert captured["render_final_output"]["markdown_content"] == "# Demo\n"
    assert captured["write_output"]["path"] == out_path
    assert captured["write_output"]["content"] == "# Demo\n"


def test_render_primary_scan_output_passes_payload_fields():
    captured = {}

    def fake_render_and_write_scan_output(**kwargs):
        captured.update(kwargs)
        return "result"

    result = scan_output_primary.render_primary_scan_output(
        out_path=Path("/tmp/README.md"),
        output_format="md",
        template="template.md.j2",
        dry_run=True,
        output_payload={
            "role_name": "demo",
            "description": "desc",
            "display_variables": {"x": 1},
            "requirements_display": ["dep"],
            "undocumented_default_filters": [],
            "metadata": {"features": {"tasks_scanned": 1}},
        },
        render_and_write_scan_output=fake_render_and_write_scan_output,
    )

    assert result == "result"
    assert captured["role_name"] == "demo"
    assert captured["description"] == "desc"
    assert captured["display_variables"] == {"x": 1}
    assert captured["requirements_display"] == ["dep"]
    assert captured["template"] == "template.md.j2"
    assert captured["dry_run"] is True


def test_scanner_wrapper_render_and_write_scan_output_delegates(monkeypatch):
    captured = {}

    def fake_render_and_write_scan_output(**kwargs):
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(
        scanner,
        "_scan_output_primary_render_and_write_scan_output",
        fake_render_and_write_scan_output,
    )

    result = scanner._render_and_write_scan_output(
        out_path=Path("/tmp/README.md"),
        output_format="md",
        role_name="demo",
        description="desc",
        display_variables={"x": 1},
        requirements_display=["dep"],
        undocumented_default_filters=[],
        metadata={"features": {}},
        template=None,
        dry_run=False,
    )

    assert result == "ok"
    assert captured["role_name"] == "demo"
    assert captured["render_readme"] is scanner.render_readme
    assert captured["render_final_output"] is scanner.render_final_output
    assert captured["write_output"] is scanner.write_output


def test_scanner_wrapper_render_primary_scan_output_delegates(monkeypatch):
    captured = {}

    def fake_render_primary_scan_output(**kwargs):
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(
        scanner,
        "_scan_output_primary_render_primary_scan_output",
        fake_render_primary_scan_output,
    )

    result = scanner._render_primary_scan_output(
        out_path=Path("/tmp/README.md"),
        output_format="md",
        template=None,
        dry_run=True,
        output_payload={
            "role_name": "demo",
            "description": "desc",
            "display_variables": {},
            "requirements_display": [],
            "undocumented_default_filters": [],
            "metadata": {},
        },
    )

    assert result == "ok"
    assert captured["output_payload"]["role_name"] == "demo"
    assert (
        captured["render_and_write_scan_output"]
        is scanner._render_and_write_scan_output
    )


def test_scanner_render_primary_alias_targets_canonical_scanner_io_module():
    assert (
        scanner._scan_output_primary_render_primary_scan_output.__module__
        == "prism.scanner_io.scan_output_primary"
    )


def test_scan_output_primary_compat_module_retired():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("prism.scanner_submodules.scan_output_primary")
