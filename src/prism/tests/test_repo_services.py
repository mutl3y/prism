import json
import pytest

from prism import repo_services
from prism import repo_intake
from prism import repo_metadata
from prism import errors as prism_errors


def test_normalize_repo_scan_result_payload_supports_dict_payloads():
    payload = {
        "role_name": "demo-role",
        "metadata": {
            "style_guide": {"path": "/tmp/style.md"},
        },
    }

    normalized = repo_services._normalize_repo_scan_result_payload(
        payload,
        repo_style_readme_path="README.md",
        scanner_report_relpath="reports/repo.scan.md",
    )

    assert isinstance(normalized, dict)
    assert normalized["metadata"]["style_guide"]["path"] == "README.md"
    assert normalized["metadata"]["scanner_report_relpath"] == "reports/repo.scan.md"


def test_normalize_repo_scan_result_payload_supports_json_payloads():
    payload = json.dumps(
        {
            "role_name": "demo-role",
            "metadata": {
                "style_guide": {"path": "/tmp/style.md"},
            },
        }
    )

    normalized = repo_services._normalize_repo_scan_result_payload(
        payload,
        repo_style_readme_path="README.md",
        scanner_report_relpath="reports/repo.scan.md",
    )

    assert isinstance(normalized, str)
    normalized_payload = json.loads(normalized)
    assert normalized_payload["metadata"]["style_guide"]["path"] == "README.md"
    assert (
        normalized_payload["metadata"]["scanner_report_relpath"]
        == "reports/repo.scan.md"
    )


def test_normalize_repo_scan_result_payload_keeps_malformed_json_unchanged():
    payload = '{"role_name": "demo-role", "metadata":'

    with pytest.raises(RuntimeError, match="REPO_SCAN_PAYLOAD_JSON_INVALID"):
        repo_services._normalize_repo_scan_result_payload(
            payload,
            repo_style_readme_path="README.md",
        )


def test_normalize_repo_scan_result_payload_keeps_non_object_json_unchanged():
    payload = json.dumps(["demo-role"])

    with pytest.raises(RuntimeError, match="REPO_SCAN_PAYLOAD_TYPE_INVALID"):
        repo_services._normalize_repo_scan_result_payload(
            payload,
            repo_style_readme_path="README.md",
        )


def test_normalize_repo_scan_result_payload_rejects_invalid_metadata_shape():
    payload = json.dumps(
        {
            "role_name": "demo-role",
            "metadata": [],
        }
    )

    with pytest.raises(RuntimeError, match="REPO_SCAN_PAYLOAD_SHAPE_INVALID"):
        repo_services._normalize_repo_scan_result_payload(
            payload,
            repo_style_readme_path="README.md",
        )


def test_normalize_repo_scan_result_payload_rejects_invalid_style_guide_shape():
    payload = json.dumps(
        {
            "role_name": "demo-role",
            "metadata": {"style_guide": "not-an-object"},
        }
    )

    with pytest.raises(RuntimeError, match="REPO_SCAN_PAYLOAD_SHAPE_INVALID"):
        repo_services._normalize_repo_scan_result_payload(
            payload,
            repo_style_readme_path="README.md",
        )


def test_build_repo_intake_error_preserves_classified_dimensions():
    exc = RuntimeError("boom")
    err = repo_services.build_repo_intake_error(
        code=prism_errors.REPO_SPARSE_CHECKOUT_FAILED,
        message="sparse checkout failed",
        cause=exc,
    )

    assert err["code"] == prism_errors.REPO_SPARSE_CHECKOUT_FAILED
    assert err["category"] == prism_errors.ERROR_CATEGORY_REPO
    assert err["message"] == "sparse checkout failed"
    assert err["cause_type"] == "RuntimeError"


