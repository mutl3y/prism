import json
import pytest

from prism import repo_services
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
