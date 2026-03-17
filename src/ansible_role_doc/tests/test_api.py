from pathlib import Path
import json
import shutil

import pytest

from ansible_role_doc import api, cli

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
    assert clone_calls["sparse_paths"] == [
        "roles/demo",
        "README.md",
        "Readme.md",
        "readme.md",
    ]
    assert scan_calls["role_path"].endswith("roles/demo")
    assert scan_calls["role_name_override"] == "demo-role"
    assert scan_calls["style_readme_path"] is None
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


def test_scan_repo_lightweight_readme_only_skips_clone(monkeypatch, tmp_path):
    fetched_style = tmp_path / "fetched-style.md"
    fetched_style.write_text("# Guide\n", encoding="utf-8")
    scan_calls: dict = {}

    monkeypatch.setattr(
        api,
        "_fetch_repo_directory_names",
        lambda *args, **kwargs: {"tasks", "defaults", "meta"},
    )
    monkeypatch.setattr(api, "_fetch_repo_file", lambda *args, **kwargs: fetched_style)
    monkeypatch.setattr(
        api,
        "_clone_repo",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("clone should not run in lightweight mode")
        ),
    )

    def fake_scan_role(role_path, **kwargs):
        scan_calls["role_path"] = role_path
        scan_calls.update(kwargs)
        return {"role_name": "demo-role", "metadata": {}}

    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_role_path="roles/demo",
        repo_style_readme_path="README.md",
        lightweight_readme_only=True,
    )

    assert payload["role_name"] == "demo-role"
    assert Path(scan_calls["role_path"]).name == "role-stub"
    assert scan_calls["style_readme_path"] == str(fetched_style.resolve())
    assert scan_calls["role_name_override"] == "demo-role"


def test_scan_repo_uses_shared_temp_root_and_normalizes_style_path(
    monkeypatch, tmp_path
):
    clone_calls: dict = {}

    monkeypatch.setattr(cli.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        api,
        "_fetch_repo_directory_names",
        lambda *args, **kwargs: {"tasks", "defaults", "meta"},
    )

    def fake_fetch_repo_file(repo_url, repo_path, destination, ref=None, timeout=60):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("# Guide\n", encoding="utf-8")
        return destination

    def fake_clone_repo(repo_url, destination, ref=None, timeout=60, sparse_paths=None):
        clone_calls["destination"] = destination
        role_dir = destination / "roles" / "demo"
        role_dir.mkdir(parents=True)

    def fake_scan_role(role_path, **kwargs):
        return {
            "role_name": "demo-role",
            "metadata": {
                "style_guide": {
                    "path": kwargs["style_readme_path"],
                }
            },
        }

    monkeypatch.setattr(api, "_fetch_repo_file", fake_fetch_repo_file)
    monkeypatch.setattr(api, "_clone_repo", fake_clone_repo)
    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_role_path="roles/demo",
        repo_style_readme_path="README.md",
    )

    assert clone_calls["destination"].parent.parent == tmp_path / "ansible-role-doc"
    assert payload["metadata"]["style_guide"]["path"] == "README.md"
    assert not (tmp_path / "ansible-role-doc").exists()


def test_scan_repo_resolves_case_variant_repo_style_readme(monkeypatch, tmp_path):
    calls: dict = {"requested_paths": []}

    def fake_fetch_repo_file(repo_url, repo_path, destination, ref=None, timeout=60):
        calls["requested_paths"].append(repo_path)
        if repo_path != "readme.md":
            return None
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("# Guide\n", encoding="utf-8")
        return destination

    def fake_clone_repo(repo_url, destination, ref=None, timeout=60, sparse_paths=None):
        calls["sparse_paths"] = sparse_paths
        role_dir = destination / "roles" / "demo"
        role_dir.mkdir(parents=True)

    def fake_scan_role(role_path, **kwargs):
        calls["style_readme_path"] = kwargs["style_readme_path"]
        return {
            "role_name": "demo-role",
            "metadata": {"style_guide": {"path": kwargs["style_readme_path"]}},
        }

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
        repo_role_path="roles/demo",
        repo_style_readme_path="README.md",
    )

    assert calls["requested_paths"] == ["README.md", "Readme.md", "readme.md"]
    assert calls["sparse_paths"] == ["roles/demo"]
    assert payload["metadata"]["style_guide"]["path"] == "readme.md"


def test_scan_repo_lightweight_requires_readme_when_missing(monkeypatch):
    monkeypatch.setattr(
        api,
        "_fetch_repo_directory_names",
        lambda *args, **kwargs: {"tasks", "defaults", "meta"},
    )
    monkeypatch.setattr(api, "_fetch_repo_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        api,
        "_clone_repo",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("clone should not run when API preflight is available")
        ),
    )

    with pytest.raises(FileNotFoundError, match="style README not found in repository"):
        api.scan_repo(
            "https://github.com/example/demo-role.git",
            repo_role_path="roles/demo",
            repo_style_readme_path="README.md",
            lightweight_readme_only=True,
        )