def test_repo_services_private_helpers_delegate_to_decomposed_modules():
    assert repo_services._clone_repo is repo_intake._clone_repo
    assert repo_services._repo_scan_workspace is repo_intake._repo_scan_workspace
    assert (
        repo_services._checkout_repo_scan_role is repo_intake._checkout_repo_scan_role
    )
    assert (
        repo_services._prepare_repo_scan_inputs is repo_intake._prepare_repo_scan_inputs
    )

    assert repo_services._fetch_repo_file is repo_metadata._fetch_repo_file
    assert (
        repo_services._fetch_repo_contents_payload
        is repo_metadata._fetch_repo_contents_payload
    )
    assert repo_services._repo_name_from_url is repo_metadata._repo_name_from_url
    assert (
        repo_services._normalize_repo_scan_result_payload
        is repo_metadata._normalize_repo_scan_result_payload
    )


def test_repo_services_public_aliases_preserve_behavior_surface():
    assert repo_services.clone_repo is repo_intake._clone_repo
    assert (
        repo_services.prepare_repo_scan_inputs is repo_intake._prepare_repo_scan_inputs
    )
    assert repo_services.repo_scan_workspace is repo_intake._repo_scan_workspace

    assert (
        repo_services.fetch_repo_directory_names
        is repo_metadata._fetch_repo_directory_names
    )
    assert repo_services.fetch_repo_file is repo_metadata._fetch_repo_file
    assert repo_services.repo_name_from_url is repo_metadata._repo_name_from_url


def test_repo_scan_facade_exposes_cohesive_api_surface():
    facade = repo_services.repo_scan_facade

    assert facade.clone_repo is repo_services.clone_repo
    assert facade.repo_scan_workspace is repo_services.repo_scan_workspace
    assert facade.checkout_repo_scan_role is repo_services.checkout_repo_scan_role
    assert (
        facade.checkout_repo_lightweight_style_readme
        is repo_services.checkout_repo_lightweight_style_readme
    )
    assert facade.resolve_repo_scan_target is repo_services.resolve_repo_scan_target
    assert (
        facade.normalize_repo_scan_metadata_paths
        is repo_services.normalize_repo_scan_metadata_paths
    )


def test_repo_scan_facade_exposes_api_compatibility_contracts():
    facade = repo_services.repo_scan_facade

    assert (
        facade.build_repo_intake_components
        is repo_services.build_repo_intake_components
    )
    assert facade.run_repo_scan is repo_services.run_repo_scan
    assert (
        facade.normalize_repo_scan_payload is repo_services.normalize_repo_scan_payload
    )


def test_run_repo_scan_uses_resolved_target_and_scan_callback(tmp_path):
    role_root = tmp_path / "role"
    role_root.mkdir(parents=True)
    calls: dict[str, object] = {}

    class _WorkspaceCtx:
        def __enter__(self):
            return tmp_path

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_resolve_repo_scan_target(**kwargs):
        calls["resolve_kwargs"] = kwargs
        return repo_services.RepoScanTarget(
            role_path=role_root,
            effective_style_readme_path="README.md",
            resolved_repo_style_readme_path="README.md",
        )

    def fake_scan(role_path, effective_style_readme_path, role_name_override):
        calls["scan_args"] = (
            role_path,
            effective_style_readme_path,
            role_name_override,
        )
        return {"role_name": role_name_override, "metadata": {}}

    result = repo_services.run_repo_scan(
        repo_url="https://github.com/example/demo-role.git",
        repo_role_path="roles/demo",
        repo_style_readme_path="README.md",
        style_readme_path=None,
        repo_ref="main",
        repo_timeout=10,
        lightweight_readme_only=False,
        create_style_guide=False,
        style_source_path=None,
        scan_fn=fake_scan,
        repo_scan_workspace_fn=lambda: _WorkspaceCtx(),
        resolve_repo_scan_target_fn=fake_resolve_repo_scan_target,
        repo_name_from_url_fn=lambda _repo_url: "demo-role",
        repo_intake_components=repo_services.build_repo_intake_components(),
    )

    assert isinstance(result.checkout, repo_services.RepoScanTarget)
    assert result.checkout.role_path == role_root
    assert result.scan_output["role_name"] == "demo-role"
    assert calls["scan_args"] == (str(role_root), "README.md", "demo-role")
