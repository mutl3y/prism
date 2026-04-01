"""CLI entry point for prism.

Provides a small CLI wrapper around :func:`prism.scanner.run_scan`.
"""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile as _tempfile
from urllib.request import urlopen

from prism import cli_commands, cli_presenters
from prism.feedback import apply_feedback_recommendations, load_feedback
from prism.repo_services import (
    build_repo_style_readme_candidates as _repo_build_repo_style_readme_candidates,
    build_sparse_clone_paths as _build_sparse_clone_paths,
    checkout_repo_lightweight_style_readme as _repo_checkout_repo_lightweight_style_readme,
    checkout_repo_scan_role as _checkout_repo_scan_role,
    clone_repo as _repo_clone_repo,
    fetch_repo_contents_payload as _repo_fetch_repo_contents_payload,
    fetch_repo_directory_names as _repo_fetch_repo_directory_names,
    fetch_repo_file as _repo_fetch_repo_file,
    github_repo_from_url as _repo_github_repo_from_url,
    normalize_repo_path as _repo_normalize_repo_path,
    normalize_repo_scan_result_payload as _normalize_repo_scan_result_payload,
    prepare_repo_scan_inputs as _prepare_repo_scan_inputs,
    repo_name_from_url as _repo_name_from_url,
    repo_path_looks_like_role as _repo_path_looks_like_role,
    repo_scan_workspace as _repo_scan_workspace,
    resolve_repo_scan_scanner_report_relpath as _resolve_repo_scan_scanner_report_relpath,
    resolve_style_readme_candidate as _resolve_style_readme_candidate,
)
from prism.scanner import parse_style_readme, resolve_default_style_guide_source, run_scan

# Compatibility exports for downstream imports and parity checks with API/helpers.
_build_repo_style_readme_candidates = _repo_build_repo_style_readme_candidates
_checkout_repo_lightweight_style_readme = _repo_checkout_repo_lightweight_style_readme
# Re-export the same tempfile module object used in repo_services.
tempfile = _tempfile

_CAPTURE_SCHEMA_VERSION = cli_presenters._CAPTURE_SCHEMA_VERSION
_CAPTURE_MAX_SECTIONS = cli_presenters._CAPTURE_MAX_SECTIONS
_CAPTURE_MAX_CONTENT_CHARS = cli_presenters._CAPTURE_MAX_CONTENT_CHARS
_CAPTURE_MAX_TOTAL_CHARS = cli_presenters._CAPTURE_MAX_TOTAL_CHARS
_TRUNCATION_MARKER = cli_presenters._TRUNCATION_MARKER
_REDACTION_PATTERNS = cli_presenters._REDACTION_PATTERNS

_EXIT_CODE_GENERIC_ERROR = cli_commands._EXIT_CODE_GENERIC_ERROR
_EXIT_CODE_NOT_FOUND = cli_commands._EXIT_CODE_NOT_FOUND
_EXIT_CODE_PERMISSION_DENIED = cli_commands._EXIT_CODE_PERMISSION_DENIED
_EXIT_CODE_JSON_PAYLOAD_ERROR = cli_commands._EXIT_CODE_JSON_PAYLOAD_ERROR
_EXIT_CODE_NETWORK_ERROR = cli_commands._EXIT_CODE_NETWORK_ERROR
_EXIT_CODE_OS_ERROR = cli_commands._EXIT_CODE_OS_ERROR
_EXIT_CODE_INTERRUPTED = cli_commands._EXIT_CODE_INTERRUPTED


_ReadableYamlDumper = cli_presenters._ReadableYamlDumper


def _str_presenter(dumper, data):
    return cli_presenters._str_presenter(dumper, data)


def _sanitize_captured_content(text: str) -> str:
    return cli_presenters._sanitize_captured_content(text)


def _truncate_content(text: str, max_chars: int) -> tuple[str, bool]:
    return cli_presenters._truncate_content(text, max_chars)


def _as_dict(value: object) -> dict:
    return cli_presenters._as_dict(value)


def _bounded_list(items: list[dict], limit: int) -> tuple[list[dict], int]:
    return cli_presenters._bounded_list(items, limit)


def _render_collection_markdown(payload: dict) -> str:
    return cli_presenters._render_collection_markdown(payload)


