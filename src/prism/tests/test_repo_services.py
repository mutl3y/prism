import json

from prism import repo_services


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

    normalized = repo_services._normalize_repo_scan_result_payload(
        payload,
        repo_style_readme_path="README.md",
    )

    assert normalized == payload


def test_normalize_repo_scan_result_payload_keeps_non_object_json_unchanged():
    payload = json.dumps(["demo-role"])

    normalized = repo_services._normalize_repo_scan_result_payload(
        payload,
        repo_style_readme_path="README.md",
    )

    assert normalized == payload
