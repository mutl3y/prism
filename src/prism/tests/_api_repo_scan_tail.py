from pathlib import Path

import pytest

from prism import api


def test_role_dependency_key_uses_src_when_name_missing():
    assert api._role_dependency_key({"name": "", "src": "demo.role"}, 2) == "demo.role"


def test_scan_collection_raises_when_path_missing(tmp_path):
    missing_root = tmp_path / "missing_collection"
    with pytest.raises(FileNotFoundError, match="collection path not found"):
        api.scan_collection(str(missing_root))


def test_scan_collection_requires_galaxy_and_roles(tmp_path):
    bad_root = tmp_path / "bad_collection"
    bad_root.mkdir()
    with pytest.raises(
        FileNotFoundError,
        match="collection root must include galaxy.yml and roles/ directory",
    ):
        api.scan_collection(str(bad_root))


def test_normalize_repo_style_guide_path_ignores_non_dict_metadata():
    payload = {"metadata": "not-a-dict"}
    assert api._normalize_repo_style_guide_path(payload, "README.md") == payload


def test_scan_repo_lightweight_requires_explicit_repo_style_path(monkeypatch):
    monkeypatch.setattr(
        api, "_fetch_repo_directory_names", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(api, "_fetch_repo_file", lambda *args, **kwargs: None)

    with pytest.raises(
        FileNotFoundError,
        match="lightweight repo scan requires repo_style_readme_path",
    ):
        api.scan_repo(
            "https://github.com/example/demo-role.git",
            lightweight_readme_only=True,
        )


def test_scan_repo_lightweight_root_role_path_uses_sparse_defaults(monkeypatch):
    clone_calls: dict = {}
    scan_calls: dict = {}

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
        clone_calls["sparse_paths"] = list(sparse_paths or [])
        clone_calls["allow_sparse_fallback_to_full"] = allow_sparse_fallback_to_full
        for dirname in ("defaults", "tasks", "meta"):
            (destination / dirname).mkdir(parents=True, exist_ok=True)
        (destination / "README.md").write_text("# Style\n", encoding="utf-8")

    def fake_scan_role(role_path, **kwargs):
        scan_calls["role_path"] = role_path
        scan_calls["style_readme_path"] = kwargs.get("style_readme_path")
        return {"role_name": "demo-role", "metadata": {}}

    monkeypatch.setattr(api, "_clone_repo", fake_clone_repo)
    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_role_path=".",
        repo_style_readme_path="README.md",
        lightweight_readme_only=True,
    )

    assert payload["role_name"] == "demo-role"
    assert clone_calls["allow_sparse_fallback_to_full"] is False
    assert clone_calls["sparse_paths"][:3] == ["defaults", "tasks", "meta"]
    assert "README.md" in clone_calls["sparse_paths"]
    assert Path(scan_calls["role_path"]).name == "role-stub"
    assert scan_calls["style_readme_path"].endswith("/repo/README.md")


def test_scan_repo_uses_cloned_style_candidate_when_fetch_unavailable(
    monkeypatch, tmp_path
):
    scan_calls: dict = {}

    monkeypatch.setattr(
        api, "_fetch_repo_directory_names", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(api, "_fetch_repo_file", lambda *args, **kwargs: None)

    def fake_clone_repo(repo_url, destination, ref=None, timeout=60, sparse_paths=None):
        role_dir = destination / "roles" / "demo"
        role_dir.mkdir(parents=True)
        (destination / "README.md").write_text("# Style\n", encoding="utf-8")

    def fake_scan_role(role_path, **kwargs):
        scan_calls["style_readme_path"] = kwargs.get("style_readme_path")
        return {"role_name": "demo-role", "metadata": {}}

    monkeypatch.setattr(api, "_clone_repo", fake_clone_repo)
    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_role_path="roles/demo",
        repo_style_readme_path="README.md",
    )

    assert payload["role_name"] == "demo-role"
    assert scan_calls["style_readme_path"].endswith("/repo/README.md")
