import json
import inspect
from pathlib import Path
import shutil

import pytest

from prism import api, cli, repo_services
from prism import errors as prism_errors

HERE = Path(__file__).parent
ROLE_FIXTURES = HERE / "roles"
BASE_ROLE_FIXTURE = ROLE_FIXTURES / "base_mock_role"


def _write_guide_file(path: Path) -> Path:
    """Write a simple markdown guide fixture and return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Guide\n", encoding="utf-8")
    return path


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


def test_api_and_cli_share_repo_service_helper_bindings(monkeypatch):
    monkeypatch.setattr(
        api,
        "_fetch_repo_directory_names",
        repo_services._fetch_repo_directory_names,
    )
    monkeypatch.setattr(api, "_fetch_repo_file", repo_services._fetch_repo_file)

    assert api._clone_repo is repo_services._clone_repo
    assert api._fetch_repo_directory_names is repo_services._fetch_repo_directory_names
    assert api._fetch_repo_file is repo_services._fetch_repo_file

    assert api._repo_scan_workspace is repo_services._repo_scan_workspace
    assert api._repo_path_looks_like_role is repo_services._repo_path_looks_like_role
    assert api._repo_name_from_url is repo_services._repo_name_from_url
    assert (
        api._build_repo_style_readme_candidates
        is repo_services._build_repo_style_readme_candidates
    )
    assert api._build_sparse_clone_paths is repo_services._build_sparse_clone_paths
    assert api._prepare_repo_scan_inputs is repo_services._prepare_repo_scan_inputs
    assert (
        api._resolve_style_readme_candidate
        is repo_services._resolve_style_readme_candidate
    )
    assert api._checkout_repo_scan_role is repo_services._checkout_repo_scan_role
    assert (
        api._build_lightweight_sparse_clone_paths
        is repo_services._build_lightweight_sparse_clone_paths
    )
    assert (
        api._checkout_repo_lightweight_style_readme
        is repo_services._checkout_repo_lightweight_style_readme
    )

    assert cli._repo_scan_workspace is repo_services._repo_scan_workspace
    assert cli._repo_path_looks_like_role is repo_services._repo_path_looks_like_role
    assert cli._repo_name_from_url is repo_services._repo_name_from_url
    assert (
        cli._build_repo_style_readme_candidates
        is repo_services._build_repo_style_readme_candidates
    )
    assert cli._build_sparse_clone_paths is repo_services._build_sparse_clone_paths
    assert cli._prepare_repo_scan_inputs is repo_services._prepare_repo_scan_inputs
    assert (
        cli._resolve_style_readme_candidate
        is repo_services._resolve_style_readme_candidate
    )
    assert cli._checkout_repo_scan_role is repo_services._checkout_repo_scan_role
    assert (
        cli._checkout_repo_lightweight_style_readme
        is repo_services._checkout_repo_lightweight_style_readme
    )


def test_api_imports_repo_service_public_aliases_only() -> None:
    api_source = inspect.getsource(api)

    assert "from .repo_services import _" not in api_source


def test_api_uses_repo_scan_facade_binding() -> None:
    assert api._repo_scan_facade is repo_services.repo_scan_facade


def test_scan_repo_uses_shared_checkout_orchestration(monkeypatch, tmp_path):
    calls: dict = {}
    role_path = tmp_path / "repo" / "roles" / "demo"
    role_path.mkdir(parents=True)

    def fake_checkout_repo_scan_role(
        repo_url,
        *,
        workspace,
        repo_role_path,
        repo_style_readme_path,
        style_readme_path,
        repo_ref,
        repo_timeout,
        prepare_repo_scan_inputs,
        fetch_repo_directory_names,
        repo_path_looks_like_role,
        fetch_repo_file,
        clone_repo,
        build_sparse_clone_paths,
        resolve_style_readme_candidate,
    ):
        calls["repo_url"] = repo_url
        calls["repo_role_path"] = repo_role_path
        calls["repo_style_readme_path"] = repo_style_readme_path
        calls["style_readme_path"] = style_readme_path
        calls["repo_ref"] = repo_ref
        calls["repo_timeout"] = repo_timeout
        return repo_services._RepoCheckoutResult(
            checkout_dir=tmp_path / "repo",
            role_path=role_path,
            effective_style_readme_path=None,
            resolved_repo_style_readme_path="README.md",
            style_candidates=["README.md"],
            fetched_repo_style_readme_path=None,
        )

    def fake_scan_role(scanned_role_path, **kwargs):
        calls["scanned_role_path"] = scanned_role_path
        calls["scanned_style_readme_path"] = kwargs.get("style_readme_path")
        return {
            "role_name": "demo",
            "metadata": {"style_guide": {"path": kwargs.get("style_readme_path")}},
        }

    monkeypatch.setattr(api, "_checkout_repo_scan_role", fake_checkout_repo_scan_role)
    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_ref="main",
        repo_role_path="roles/demo",
        repo_timeout=12,
        repo_style_readme_path="README.md",
    )

    assert payload["role_name"] == "demo"
    assert calls["repo_url"] == "https://github.com/example/demo-role.git"
    assert calls["repo_role_path"] == "roles/demo"
    assert calls["repo_style_readme_path"] == "README.md"
    assert calls["repo_ref"] == "main"
    assert calls["repo_timeout"] == 12
    assert calls["scanned_role_path"] == str(role_path)
    assert calls["scanned_style_readme_path"] is None


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
        fail_on_unconstrained_dynamic_includes=True,
        ignore_unresolved_internal_underscore_references=False,
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
    assert calls["fail_on_unconstrained_dynamic_includes"] is True
    assert calls["ignore_unresolved_internal_underscore_references"] is False
    assert calls["keep_unknown_style_sections"] is False


def test_scan_role_classifies_invalid_json_payload(monkeypatch):
    monkeypatch.setattr(api, "run_scan", lambda *args, **kwargs: "{not-json")

    with pytest.raises(RuntimeError, match="SCAN_ROLE_PAYLOAD_JSON_INVALID"):
        api.scan_role("/tmp/mock_role")


def test_scan_role_classifies_non_mapping_json_payload(monkeypatch):
    monkeypatch.setattr(api, "run_scan", lambda *args, **kwargs: "[]")

    with pytest.raises(RuntimeError, match="SCAN_ROLE_PAYLOAD_TYPE_INVALID"):
        api.scan_role("/tmp/mock_role")


def test_scan_role_classifies_invalid_metadata_shape(monkeypatch):
    monkeypatch.setattr(
        api,
        "run_scan",
        lambda *args, **kwargs: json.dumps({"metadata": []}),
    )

    with pytest.raises(RuntimeError, match="SCAN_ROLE_PAYLOAD_SHAPE_INVALID"):
        api.scan_role("/tmp/mock_role")


def test_scan_role_accepts_in_memory_payload_without_json_roundtrip(monkeypatch):
    expected_payload = {"role_name": "mock_role", "metadata": {"ok": True}}
    monkeypatch.setattr(api, "run_scan", lambda *args, **kwargs: expected_payload)

    payload = api.scan_role("/tmp/mock_role")

    assert payload == expected_payload


def test_collection_role_failure_uses_typed_runtime_error_code():
    exc = prism_errors.PrismRuntimeError(
        code=prism_errors.ROLE_METADATA_YAML_INVALID,
        category=prism_errors.ERROR_CATEGORY_CONFIG,
        message="meta parse failed",
    )

    error_code, error_category, error_detail_code = api._collection_role_failure_details(exc)

    assert error_code == prism_errors.ROLE_METADATA_YAML_INVALID
    assert error_category == prism_errors.ERROR_CATEGORY_CONFIG
    assert error_detail_code == prism_errors.ROLE_METADATA_YAML_INVALID


def test_scan_role_forwards_failure_policy_contract(monkeypatch):
    calls: dict[str, object] = {}

    def fake_run_scan(*args, **kwargs):
        calls.update(kwargs)
        return {"role_name": "demo", "metadata": {}}

    monkeypatch.setattr(api, "run_scan", fake_run_scan)

    policy = prism_errors.FailurePolicy(strict=False)
    payload = api.scan_role("/tmp/mock_role", failure_policy=policy)

    assert payload["role_name"] == "demo"
    assert calls["failure_policy"] == policy


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
    _write_guide_file(fetched_style)

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
    _write_guide_file(fetched_style)
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


def test_scan_repo_lightweight_uses_shared_checkout_orchestration(
    monkeypatch, tmp_path
):
    calls: dict = {}
    role_stub = tmp_path / "role-stub"
    role_stub.mkdir(parents=True)
    fetched_style = tmp_path / "style.md"
    _write_guide_file(fetched_style)

    def fake_checkout_repo_lightweight_style_readme(
        repo_url,
        *,
        workspace,
        repo_role_path,
        repo_style_readme_path,
        repo_ref,
        repo_timeout,
        prepare_repo_scan_inputs,
        fetch_repo_directory_names,
        repo_path_looks_like_role,
        fetch_repo_file,
        clone_repo,
        build_lightweight_sparse_clone_paths,
        resolve_style_readme_candidate,
    ):
        calls["repo_url"] = repo_url
        calls["repo_role_path"] = repo_role_path
        calls["repo_style_readme_path"] = repo_style_readme_path
        calls["repo_ref"] = repo_ref
        calls["repo_timeout"] = repo_timeout
        return repo_services._RepoLightweightCheckoutResult(
            role_stub_dir=role_stub,
            effective_style_readme_path=str(fetched_style.resolve()),
            resolved_repo_style_readme_path="README.md",
        )

    def fake_scan_role(role_path, **kwargs):
        calls["scanned_role_path"] = role_path
        calls["scanned_style_readme_path"] = kwargs.get("style_readme_path")
        return {
            "role_name": "demo-role",
            "metadata": {
                "style_guide": {
                    "path": kwargs.get("style_readme_path"),
                }
            },
        }

    monkeypatch.setattr(
        api,
        "_checkout_repo_lightweight_style_readme",
        fake_checkout_repo_lightweight_style_readme,
    )
    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_ref="main",
        repo_role_path="roles/demo",
        repo_timeout=7,
        repo_style_readme_path="README.md",
        lightweight_readme_only=True,
    )

    assert payload["role_name"] == "demo-role"
    assert calls["repo_url"] == "https://github.com/example/demo-role.git"
    assert calls["repo_role_path"] == "roles/demo"
    assert calls["repo_style_readme_path"] == "README.md"
    assert calls["repo_ref"] == "main"
    assert calls["repo_timeout"] == 7
    assert calls["scanned_role_path"] == str(role_stub)
    assert calls["scanned_style_readme_path"] == str(fetched_style.resolve())
    assert payload["metadata"]["style_guide"]["path"] == "README.md"


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
        return _write_guide_file(destination)

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

    assert clone_calls["destination"].parent.parent == tmp_path / "prism"
    assert payload["metadata"]["style_guide"]["path"] == "README.md"
    assert not (tmp_path / "prism").exists()


def test_scan_repo_resolves_case_variant_repo_style_readme(monkeypatch, tmp_path):
    calls: dict = {"requested_paths": []}

    def fake_fetch_repo_file(repo_url, repo_path, destination, ref=None, timeout=60):
        calls["requested_paths"].append(repo_path)
        if repo_path != "readme.md":
            return None
        return _write_guide_file(destination)

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


def test_scan_repo_sets_logical_scanner_report_relpath(monkeypatch, tmp_path):
    role_path = tmp_path / "repo" / "roles" / "demo"
    role_path.mkdir(parents=True)

    def fake_checkout_repo_scan_role(*args, **kwargs):
        return repo_services._RepoCheckoutResult(
            checkout_dir=tmp_path / "repo",
            role_path=role_path,
            effective_style_readme_path=str((tmp_path / "STYLE.md").resolve()),
            resolved_repo_style_readme_path="readme.md",
            style_candidates=["README.md", "Readme.md", "readme.md"],
            fetched_repo_style_readme_path=None,
        )

    def fake_scan_role(role_path, **kwargs):
        return {
            "role_name": "demo-role",
            "metadata": {
                "style_guide": {
                    "path": kwargs.get("style_readme_path"),
                }
            },
        }

    monkeypatch.setattr(api, "_checkout_repo_scan_role", fake_checkout_repo_scan_role)
    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_role_path="roles/demo",
        repo_style_readme_path="README.md",
        concise_readme=True,
        scanner_report_output="reports/repo.scan.md",
    )

    assert payload["metadata"]["style_guide"]["path"] == "readme.md"
    assert payload["metadata"]["scanner_report_relpath"] == "reports/repo.scan.md"


def test_scan_repo_normalizes_windows_scanner_report_relpath(monkeypatch, tmp_path):
    role_path = tmp_path / "repo" / "roles" / "demo"
    role_path.mkdir(parents=True)

    def fake_checkout_repo_scan_role(*args, **kwargs):
        return repo_services._RepoCheckoutResult(
            checkout_dir=tmp_path / "repo",
            role_path=role_path,
            effective_style_readme_path=str((tmp_path / "STYLE.md").resolve()),
            resolved_repo_style_readme_path="readme.md",
            style_candidates=["README.md", "Readme.md", "readme.md"],
            fetched_repo_style_readme_path=None,
        )

    def fake_scan_role(role_path, **kwargs):
        return {
            "role_name": "demo-role",
            "metadata": {
                "style_guide": {
                    "path": kwargs.get("style_readme_path"),
                }
            },
        }

    monkeypatch.setattr(api, "_checkout_repo_scan_role", fake_checkout_repo_scan_role)
    monkeypatch.setattr(api, "scan_role", fake_scan_role)
    monkeypatch.setattr(
        repo_services.os.path,
        "relpath",
        lambda *args, **kwargs: r"..\reports\nested\repo.scan.md",
    )

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_role_path="roles/demo",
        repo_style_readme_path="README.md",
        concise_readme=True,
        scanner_report_output=r"reports\nested\repo.scan.md",
    )

    assert payload["metadata"]["style_guide"]["path"] == "readme.md"
    assert (
        payload["metadata"]["scanner_report_relpath"]
        == "../reports/nested/repo.scan.md"
    )


def test_scan_repo_lightweight_normalizes_windows_scanner_report_relpath(
    monkeypatch, tmp_path
):
    role_stub = tmp_path / "role-stub"
    role_stub.mkdir(parents=True)

    def fake_checkout_repo_lightweight_style_readme(*args, **kwargs):
        return repo_services._RepoLightweightCheckoutResult(
            role_stub_dir=role_stub,
            effective_style_readme_path=str((tmp_path / "STYLE.md").resolve()),
            resolved_repo_style_readme_path="readme.md",
        )

    def fake_scan_role(role_path, **kwargs):
        return {
            "role_name": "demo-role",
            "metadata": {
                "style_guide": {
                    "path": kwargs.get("style_readme_path"),
                }
            },
        }

    monkeypatch.setattr(
        api,
        "_checkout_repo_lightweight_style_readme",
        fake_checkout_repo_lightweight_style_readme,
    )
    monkeypatch.setattr(api, "scan_role", fake_scan_role)
    monkeypatch.setattr(
        repo_services.os.path,
        "relpath",
        lambda *args, **kwargs: r"..\reports\nested\repo.scan.md",
    )

    payload = api.scan_repo(
        "https://github.com/example/demo-role.git",
        repo_role_path="roles/demo",
        repo_style_readme_path="README.md",
        concise_readme=True,
        scanner_report_output=r"reports\nested\repo.scan.md",
        lightweight_readme_only=True,
    )

    assert payload["metadata"]["style_guide"]["path"] == "readme.md"
    assert (
        payload["metadata"]["scanner_report_relpath"]
        == "../reports/nested/repo.scan.md"
    )


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
    assert payload["plugin_catalog"]["schema_version"] == 1
    assert payload["plugin_catalog"]["summary"] == {
        "total_plugins": 0,
        "types_present": [],
        "files_scanned": 0,
        "files_failed": 0,
    }
    assert payload["plugin_catalog"]["failures"] == []
    assert payload["plugin_catalog"]["by_type"] == {
        "filter": [],
        "modules": [],
        "lookup": [],
        "inventory": [],
        "callback": [],
        "connection": [],
        "strategy": [],
        "test": [],
        "doc_fragments": [],
        "module_utils": [],
    }


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
            raise ValueError("invalid role content")
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
            "error_code": "role_content_invalid",
            "error_category": "validation",
            "error_type": "ValueError",
            "error": "invalid role content",
        }
    ]
    assert "traceback" not in payload["failures"][0]
    assert sorted(payload["plugin_catalog"]["by_type"].keys()) == [
        "callback",
        "connection",
        "doc_fragments",
        "filter",
        "inventory",
        "lookup",
        "module_utils",
        "modules",
        "strategy",
        "test",
    ]


@pytest.mark.parametrize(
    ("raised", "expected_code", "expected_category", "expected_detail_code"),
    [
        (
            RuntimeError("scanner system failure"),
            "role_scan_runtime_error",
            "runtime",
            None,
        ),
        (
            prism_errors.PrismRuntimeError(
                code=prism_errors.ROLE_METADATA_YAML_INVALID,
                category=prism_errors.ERROR_CATEGORY_CONFIG,
                message="role metadata parse failed",
            ),
            "role_metadata_yaml_invalid",
            "config",
            "role_metadata_yaml_invalid",
        ),
        (
            OSError("permission denied"),
            "role_content_io_error",
            "io",
            None,
        ),
        (
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
            "role_content_encoding_invalid",
            "io",
            None,
        ),
        (
            json.JSONDecodeError("bad json", "{", 0),
            "role_content_json_invalid",
            "parser",
            None,
        ),
        (
            api.yaml.YAMLError("bad yaml"),
            "role_content_yaml_invalid",
            "parser",
            None,
        ),
    ],
)
def test_scan_collection_classifies_recoverable_role_failures_without_abort(
    monkeypatch,
    tmp_path,
    raised,
    expected_code,
    expected_category,
    expected_detail_code,
):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "roles" / "role_b").mkdir(parents=True)
    (collection_root / "roles" / "role_c").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )

    def fake_scan_role(role_path, **kwargs):
        if Path(role_path).name == "role_b":
            raise raised
        return {"role_name": Path(role_path).name, "metadata": {}}

    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_collection(str(collection_root))

    assert payload["summary"] == {
        "total_roles": 3,
        "scanned_roles": 2,
        "failed_roles": 1,
    }
    assert [entry["role"] for entry in payload["roles"]] == ["role_a", "role_c"]

    failure = payload["failures"][0]
    assert failure["role"] == "role_b"
    assert failure["error_code"] == expected_code
    assert failure["error_category"] == expected_category
    assert failure.get("error_detail_code") == expected_detail_code


def test_scan_collection_can_include_traceback_when_requested(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "roles" / "role_b").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )

    def fake_scan_role(role_path, **kwargs):
        if Path(role_path).name == "role_b":
            raise ValueError("bad vars schema")
        return {"role_name": "role_a", "metadata": {}}

    monkeypatch.setattr(api, "scan_role", fake_scan_role)

    payload = api.scan_collection(str(collection_root), include_traceback=True)

    assert payload["summary"]["failed_roles"] == 1
    failure = payload["failures"][0]
    assert failure["error_code"] == "role_content_invalid"
    assert failure["error_type"] == "ValueError"
    assert "ValueError: bad vars schema" in failure["traceback"]


def test_scan_collection_can_include_rendered_readme(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {
            "role_name": Path(role_path).name,
            "description": "",
            "variables": {},
            "requirements": [],
            "default_filters": [],
            "metadata": {},
        },
    )

    def fail_run_scan(*args, **kwargs):
        raise AssertionError(
            "run_scan should not be called for collection README rendering"
        )

    monkeypatch.setattr(api, "run_scan", fail_run_scan)

    render_calls = {"count": 0}

    def fake_render_readme(
        output,
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        template=None,
        metadata=None,
        write=True,
    ):
        render_calls["count"] += 1
        assert output == "README.md"
        assert role_name == "role_a"
        assert write is False
        return f"# {role_name}\n"

    monkeypatch.setattr(api, "render_readme", fake_render_readme)

    payload = api.scan_collection(str(collection_root), include_rendered_readme=True)

    assert render_calls["count"] == 1
    assert payload["roles"][0]["rendered_readme"] == "# role_a\n"


def test_scan_role_forwards_detailed_catalog(monkeypatch, tmp_path):
    role_path = tmp_path / "role"
    role_path.mkdir()

    def fake_run_scan(role_path_arg, output, output_format, **kwargs):
        assert kwargs["detailed_catalog"] is True
        return "{}"

    monkeypatch.setattr(api, "run_scan", fake_run_scan)
    payload = api.scan_role(str(role_path), detailed_catalog=True)
    assert payload == {}


def test_scan_collection_extracts_filter_plugins_into_catalog(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "plugins" / "filter").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )
    (collection_root / "plugins" / "filter" / "network.py").write_text(
        '"""Network filter helpers."""\n\n'
        "class FilterModule:\n"
        "    def filters(self):\n"
        "        return {\n"
        '            "cidr_contains": cidr_contains,\n'
        '            "ip_version": ip_version,\n'
        "        }\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {"role_name": Path(role_path).name, "metadata": {}},
    )

    payload = api.scan_collection(str(collection_root))
    catalog = payload["plugin_catalog"]

    assert catalog["summary"]["files_scanned"] == 1
    assert catalog["summary"]["files_failed"] == 0
    assert catalog["summary"]["total_plugins"] == 1
    assert catalog["summary"]["types_present"] == ["filter"]
    assert len(catalog["by_type"]["filter"]) == 1

    record = catalog["by_type"]["filter"][0]
    assert record["name"] == "network"
    assert record["relative_path"] == "plugins/filter/network.py"
    assert record["symbols"] == ["cidr_contains", "ip_version"]
    assert record["doc_source"] == "module_docstring"
    assert record["confidence"] == "high"
    assert record["extraction"]["method"] == "ast"
    assert catalog["failures"] == []


def test_scan_collection_filter_summary_prefers_function_docstring(
    monkeypatch, tmp_path
):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "plugins" / "filter").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )
    (collection_root / "plugins" / "filter" / "network.py").write_text(
        '"""Fallback module docstring."""\n\n'
        "def cidr_contains(value):\n"
        '    """Check whether an IP belongs to the supplied CIDR block."""\n'
        "    return value\n\n"
        "class FilterModule:\n"
        "    def filters(self):\n"
        "        return {\n"
        '            "cidr_contains": cidr_contains,\n'
        "        }\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {"role_name": Path(role_path).name, "metadata": {}},
    )

    payload = api.scan_collection(str(collection_root))
    record = payload["plugin_catalog"]["by_type"]["filter"][0]

    assert (
        record["summary"] == "Check whether an IP belongs to the supplied CIDR block."
    )
    assert record["doc_source"] == "filter_function_docstring"


def test_scan_collection_filter_plugin_syntax_error_is_reported(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "plugins" / "filter").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )
    (collection_root / "plugins" / "filter" / "broken.py").write_text(
        "def broken(:\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {"role_name": Path(role_path).name, "metadata": {}},
    )

    payload = api.scan_collection(str(collection_root))
    catalog = payload["plugin_catalog"]

    assert catalog["summary"]["files_scanned"] == 1
    assert catalog["summary"]["files_failed"] == 1
    assert catalog["summary"]["total_plugins"] == 0
    assert catalog["by_type"]["filter"] == []
    assert len(catalog["failures"]) == 1
    assert catalog["failures"][0]["relative_path"] == "plugins/filter/broken.py"
    assert catalog["failures"][0]["stage"] == "ast_parse"


def test_scan_collection_inventories_non_filter_plugin_types(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "plugins" / "lookup").mkdir(parents=True)
    (collection_root / "plugins" / "modules").mkdir(parents=True)
    (collection_root / "plugins" / "module_utils").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )
    (collection_root / "plugins" / "lookup" / "service.py").write_text(
        "DOCUMENTATION = ''\n",
        encoding="utf-8",
    )
    (collection_root / "plugins" / "modules" / "deploy").write_text(
        "#!/usr/bin/python\n",
        encoding="utf-8",
    )
    (collection_root / "plugins" / "module_utils" / "net.py").write_text(
        "def helper():\n    return 'ok'\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {"role_name": Path(role_path).name, "metadata": {}},
    )

    payload = api.scan_collection(str(collection_root))
    catalog = payload["plugin_catalog"]

    assert catalog["summary"]["files_scanned"] == 3
    assert catalog["summary"]["files_failed"] == 0
    assert catalog["summary"]["total_plugins"] == 3
    assert catalog["summary"]["types_present"] == ["modules", "lookup", "module_utils"]

    modules_record = catalog["by_type"]["modules"][0]
    assert modules_record["name"] == "deploy"
    assert modules_record["language"] == "unknown"
    assert modules_record["extraction"]["method"] == "path_inventory"

    lookup_record = catalog["by_type"]["lookup"][0]
    assert lookup_record["name"] == "service"
    assert lookup_record["language"] == "python"

    module_utils_record = catalog["by_type"]["module_utils"][0]
    assert module_utils_record["name"] == "net"
    assert module_utils_record["language"] == "python"


def test_scan_collection_extracts_short_description_from_plugin_documentation(
    monkeypatch, tmp_path
):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "plugins" / "modules").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )
    (collection_root / "plugins" / "modules" / "deploy.py").write_text(
        "DOCUMENTATION = '''\n"
        "---\n"
        "short_description: Deploy application resources\n"
        "'''\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {"role_name": Path(role_path).name, "metadata": {}},
    )

    payload = api.scan_collection(str(collection_root))
    record = payload["plugin_catalog"]["by_type"]["modules"][0]

    assert record["summary"] == "Deploy application resources"
    assert record["doc_source"] == "documentation_short_description"
    assert record["extraction"]["method"] == "ast"
    assert "short_description:" in record["documentation_blocks"]["DOCUMENTATION"]


def test_scan_collection_extracts_lookup_class_method_capability_hints(
    monkeypatch, tmp_path
):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "plugins" / "lookup").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )
    (collection_root / "plugins" / "lookup" / "service.py").write_text(
        "class LookupModule:\n"
        "    def run(self, terms, variables=None, **kwargs):\n"
        "        return terms\n\n"
        "    def helper(self):\n"
        "        return []\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {"role_name": Path(role_path).name, "metadata": {}},
    )

    payload = api.scan_collection(str(collection_root))
    record = payload["plugin_catalog"]["by_type"]["lookup"][0]

    assert record["doc_source"] == "class_method_hints"
    assert record["extraction"]["method"] == "ast"
    assert record["capability_hints"] == ["LookupModule.helper", "LookupModule.run"]
    assert "LookupModule" in record["symbols"]
    assert "run" in record["symbols"]


def test_load_yaml_document_returns_none_for_scalar_and_raises_for_invalid(tmp_path):
    scalar_path = tmp_path / "scalar.yml"
    scalar_path.write_text("---\n42\n", encoding="utf-8")
    invalid_path = tmp_path / "invalid.yml"
    invalid_path.write_text("{broken", encoding="utf-8")

    assert api._load_yaml_document(tmp_path / "missing.yml") is None
    assert api._load_yaml_document(scalar_path) is None
    with pytest.raises(prism_errors.PrismRuntimeError) as exc_info:
        api._load_yaml_document(invalid_path)
    assert exc_info.value.code == prism_errors.ROLE_CONTENT_YAML_INVALID


def test_requirements_entries_and_dependency_key_helpers_cover_edge_cases():
    list_entries = api._requirements_entries_from_document(
        [
            {"name": "community.general"},
            "ignore-me",
        ]
    )
    dict_entries = api._requirements_entries_from_document(
        {
            "collections": [{"name": "community.crypto"}],
            "roles": [{"name": "geerlingguy.mysql"}],
        }
    )

    assert list_entries == [{"name": "community.general"}]
    assert dict_entries == [
        {"name": "community.crypto"},
        {"name": "geerlingguy.mysql"},
    ]
    assert api._requirements_entries_from_document("not-a-doc") == []

    assert (
        api._collection_dependency_key({"src": "community.general"}, 0)
        == "community.general"
    )
    assert api._collection_dependency_key({"src": "git+ssh://example/repo"}, 0) is None
    assert api._role_dependency_key({"name": ""}, 7) == "unknown:7"


def test_scan_collection_writes_runbook_markdown_and_csv(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    role_dir = collection_root / "roles" / "role_a"
    role_dir.mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {
            "role_name": Path(role_path).name,
            "metadata": {"task_catalog": [{"name": "task"}]},
        },
    )
    monkeypatch.setattr(api, "render_runbook", lambda role_name, metadata: "# RB\n")
    monkeypatch.setattr(api, "render_runbook_csv", lambda metadata: "task,file\n")

    runbook_dir = tmp_path / "runbooks"
    runbook_csv_dir = tmp_path / "runbooks_csv"
    payload = api.scan_collection(
        str(collection_root),
        runbook_output_dir=str(runbook_dir),
        runbook_csv_output_dir=str(runbook_csv_dir),
    )

    assert payload["summary"]["scanned_roles"] == 1
    assert (runbook_dir / "role_a.runbook.md").read_text(encoding="utf-8") == "# RB\n"
    assert (runbook_csv_dir / "role_a.runbook.csv").read_text(
        encoding="utf-8"
    ) == "task,file\n"


def test_scan_collection_records_post_scan_render_failures(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "roles" / "role_b").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {
            "role_name": Path(role_path).name,
            "metadata": {},
            "variables": {},
            "requirements": [],
            "default_filters": [],
            "description": "",
        },
    )

    def fake_render_readme(*args, **kwargs):
        role_name = kwargs.get("role_name") or (args[1] if len(args) > 1 else None)
        if role_name == "role_b":
            raise RuntimeError("render boom")
        return "# ok\n"

    monkeypatch.setattr(api, "render_readme", fake_render_readme)

    payload = api.scan_collection(str(collection_root), include_rendered_readme=True)

    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 1,
        "failed_roles": 1,
    }
    assert payload["failures"] == [
        {
            "role": "role_b",
            "path": str((collection_root / "roles" / "role_b").resolve()),
            "error_code": "role_scan_runtime_error",
            "error_category": "runtime",
            "error_type": "RuntimeError",
            "error": "render boom",
        }
    ]


def test_scan_collection_records_runbook_render_failures(monkeypatch, tmp_path):
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "roles" / "role_b").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        api,
        "scan_role",
        lambda role_path, **kwargs: {
            "role_name": Path(role_path).name,
            "metadata": {},
        },
    )

    def fake_render_runbook(role_name, metadata):
        if role_name == "role_b":
            raise RuntimeError("runbook boom")
        return "# RB\n"

    monkeypatch.setattr(api, "render_runbook", fake_render_runbook)

    payload = api.scan_collection(
        str(collection_root),
        runbook_output_dir=str(tmp_path / "runbooks"),
    )

    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 1,
        "failed_roles": 1,
    }
    assert payload["failures"] == [
        {
            "role": "role_b",
            "path": str((collection_root / "roles" / "role_b").resolve()),
            "error_code": "role_scan_runtime_error",
            "error_category": "runtime",
            "error_type": "RuntimeError",
            "error": "runbook boom",
        }
    ]


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
