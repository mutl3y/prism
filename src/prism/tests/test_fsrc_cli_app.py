"""Tests for fsrc cli_app package: runtime, presenters, shared modules."""

from __future__ import annotations

from pathlib import Path

from prism.cli_app.runtime import (
    EXIT_CODE_GENERIC_ERROR,
    EXIT_CODE_INTERRUPTED,
    EXIT_CODE_JSON_PAYLOAD_ERROR,
    EXIT_CODE_NETWORK_ERROR,
    EXIT_CODE_NOT_FOUND,
    EXIT_CODE_OS_ERROR,
    EXIT_CODE_PERMISSION_DENIED,
    map_top_level_exception_to_exit_code,
    resolve_cli_output_path,
)
from prism.cli_app.presenters import (
    REDACTION_PATTERNS,
    sanitize_captured_content,
    truncate_content,
)
from prism.cli_app.shared import resolve_effective_readme_config


# --- EXIT_CODE constants ---


def test_exit_code_generic_error_value():
    assert EXIT_CODE_GENERIC_ERROR == 2


def test_exit_code_not_found_value():
    assert EXIT_CODE_NOT_FOUND == 3


def test_exit_code_permission_denied_value():
    assert EXIT_CODE_PERMISSION_DENIED == 4


def test_exit_code_json_payload_error_value():
    assert EXIT_CODE_JSON_PAYLOAD_ERROR == 5


def test_exit_code_network_error_value():
    assert EXIT_CODE_NETWORK_ERROR == 6


def test_exit_code_os_error_value():
    assert EXIT_CODE_OS_ERROR == 7


def test_exit_code_interrupted_value():
    assert EXIT_CODE_INTERRUPTED == 130


# --- map_top_level_exception_to_exit_code ---


def test_map_file_not_found_to_exit_code():
    assert (
        map_top_level_exception_to_exit_code(FileNotFoundError()) == EXIT_CODE_NOT_FOUND
    )


def test_map_permission_error_to_exit_code():
    assert (
        map_top_level_exception_to_exit_code(PermissionError())
        == EXIT_CODE_PERMISSION_DENIED
    )


def test_map_generic_exception_to_exit_code():
    assert (
        map_top_level_exception_to_exit_code(RuntimeError("boom"))
        == EXIT_CODE_GENERIC_ERROR
    )


def test_map_os_error_to_exit_code():
    assert map_top_level_exception_to_exit_code(OSError()) == EXIT_CODE_OS_ERROR


# --- REDACTION_PATTERNS ---


def test_redaction_patterns_redacts_password():
    text = "password=supersecret"
    pattern, replacement = REDACTION_PATTERNS[0]
    result = pattern.sub(replacement, text)
    assert "supersecret" not in result
    assert "password" in result


def test_redaction_patterns_redacts_token():
    text = "token=abc123xyz"
    pattern, replacement = REDACTION_PATTERNS[0]
    result = pattern.sub(replacement, text)
    assert "abc123xyz" not in result
    assert "token" in result


# --- sanitize_captured_content ---


def test_sanitize_captured_content_redacts_password():
    result = sanitize_captured_content("password=hunter2")
    assert "hunter2" not in result


def test_sanitize_captured_content_redacts_token_colon():
    result = sanitize_captured_content("token: mytoken99")
    assert "mytoken99" not in result


def test_sanitize_captured_content_keeps_safe_text():
    text = "This is a normal README with no secrets."
    assert sanitize_captured_content(text) == text


# --- truncate_content ---


def test_truncate_content_short_text_unchanged():
    text = "short text"
    result, was_truncated = truncate_content(text, 100)
    assert result == text
    assert was_truncated is False


def test_truncate_content_long_text_truncated():
    text = "a" * 200
    result, was_truncated = truncate_content(text, 50)
    assert len(result) < 200
    assert was_truncated is True
    assert "[truncated]" in result


def test_truncate_content_exactly_at_limit():
    text = "a" * 50
    result, was_truncated = truncate_content(text, 50)
    assert result == text
    assert was_truncated is False


# --- resolve_effective_readme_config ---


def test_resolve_effective_readme_config_returns_explicit_when_given(tmp_path):
    explicit = str(tmp_path / "custom.yml")
    result = resolve_effective_readme_config(tmp_path, explicit)
    assert result == explicit


def test_resolve_effective_readme_config_returns_none_when_no_default(tmp_path):
    result = resolve_effective_readme_config(tmp_path, None)
    assert result is None


def test_resolve_effective_readme_config_finds_default(tmp_path):
    cfg = tmp_path / ".prism.yml"
    cfg.write_text("sections: []", encoding="utf-8")
    result = resolve_effective_readme_config(tmp_path, None)
    assert result == str(cfg)


# --- resolve_cli_output_path ---


def test_resolve_cli_output_path_appends_json_suffix():
    result = resolve_cli_output_path("output/report", "json")
    assert result == Path("output/report.json")


def test_resolve_cli_output_path_appends_md_suffix():
    result = resolve_cli_output_path("output/report", "md")
    assert result == Path("output/report.md")


def test_resolve_cli_output_path_keeps_existing_json_suffix():
    result = resolve_cli_output_path("output/report.json", "json")
    assert result == Path("output/report.json")


def test_resolve_cli_output_path_keeps_existing_md_suffix():
    result = resolve_cli_output_path("output/readme.md", "md")
    assert result == Path("output/readme.md")