def _add_shared_scan_arguments(parser: argparse.ArgumentParser) -> None:
    cli_commands._add_shared_scan_arguments(parser)


def _add_common_output_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_template: bool,
    format_choices: tuple[str, ...],
) -> None:
    cli_commands._add_common_output_arguments(
        parser,
        include_template=include_template,
        format_choices=format_choices,
    )


def _add_repo_arguments(parser: argparse.ArgumentParser) -> None:
    cli_commands._add_repo_arguments(parser)


def build_parser() -> argparse.ArgumentParser:
    return cli_commands.build_parser()


def _collect_option_strings(parser: argparse.ArgumentParser) -> list[str]:
    return cli_commands._collect_option_strings(parser)


def _build_bash_completion_script() -> str:
    return cli_commands._build_bash_completion_script(parser_factory=build_parser)


def _resolve_effective_readme_config(
    role_path: Path,
    explicit_config_path: str | None,
) -> str | None:
    return cli_commands._resolve_effective_readme_config(role_path, explicit_config_path)


def _emit_success(
    args: argparse.Namespace,
    outpath: str,
    style_source_path: str | None = None,
    style_demo_path: str | None = None,
) -> int:
    return cli_presenters._emit_success(args, outpath, style_source_path, style_demo_path)


def _resolve_vars_context_paths(args: argparse.Namespace) -> list[str] | None:
    return cli_commands._resolve_vars_context_paths(args)


def _resolve_include_collection_checks(
    feedback_source: str | None,
    include_collection_checks: bool,
) -> bool | None:
    return cli_commands._resolve_include_collection_checks(
        feedback_source,
        include_collection_checks,
        load_feedback=load_feedback,
        apply_feedback_recommendations=apply_feedback_recommendations,
    )


def _normalize_repo_json_payload(
    rendered_payload: str,
    *,
    repo_style_readme_path: str | None,
    scanner_report_relpath: str | None,
) -> str:
    return cli_commands._normalize_repo_json_payload(
        rendered_payload,
        repo_style_readme_path=repo_style_readme_path,
        scanner_report_relpath=scanner_report_relpath,
        normalize_repo_scan_result_payload=_normalize_repo_scan_result_payload,
    )


def _map_top_level_exception_to_exit_code(exc: Exception) -> int:
    return cli_commands._map_top_level_exception_to_exit_code(exc)


def _format_top_level_exception(exc: Exception) -> str:
    return cli_commands._format_top_level_exception(exc)


def _handle_repo_command(args: argparse.Namespace) -> int:
    return cli_commands._handle_repo_command(
        args,
        repo_scan_workspace=_repo_scan_workspace,
        checkout_repo_scan_role=_checkout_repo_scan_role,
        prepare_repo_scan_inputs=_prepare_repo_scan_inputs,
        fetch_repo_directory_names=_fetch_repo_directory_names,
        repo_path_looks_like_role=_repo_path_looks_like_role,
        fetch_repo_file=_fetch_repo_file,
        clone_repo=_clone_repo,
        build_sparse_clone_paths=_build_sparse_clone_paths,
        resolve_style_readme_candidate=_resolve_style_readme_candidate,
        resolve_default_style_guide_source=resolve_default_style_guide_source,
        run_scan=run_scan,
        repo_name_from_url=_repo_name_from_url,
        resolve_repo_scan_scanner_report_relpath=_resolve_repo_scan_scanner_report_relpath,
        resolve_include_collection_checks=_resolve_include_collection_checks,
        normalize_repo_json_payload=_normalize_repo_json_payload,
        resolve_effective_readme_config=_resolve_effective_readme_config,
        save_style_comparison_artifacts=_save_style_comparison_artifacts,
        emit_success=_emit_success,
        resolve_vars_context_paths=_resolve_vars_context_paths,
    )


def _handle_collection_command(args: argparse.Namespace) -> int:
    from prism.api import scan_collection

    return cli_commands._handle_collection_command(
        args,
        scan_collection=scan_collection,
        render_collection_markdown=_render_collection_markdown,
        resolve_vars_context_paths=_resolve_vars_context_paths,
        resolve_include_collection_checks=_resolve_include_collection_checks,
        emit_success=_emit_success,
    )


