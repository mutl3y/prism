from pathlib import Path
import builtins
import json
import shutil
import subprocess
import sys
import types

import pytest

from prism import scanner

HERE = Path(__file__).parent
ROLE_FIXTURES = HERE / "roles"
BASE_ROLE_FIXTURE = ROLE_FIXTURES / "base_mock_role"


def test_outputs_md_and_html(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out_md = tmp_path / "output.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from prism.cli import main;"
        "sys.exit(main(['{role}','-o','{out}','-v']))"
    ).format(src_dir=str(HERE.parent.parent), role=str(target), out=str(out_md))

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    assert res.returncode == 0
    assert out_md.exists()
    content = out_md.read_text(encoding="utf-8")
    # metadata from mock_role should be present
    assert "Galaxy Info" in content
    assert "license" in content.lower()

    # now HTML output
    out_html = tmp_path / "output.html"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from prism.cli import main;"
        "sys.exit(main(['{role}','-o','{out}','-f','html']))"
    ).format(src_dir=str(HERE.parent.parent), role=str(target), out=str(out_html))

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    assert res.returncode == 0
    assert out_html.exists()
    html = out_html.read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert "mock_role" in html


def test_run_scan_html_without_suffix_uses_html_extension(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "rendered"
    result = scanner.run_scan(str(target), output=str(out), output_format="html")

    assert result.endswith(".html")
    assert (tmp_path / "rendered.html").exists()


def test_run_scan_html_falls_back_when_markdown_import_fails(tmp_path, monkeypatch):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "markdown":
            raise ImportError("markdown unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    out = tmp_path / "fallback.html"
    result = scanner.run_scan(str(target), output=str(out), output_format="html")

    assert result.endswith("fallback.html")
    html = out.read_text(encoding="utf-8")
    assert "<pre>" in html
    assert "mock_role" in html


def test_run_scan_rejects_missing_style_or_compare_paths(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    with pytest.raises(FileNotFoundError, match="style README not found"):
        scanner.run_scan(
            str(target),
            output=str(tmp_path / "out.md"),
            style_readme_path=str(tmp_path / "missing-style.md"),
        )

    with pytest.raises(FileNotFoundError, match="comparison role path not found"):
        scanner.run_scan(
            str(target),
            output=str(tmp_path / "out.md"),
            compare_role_path=str(tmp_path / "missing-baseline"),
        )


def test_run_scan_rejects_missing_role_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="role path not found"):
        scanner.run_scan(
            str(tmp_path / "missing-role"), output=str(tmp_path / "out.md")
        )


def test_run_scan_html_uses_markdown_module_when_available(tmp_path, monkeypatch):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    fake_markdown = types.SimpleNamespace(
        markdown=lambda text, extensions: "<p>rendered by fake markdown</p>"
    )
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "markdown":
            return fake_markdown
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    out = tmp_path / "uses-markdown.html"
    scanner.run_scan(str(target), output=str(out), output_format="html")

    html = out.read_text(encoding="utf-8")
    assert "rendered by fake markdown" in html


def test_run_scan_json_output_uses_json_suffix_and_payload(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "scan-result"
    result = scanner.run_scan(str(target), output=str(out), output_format="json")

    json_path = tmp_path / "scan-result.json"
    assert result.endswith(".json")
    assert json_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["role_name"] == "mock_role"
    assert "variables" in payload
    assert "metadata" in payload


def test_run_scan_dry_run_returns_content_and_skips_write(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "dry-run.md"
    preview = scanner.run_scan(str(target), output=str(out), dry_run=True)

    assert not out.exists()
    assert "Role Variables" in preview


def test_run_scan_json_dry_run_returns_payload_without_write(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "dry-run-json"
    preview = scanner.run_scan(
        str(target), output=str(out), output_format="json", dry_run=True
    )

    assert not (tmp_path / "dry-run-json.json").exists()
    payload = json.loads(preview)
    assert payload["role_name"] == "mock_role"


def test_run_scan_pdf_output_uses_pdf_suffix_and_writes_bytes(tmp_path, monkeypatch):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    class _FakeHtml:
        def __init__(self, string):
            self.string = string

        def write_pdf(self):
            return b"%PDF-1.7\nfake\n"

    fake_weasyprint = types.SimpleNamespace(HTML=_FakeHtml)
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "weasyprint":
            return fake_weasyprint
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    out = tmp_path / "scan-pdf"
    result = scanner.run_scan(str(target), output=str(out), output_format="pdf")

    pdf_path = tmp_path / "scan-pdf.pdf"
    assert result.endswith(".pdf")
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_run_scan_pdf_raises_when_weasyprint_missing(tmp_path, monkeypatch):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "weasyprint":
            raise ImportError("missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="weasyprint"):
        scanner.run_scan(
            str(target),
            output=str(tmp_path / "missing.pdf"),
            output_format="pdf",
        )
