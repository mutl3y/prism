"""Package-owned runtime helpers for Prism CLI facade behavior."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError

from prism.errors import PrismRuntimeError

EXIT_CODE_GENERIC_ERROR = 2
EXIT_CODE_NOT_FOUND = 3
EXIT_CODE_PERMISSION_DENIED = 4
EXIT_CODE_JSON_PAYLOAD_ERROR = 5
EXIT_CODE_NETWORK_ERROR = 6
EXIT_CODE_OS_ERROR = 7
EXIT_CODE_INTERRUPTED = 130


def finalize_repo_json_output(
    rendered_or_path: str,
    *,
    dry_run: bool,
    repo_style_readme_path: str | None,
    scanner_report_relpath: str | None,
    normalize_repo_json_payload,
) -> str:
    """Normalize repo JSON output while preserving dry-run vs file-write semantics."""
    if dry_run:
        return normalize_repo_json_payload(
            rendered_or_path,
            repo_style_readme_path=repo_style_readme_path,
            scanner_report_relpath=scanner_report_relpath,
        )

    output_path = Path(rendered_or_path)
    try:
        raw_payload = output_path.read_text(encoding="utf-8")
    except OSError:
        raw_payload = ""
    normalized_payload = normalize_repo_json_payload(
        raw_payload,
        repo_style_readme_path=repo_style_readme_path,
        scanner_report_relpath=scanner_report_relpath,
    )
    if normalized_payload and normalized_payload != raw_payload:
        output_path.write_text(normalized_payload, encoding="utf-8")
    return rendered_or_path


def resolve_cli_output_path(output: str, output_format: str) -> Path:
    """Resolve the effective output path for CLI-managed collection outputs."""
    output_path = Path(output)
    if output_format == "json" and output_path.suffix.lower() != ".json":
        return output_path.with_suffix(".json")
    if output_format == "md" and output_path.suffix.lower() != ".md":
        return output_path.with_suffix(".md")
    return output_path


def persist_collection_role_markdown_documents(
    *,
    output_path: Path,
    payload: dict,
) -> None:
    """Write per-role markdown documents beside collection markdown output."""
    roles_dir = output_path.parent / "roles"
    roles_dir.mkdir(parents=True, exist_ok=True)
    for role_entry in payload.get("roles", []):
        if not isinstance(role_entry, dict):
            continue
        role_name = str(role_entry.get("role") or "")
        if not role_name:
            continue
        role_doc = role_entry.get("rendered_readme")
        if not isinstance(role_doc, str) or not role_doc.strip():
            continue
        (roles_dir / f"{role_name}.md").write_text(role_doc, encoding="utf-8")


def map_top_level_exception_to_exit_code(exc: Exception) -> int:
    if isinstance(exc, PrismRuntimeError):
        if exc.category == "network":
            return EXIT_CODE_NETWORK_ERROR
        if exc.category == "io":
            return EXIT_CODE_OS_ERROR
        return EXIT_CODE_GENERIC_ERROR
    if isinstance(exc, FileNotFoundError):
        return EXIT_CODE_NOT_FOUND
    if isinstance(exc, PermissionError):
        return EXIT_CODE_PERMISSION_DENIED
    if isinstance(exc, json.JSONDecodeError):
        return EXIT_CODE_JSON_PAYLOAD_ERROR
    if isinstance(exc, (HTTPError, URLError)):
        return EXIT_CODE_NETWORK_ERROR
    if isinstance(exc, OSError):
        return EXIT_CODE_OS_ERROR
    return EXIT_CODE_GENERIC_ERROR


def format_top_level_exception(exc: Exception) -> str:
    if isinstance(exc, PrismRuntimeError):
        return f"Error: code={exc.code} category={exc.category} message={exc.message}"
    return f"Error: message={exc}"
