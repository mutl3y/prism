import json
import pytest

from prism import repo_services
from prism import errors as prism_errors
from prism.tests._boundary_acceptance import (
    assert_callable_aliases_expose_contract,
    assert_named_exports_exist,
    assert_repo_scan_facade_contract,
)


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


def test_repo_services_declares_canonical_surface_registers() -> None:
    assert_named_exports_exist(
        repo_services, repo_services.REPO_SERVICE_CANONICAL_SURFACE
    )
    assert_named_exports_exist(
        repo_services, repo_services.REPO_SERVICE_COMPATIBILITY_SEAMS
    )


def test_repo_services_private_helpers_delegate_to_decomposed_modules():
    assert_callable_aliases_expose_contract(
        repo_services,
        (
            "_clone_repo",
            "_repo_scan_workspace",
            "_checkout_repo_scan_role",
            "_prepare_repo_scan_inputs",
            "_fetch_repo_file",
            "_fetch_repo_contents_payload",
            "_repo_name_from_url",
            "_normalize_repo_scan_result_payload",
        ),
        expected_owner_modules={
            "_clone_repo": "prism.repo_layer.intake",
            "_repo_scan_workspace": "prism.repo_layer.intake",
            "_checkout_repo_scan_role": "prism.repo_layer.intake",
            "_prepare_repo_scan_inputs": "prism.repo_layer.intake",
            "_fetch_repo_file": "prism.repo_layer.metadata",
            "_fetch_repo_contents_payload": "prism.repo_layer.metadata",
            "_repo_name_from_url": "prism.repo_layer.metadata",
            "_normalize_repo_scan_result_payload": "prism.repo_layer.metadata",
        },
    )


def test_repo_services_public_aliases_preserve_behavior_surface():
    assert_callable_aliases_expose_contract(
        repo_services,
        (
            "clone_repo",
            "prepare_repo_scan_inputs",
            "repo_scan_workspace",
            "fetch_repo_directory_names",
            "fetch_repo_file",
            "repo_name_from_url",
        ),
        expected_owner_modules={
            "clone_repo": "prism.repo_layer.intake",
            "prepare_repo_scan_inputs": "prism.repo_layer.intake",
            "repo_scan_workspace": "prism.repo_layer.intake",
            "fetch_repo_directory_names": "prism.repo_layer.metadata",
            "fetch_repo_file": "prism.repo_layer.metadata",
            "repo_name_from_url": "prism.repo_layer.metadata",
        },
    )
    assert (
        repo_services.repo_name_from_url("https://github.com/example/demo-role.git")
        == "demo-role"
    )


def test_repo_scan_facade_exposes_cohesive_api_surface():
    facade = repo_services.repo_scan_facade
    assert_callable_aliases_expose_contract(
        facade,
        (
            "clone_repo",
            "repo_scan_workspace",
            "checkout_repo_scan_role",
            "checkout_repo_lightweight_style_readme",
            "resolve_repo_scan_target",
            "normalize_repo_scan_metadata_paths",
        ),
        expected_owner_modules={
            "clone_repo": "prism.repo_layer.intake",
            "repo_scan_workspace": "prism.repo_layer.intake",
            "checkout_repo_scan_role": "prism.repo_layer.intake",
            "checkout_repo_lightweight_style_readme": "prism.repo_layer.intake",
            "resolve_repo_scan_target": "prism.repo_services",
            "normalize_repo_scan_metadata_paths": "prism.repo_layer.metadata",
        },
    )


def test_repo_scan_facade_exposes_api_compatibility_contracts():
    facade = repo_services.repo_scan_facade
    assert_repo_scan_facade_contract(facade)
    assert_callable_aliases_expose_contract(
        facade,
        (
            "build_repo_intake_components",
            "run_repo_scan",
            "normalize_repo_scan_payload",
        ),
        expected_owner_modules={
            "build_repo_intake_components": "prism.repo_services",
            "run_repo_scan": "prism.repo_services",
            "normalize_repo_scan_payload": "prism.repo_services",
        },
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
