"""Focused tests for scan discovery/path extraction and scanner wrappers."""

from pathlib import Path

import pytest

from prism import scanner
from prism.scanner_extract import discovery as scan_discovery


def test_scan_discovery_iter_role_variable_map_candidates_prefers_main_then_fragments(
    tmp_path,
):
    role = tmp_path / "role"
    defaults = role / "defaults"
    fragments = defaults / "main"
    fragments.mkdir(parents=True)

    (defaults / "main.yml").write_text("a: 1\n", encoding="utf-8")
    (defaults / "main.yaml").write_text("b: 2\n", encoding="utf-8")
    (fragments / "10-a.yml").write_text("c: 3\n", encoding="utf-8")
    (fragments / "20-b.yaml").write_text("d: 4\n", encoding="utf-8")

    candidates = scan_discovery.iter_role_variable_map_candidates(role, "defaults")

    assert [path.relative_to(role).as_posix() for path in candidates] == [
        "defaults/main.yml",
        "defaults/main/10-a.yml",
        "defaults/main/20-b.yaml",
    ]


def test_scan_discovery_resolve_scan_identity_respects_role_name_override_when_repo(
    tmp_path,
):
    role = tmp_path / "repo"
    role.mkdir(parents=True)

    meta = {
        "galaxy_info": {
            "role_name": "repo",
            "description": "Demo role",
        }
    }

    resolved = scan_discovery.resolve_scan_identity(
        str(role),
        "custom_name",
        load_meta_fn=lambda _: meta,
    )

    assert resolved[0] == role
    assert resolved[1] == meta
    assert resolved[2] == "custom_name"
    assert resolved[3] == "Demo role"


def test_scan_discovery_resolve_scan_identity_raises_for_missing_role_path(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError, match="role path not found"):
        scan_discovery.resolve_scan_identity(
            str(missing),
            None,
            load_meta_fn=lambda _: {},
        )


def test_scanner_wrapper_load_meta_re_exports_canonical_implementation():
    assert scanner.load_meta is scanner._scan_discovery_load_meta


def test_scanner_wrapper_load_requirements_re_exports_canonical_implementation():
    assert scanner.load_requirements is scanner._scan_discovery_load_requirements


def test_scanner_wrapper_load_variables_delegates(monkeypatch):
    captured = {}

    def fake_load_variables(
        role_path,
        *,
        include_vars_main,
        exclude_paths,
        collect_include_vars_files,
    ):
        captured["role_path"] = role_path
        captured["include_vars_main"] = include_vars_main
        captured["exclude_paths"] = exclude_paths
        captured["include_vars_callback"] = collect_include_vars_files
        return {"example": "value"}

    monkeypatch.setattr(scanner, "_scan_discovery_load_variables", fake_load_variables)

    result = scanner.load_variables(
        "/tmp/demo-role",
        include_vars_main=False,
        exclude_paths=["tasks/nested/*"],
    )

    assert result == {"example": "value"}
    assert captured["role_path"] == "/tmp/demo-role"
    assert captured["include_vars_main"] is False
    assert captured["exclude_paths"] == ["tasks/nested/*"]
    assert callable(captured["include_vars_callback"])


def test_scanner_wrapper_resolve_scan_identity_delegates(monkeypatch):
    captured = {}

    def fake_resolve_scan_identity(role_path, role_name_override, *, load_meta_fn):
        captured["role_path"] = role_path
        captured["role_name_override"] = role_name_override
        captured["load_meta_fn"] = load_meta_fn
        return Path("/tmp/demo"), {"galaxy_info": {}}, "demo", "desc"

    monkeypatch.setattr(
        scanner,
        "_scan_discovery_resolve_scan_identity",
        fake_resolve_scan_identity,
    )

    result = scanner._resolve_scan_identity("/tmp/demo", "override")

    assert result == (Path("/tmp/demo"), {"galaxy_info": {}}, "demo", "desc")
    assert captured["role_path"] == "/tmp/demo"
    assert captured["role_name_override"] == "override"
    assert captured["load_meta_fn"] is scanner.load_meta
