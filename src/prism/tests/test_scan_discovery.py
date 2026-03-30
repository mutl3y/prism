"""Focused tests for scan discovery/path extraction and scanner wrappers."""

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


def test_scanner_load_meta_reads_role_metadata_file(tmp_path):
    role = tmp_path / "role"
    (role / "meta").mkdir(parents=True)
    (role / "meta" / "main.yml").write_text(
        "galaxy_info:\n  role_name: demo\n  description: Demo role\n",
        encoding="utf-8",
    )

    result = scanner.load_meta(str(role))

    assert result["galaxy_info"]["role_name"] == "demo"
    assert result["galaxy_info"]["description"] == "Demo role"


def test_scanner_load_requirements_reads_meta_requirements_file(tmp_path):
    role = tmp_path / "role"
    (role / "meta").mkdir(parents=True)
    (role / "meta" / "requirements.yml").write_text(
        "- ansible.posix\n- community.general\n",
        encoding="utf-8",
    )

    result = scanner.load_requirements(str(role))

    assert result == ["ansible.posix", "community.general"]


def test_scanner_load_requirements_normalizes_mapping_payload_to_empty_list(tmp_path):
    role = tmp_path / "role"
    (role / "meta").mkdir(parents=True)
    (role / "meta" / "requirements.yml").write_text(
        "collections:\n  - ansible.posix\n",
        encoding="utf-8",
    )

    result = scanner.load_requirements(str(role))

    assert result == []


def test_scanner_load_requirements_normalizes_scalar_payload_to_empty_list(tmp_path):
    role = tmp_path / "role"
    (role / "meta").mkdir(parents=True)
    (role / "meta" / "requirements.yml").write_text(
        "community.general\n",
        encoding="utf-8",
    )

    result = scanner.load_requirements(str(role))

    assert result == []


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


def test_scanner_wrapper_resolve_scan_identity_applies_override_when_meta_role_is_repo(
    tmp_path,
):
    role = tmp_path / "role"
    role.mkdir(parents=True)
    (role / "meta").mkdir(parents=True)
    (role / "meta" / "main.yml").write_text(
        "galaxy_info:\n  role_name: repo\n  description: meta description\n",
        encoding="utf-8",
    )

    resolved = scanner._resolve_scan_identity(str(role), "override_name")

    assert resolved[0] == role
    assert resolved[1]["galaxy_info"]["role_name"] == "repo"
    assert resolved[2] == "override_name"
    assert resolved[3] == "meta description"