def test_scan_repo_lightweight_sparse_failure_does_not_fallback_full_clone(monkeypatch):
    clone_calls: dict = {"count": 0}

    monkeypatch.setattr(
        api, "_fetch_repo_directory_names", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(api, "_fetch_repo_file", lambda *args, **kwargs: None)

    def fake_clone_repo(
        repo_url,
        destination,
        ref=None,
        timeout=60,
        sparse_paths=None,
        allow_sparse_fallback_to_full=True,
    ):
        clone_calls["count"] += 1
        clone_calls["allow_sparse_fallback_to_full"] = allow_sparse_fallback_to_full
        raise RuntimeError("repository sparse checkout failed: boom")

    monkeypatch.setattr(api, "_clone_repo", fake_clone_repo)

    with pytest.raises(RuntimeError, match="repository sparse checkout failed"):
        api.scan_repo(
            "https://github.com/example/demo-role.git",
            repo_role_path="roles/demo",
            repo_style_readme_path="README.md",
            lightweight_readme_only=True,
        )

    assert clone_calls["count"] == 1
    assert clone_calls["allow_sparse_fallback_to_full"] is False


def test_scan_collection_returns_aggregated_payload(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "roles" / "role_b").mkdir(parents=True)
    (collection_root / "collections").mkdir(parents=True)

    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\nversion: 1.0.0\n",
        encoding="utf-8",
    )
    (collection_root / "collections" / "requirements.yml").write_text(
        "---\ncollections:\n  - name: community.general\n    version: 8.0.0\n",
        encoding="utf-8",
    )
    (collection_root / "roles" / "requirements.yml").write_text(
        "---\nroles:\n  - name: geerlingguy.mysql\n    version: 3.3.0\n",
        encoding="utf-8",
    )

    def fake_scan_role(role_path, **kwargs):
        return {
            "role_name": Path(role_path).name,
            "metadata": {"scanner_counters": {}},
        }

    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_collection(str(collection_root))

    assert payload["collection"]["metadata"]["namespace"] == "demo"
    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 2,
        "failed_roles": 0,
    }
    assert {entry["role"] for entry in payload["roles"]} == {"role_a", "role_b"}
    assert payload["dependencies"]["collections"] == [
        {
            "key": "community.general",
            "type": "collection",
            "name": "community.general",
            "src": None,
            "version": "8.0.0",
            "versions": ["8.0.0"],
            "sources": ["collections/requirements.yml"],
        }
    ]
    assert payload["dependencies"]["roles"] == [
        {
            "key": "geerlingguy.mysql",
            "type": "role",
            "name": "geerlingguy.mysql",
            "src": None,
            "version": "3.3.0",
            "versions": ["3.3.0"],
            "sources": ["roles/requirements.yml"],
        }
    ]


def test_scan_collection_tracks_dependency_conflicts(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "roles" / "role_b").mkdir(parents=True)
    (collection_root / "collections").mkdir(parents=True)

    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )
    (collection_root / "collections" / "requirements.yml").write_text(
        "---\ncollections:\n  - name: community.general\n    version: 8.0.0\n",
        encoding="utf-8",
    )
    (collection_root / "roles" / "role_a" / "meta").mkdir(parents=True)
    (collection_root / "roles" / "role_a" / "meta" / "requirements.yml").write_text(
        "---\n- name: community.general\n  type: collection\n  version: 7.5.0\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {"role_name": Path(role_path).name, "metadata": {}},
    )

    payload = api.scan_collection(str(collection_root))

    assert payload["dependencies"]["conflicts"] == [
        {
            "conflict": "version_conflict",
            "key": "community.general",
            "versions": ["7.5.0", "8.0.0"],
            "sources": [
                "collections/requirements.yml",
                "roles/role_a/meta/requirements.yml",
            ],
        }
    ]


def test_scan_collection_records_role_failures(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "roles" / "role_b").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )

    def fake_scan_role(role_path, **kwargs):
        if Path(role_path).name == "role_b":
            raise RuntimeError("boom")
        return {"role_name": "role_a", "metadata": {}}

    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_collection(str(collection_root))

    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 1,
        "failed_roles": 1,
    }
    assert payload["failures"] == [
        {
            "role": "role_b",
            "path": str((collection_root / "roles" / "role_b").resolve()),
            "error_type": "RuntimeError",
            "error": "boom",
        }
    ]