def _handle_role_command(args: argparse.Namespace) -> int:
    return cli_commands._handle_role_command(
        args,
        run_scan=run_scan,
        resolve_default_style_guide_source=resolve_default_style_guide_source,
        resolve_vars_context_paths=_resolve_vars_context_paths,
        resolve_include_collection_checks=_resolve_include_collection_checks,
        resolve_effective_readme_config=_resolve_effective_readme_config,
        save_style_comparison_artifacts=_save_style_comparison_artifacts,
        emit_success=_emit_success,
    )


def _handle_completion_command(args: argparse.Namespace) -> int:
    return cli_commands._handle_completion_command(
        args,
        build_bash_completion_script=_build_bash_completion_script,
    )


def _clone_repo(
    repo_url: str,
    destination: Path,
    ref: str | None = None,
    timeout: int = 60,
    sparse_paths: list[str] | None = None,
    allow_sparse_fallback_to_full: bool = True,
) -> None:
    _repo_clone_repo(
        repo_url,
        destination,
        ref,
        timeout,
        sparse_paths=sparse_paths,
        allow_sparse_fallback_to_full=allow_sparse_fallback_to_full,
        run_command=subprocess.run,
        environment=os.environ,
        remove_tree=shutil.rmtree,
    )


def _github_repo_from_url(repo_url: str) -> tuple[str, str] | None:
    return _repo_github_repo_from_url(repo_url)


def _normalize_repo_path(repo_path: str | None) -> str:
    return _repo_normalize_repo_path(repo_path)


def _fetch_repo_contents_payload(
    repo_url: str,
    repo_path: str | None = None,
    ref: str | None = None,
    timeout: int = 60,
    *,
    opener=urlopen,
) -> dict | list | None:
    return _repo_fetch_repo_contents_payload(
        repo_url,
        repo_path=repo_path,
        ref=ref,
        timeout=timeout,
        opener=opener,
    )


def _fetch_repo_directory_names(
    repo_url: str,
    repo_path: str | None = None,
    ref: str | None = None,
    timeout: int = 60,
) -> set[str] | None:
    return _repo_fetch_repo_directory_names(
        repo_url,
        repo_path=repo_path,
        ref=ref,
        timeout=timeout,
        opener=urlopen,
        fetch_payload=_fetch_repo_contents_payload,
    )


def _fetch_repo_file(
    repo_url: str,
    repo_path: str | None,
    destination: Path,
    ref: str | None = None,
    timeout: int = 60,
) -> Path | None:
    return _repo_fetch_repo_file(
        repo_url,
        repo_path,
        destination,
        ref=ref,
        timeout=timeout,
        opener=urlopen,
        fetch_payload=_fetch_repo_contents_payload,
        decode_base64=base64.b64decode,
    )


def _save_style_comparison_artifacts(
    style_readme_path: str | None,
    generated_output: str,
    style_source_name: str | None = None,
    role_config_path: str | None = None,
    keep_unknown_style_sections: bool = False,
) -> tuple[str | None, str | None]:
    return cli_presenters._save_style_comparison_artifacts(
        style_readme_path,
        generated_output,
        style_source_name,
        role_config_path,
        keep_unknown_style_sections,
        parse_style_readme_fn=parse_style_readme,
        capture_schema_version=_CAPTURE_SCHEMA_VERSION,
        capture_max_sections=_CAPTURE_MAX_SECTIONS,
        capture_max_content_chars=_CAPTURE_MAX_CONTENT_CHARS,
        capture_max_total_chars=_CAPTURE_MAX_TOTAL_CHARS,
    )


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0

    try:
        if args.command == "repo":
            return _handle_repo_command(args)
        if args.command == "collection":
            return _handle_collection_command(args)
        if args.command == "role":
            return _handle_role_command(args)
        if args.command == "completion":
            return _handle_completion_command(args)
        raise ValueError(f"unsupported command: {args.command}")
    except KeyboardInterrupt:
        return _EXIT_CODE_INTERRUPTED
    except Exception as exc:
        print(_format_top_level_exception(exc), file=sys.stderr)
        return _map_top_level_exception_to_exit_code(exc)


if __name__ == "__main__":
    raise SystemExit(main())
