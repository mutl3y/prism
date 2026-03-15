from pathlib import Path
import json
import shutil

import pytest

from ansible_role_doc import api

HERE = Path(__file__).parent
ROLE_FIXTURES = HERE / "roles"
BASE_ROLE_FIXTURE = ROLE_FIXTURES / "base_mock_role"


@pytest.fixture(autouse=True)
def _disable_remote_github_api(monkeypatch):
    monkeypatch.setattr(
        api, "_fetch_repo_directory_names", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(api, "_fetch_repo_file", lambda *args, **kwargs: None)


def test_scan_role_returns_payload_dict(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    payload = api.scan_role(str(target))

    assert payload["role_name"] == "mock_role"
    assert "variables" in payload
    assert "metadata" in payload


def test_scan_role_forwards_library_options(monkeypatch):
    calls: dict = {}

    def fake_run_scan(role_path, **kwargs):
        calls["role_path"] = role_path
        calls.update(kwargs)
        return json.dumps({"role_name": "mock_role", "metadata": {}})

    monkeypatch.setattr(api, "run_scan", fake_run_scan)

    payload = api.scan_role(
        "/tmp/mock_role",
        exclude_path_patterns=["tests/**"],
        style_source_path="/tmp/style.md",
        policy_config_path="/tmp/policy.yml",
        keep_unknown_style_sections=False,
    )

    assert payload["role_name"] == "mock_role"
    assert calls["role_path"] == "/tmp/mock_role"
    assert calls["output"] == "scan.json"
    assert calls["output_format"] == "json"
    assert calls["dry_run"] is True
    assert calls["exclude_path_patterns"] == ["tests/**"]
    assert calls["style_source_path"] == "/tmp/style.md"
    assert calls["policy_config_path"] == "/tmp/policy.yml"
    assert calls["keep_unknown_style_sections"] is False


def test_scan_repo_returns_payload_dict(monkeypatch, tmp_path):
    def fake_clone_repo(repo_url, destination, ref=None, timeout=60, sparse_paths=None):
        role_dir = destination / "roles" / "demo"
        role_dir.mkdir(parents=True)
        (role_dir / "tasks").mkdir()
        (role_dir / "tasks" / "main.yml").write_text(
            "---\n- name: demo\n  debug:\n    msg: ok\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(api, "_clone_repo", fake_clone_repo)

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_role_path="roles/demo",
    )

    assert payload["role_name"] == "demo-role"
    assert "metadata" in payload


def test_scan_repo_forwards_repo_options(monkeypatch):
    clone_calls: dict = {}
    scan_calls: dict = {}

    def fake_clone_repo(repo_url, destination, ref=None, timeout=60, sparse_paths=None):
        clone_calls["repo_url"] = repo_url
        clone_calls["destination"] = destination
        clone_calls["ref"] = ref
        clone_calls["timeout"] = timeout
        clone_calls["sparse_paths"] = sparse_paths
        role_dir = destination / "roles" / "demo"
        role_dir.mkdir(parents=True)

    def fake_scan_role(role_path, **kwargs):
        scan_calls["role_path"] = role_path
        scan_calls.update(kwargs)
        return {"role_name": "demo", "metadata": {}}

    monkeypatch.setattr(api, "_clone_repo", fake_clone_repo)
    monkeypatch.setattr(api, "scan_role", fake_scan_role)
    monkeypatch.setattr(api, "_fetch_repo_file", lambda *args, **kwargs: None)

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_ref="main",
        repo_role_path="roles/demo",
        repo_timeout=5,
        repo_style_readme_path="README.md",
        exclude_path_patterns=["tests/**"],
        style_source_path="/tmp/style.md",
        policy_config_path="/tmp/policy.yml",
    )

    assert payload["role_name"] == "demo"
    assert clone_calls["repo_url"] == "https://github.com/example/demo-role.git"
    assert clone_calls["ref"] == "main"
    assert clone_calls["timeout"] == 5
    assert clone_calls["sparse_paths"] == ["roles/demo", "README.md"]
    assert scan_calls["role_path"].endswith("roles/demo")
    assert scan_calls["role_name_override"] == "demo-role"
    assert scan_calls["style_readme_path"].endswith("README.md")
    assert scan_calls["exclude_path_patterns"] == ["tests/**"]
    assert scan_calls["style_source_path"] == "/tmp/style.md"
    assert scan_calls["policy_config_path"] == "/tmp/policy.yml"


def test_scan_repo_uses_fetched_style_readme_when_available(monkeypatch, tmp_path):
    clone_calls: dict = {}
    scan_calls: dict = {}
    fetched_style = tmp_path / "fetched-style.md"
    fetched_style.write_text("# Guide\n", encoding="utf-8")

    def fake_fetch_repo_file(repo_url, repo_path, destination, ref=None, timeout=60):
        clone_calls["fetched_repo_path"] = repo_path
        clone_calls["fetch_destination"] = destination
        return fetched_style

    def fake_clone_repo(repo_url, destination, ref=None, timeout=60, sparse_paths=None):
        clone_calls["sparse_paths"] = sparse_paths
        role_dir = destination / "roles" / "demo"
        role_dir.mkdir(parents=True)

    def fake_scan_role(role_path, **kwargs):
        scan_calls["role_path"] = role_path
        scan_calls.update(kwargs)
        return {"role_name": "demo", "metadata": {}}

    monkeypatch.setattr(
        api,
        "_fetch_repo_directory_names",
        lambda *args, **kwargs: {"tasks", "defaults", "meta"},
    )
    monkeypatch.setattr(api, "_fetch_repo_file", fake_fetch_repo_file)
    monkeypatch.setattr(api, "_clone_repo", fake_clone_repo)
    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_ref="main",
        repo_role_path="roles/demo",
        repo_style_readme_path="README.md",
    )

    assert payload["role_name"] == "demo"
    assert clone_calls["fetched_repo_path"] == "README.md"
    assert clone_calls["sparse_paths"] == ["roles/demo"]
    assert scan_calls["style_readme_path"] == str(fetched_style.resolve())


def test_scan_repo_rejects_non_role_directory_listing(monkeypatch):
    monkeypatch.setattr(
        api,
        "_fetch_repo_directory_names",
        lambda *args, **kwargs: {"docs", ".github"},
    )
    monkeypatch.setattr(
        api,
        "_clone_repo",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("clone should not run for non-role repos")
        ),
    )

    with pytest.raises(
        FileNotFoundError, match="repository path does not look like an Ansible role"
    ):
        api.scan_repo("https://github.com/example/not-a-role.git")


def test_scan_repo_raises_for_missing_repo_role_path(monkeypatch):
    def fake_clone_repo(repo_url, destination, ref=None, timeout=60, sparse_paths=None):
        destination.mkdir(parents=True)

    monkeypatch.setattr(api, "_clone_repo", fake_clone_repo)

    with pytest.raises(
        FileNotFoundError, match="role path not found in cloned repository"
    ):
        api.scan_repo(
            "https://github.com/example/demo-role.git",
            repo_role_path="roles/missing",
        )
