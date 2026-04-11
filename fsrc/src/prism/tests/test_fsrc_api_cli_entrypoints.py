"""Focused fsrc tests for top-level API and CLI entrypoint behavior."""

from __future__ import annotations

import importlib
import json
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "fsrc" / "src"


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


def _build_tiny_role(role_path: Path) -> None:
    (role_path / "defaults").mkdir(parents=True)
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "defaults" / "main.yml").write_text(
        "---\nexample_name: prism\n", encoding="utf-8"
    )
    (role_path / "tasks" / "main.yml").write_text(
        '---\n- name: Use a variable\n  debug:\n    msg: "{{ example_name }} {{ runtime_name }}"\n',
        encoding="utf-8",
    )
    (role_path / "README.md").write_text(
        "Role for API entrypoint tests.\n\nInput variable: {{ example_name }}\n",
        encoding="utf-8",
    )


def test_fsrc_api_run_scan_returns_structured_payload(tmp_path: Path) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert payload["role_name"] == "tiny_role"
    assert isinstance(payload["description"], str)
    assert payload["description"]
    assert "example_name" in payload["display_variables"]
    assert payload["display_variables"]["example_name"]["default"] == "prism"
    assert "requirements_display" in payload
    assert "undocumented_default_filters" in payload
    assert payload["metadata"]["features"]["task_files_scanned"] == 1


def test_fsrc_cli_main_runs_scan_and_emits_json(tmp_path: Path, capsys) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")
        exit_code = cli_module.main(["role", str(role_path), "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["role_name"] == "tiny_role"
    assert "example_name" in payload["display_variables"]


def test_fsrc_cli_main_returns_nonzero_on_failure(monkeypatch, capsys) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")

        def _raise_failure(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise RuntimeError("boom")

        monkeypatch.setattr(cli_module.api, "scan_role", _raise_failure)
        exit_code = cli_module.main(["role", "/tmp/role-that-does-not-matter"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "boom" in captured.err


def test_fsrc_api_run_scan_rejects_invalid_or_missing_role_path(tmp_path: Path) -> None:
    missing_role = tmp_path / "missing_role"

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as empty_error:
            api_module.run_scan("   ")
        with pytest.raises(errors_module.PrismRuntimeError) as missing_error:
            api_module.run_scan(str(missing_role))

    assert "role_path" in str(empty_error.value)
    assert "not exist" in str(missing_error.value)


def test_fsrc_cli_main_returns_nonzero_for_invalid_role_path(capsys) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")
        exit_code = cli_module.main(["role", "/tmp/prism-definitely-missing-role"])

    captured = capsys.readouterr()
    assert isinstance(exit_code, int)
    assert exit_code != 0
    assert "Error:" in captured.err


def test_fsrc_cli_main_parse_error_returns_nonzero_int(capsys) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")
        exit_code = cli_module.main([])

    captured = capsys.readouterr()
    assert isinstance(exit_code, int)
    assert exit_code != 0
    assert "usage:" in captured.err.lower()
