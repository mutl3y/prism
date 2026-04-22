"""Package-owned shared runtime helpers for Prism CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from prism.errors import (
    PrismRuntimeError,
    REPO_SCAN_PAYLOAD_JSON_INVALID,
    REPO_SCAN_PAYLOAD_SHAPE_INVALID,
    REPO_SCAN_PAYLOAD_TYPE_INVALID,
)
from prism.scanner_config.section import SECTION_CONFIG_FILENAMES
from prism.scanner_readme.style import parse_style_readme
from . import presenters as cli_presenters


def resolve_effective_readme_config(
    role_path: Path,
    explicit_config_path: str | None,
) -> str | None:
    if explicit_config_path:
        return explicit_config_path
    for cfg_name in SECTION_CONFIG_FILENAMES:
        default_cfg = role_path / cfg_name
        if default_cfg.is_file():
            return str(default_cfg)
    return None


def resolve_vars_context_paths(args: argparse.Namespace) -> list[str] | None:
    context_paths = list(args.vars_context_path or [])
    legacy_paths = list(args.vars_seed or [])
    if legacy_paths:
        print(
            "Warning: --vars-seed is deprecated and will be removed in a future release; "
            "use --vars-context-path instead.",
            file=sys.stderr,
        )
        context_paths.extend(legacy_paths)
    return context_paths or None


def normalize_repo_json_payload(
    rendered_payload: str,
    *,
    repo_style_readme_path: str | None,
    scanner_report_relpath: str | None,
    normalize_repo_scan_result_payload,
) -> str:
    try:
        normalized_payload = normalize_repo_scan_result_payload(
            rendered_payload,
            repo_style_readme_path=repo_style_readme_path,
            scanner_report_relpath=scanner_report_relpath,
        )
    except PrismRuntimeError as exc:
        if exc.code in {
            REPO_SCAN_PAYLOAD_JSON_INVALID,
            REPO_SCAN_PAYLOAD_TYPE_INVALID,
            REPO_SCAN_PAYLOAD_SHAPE_INVALID,
        }:
            return rendered_payload
        raise
    if isinstance(normalized_payload, str):
        return normalized_payload
    return rendered_payload


def save_style_comparison_artifacts(
    style_readme_path: str | None,
    generated_output: str,
    style_source_name: str | None = None,
    role_config_path: str | None = None,
    keep_unknown_style_sections: bool = False,
    *,
    parse_style_readme_fn=parse_style_readme,
    capture_schema_version: int = cli_presenters.CAPTURE_SCHEMA_VERSION,
    capture_max_sections: int = cli_presenters.CAPTURE_MAX_SECTIONS,
    capture_max_content_chars: int = cli_presenters.CAPTURE_MAX_CONTENT_CHARS,
    capture_max_total_chars: int = cli_presenters.CAPTURE_MAX_TOTAL_CHARS,
) -> tuple[str | None, str | None]:
    return cli_presenters.save_style_comparison_artifacts(
        style_readme_path,
        generated_output,
        style_source_name,
        role_config_path,
        keep_unknown_style_sections,
        parse_style_readme_fn=parse_style_readme_fn,
        capture_schema_version=capture_schema_version,
        capture_max_sections=capture_max_sections,
        capture_max_content_chars=capture_max_content_chars,
        capture_max_total_chars=capture_max_total_chars,
    )
