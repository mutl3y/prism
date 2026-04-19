"""Minimal CLI entrypoint for the fsrc Prism package lane."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import PurePosixPath, PureWindowsPath
import sys
from urllib.error import HTTPError, URLError

import prism.api as api
from prism.errors import PrismRuntimeError


CLI_PUBLIC_ENTRYPOINTS: tuple[str, ...] = ("main", "build_parser")
CLI_RETAINED_COMPATIBILITY_SEAMS: tuple[str, ...] = ("_handle_repo_command",)

__all__ = ["main", "build_parser"]

_EXIT_CODE_GENERIC_ERROR = 2
_EXIT_CODE_NOT_FOUND = 3
_EXIT_CODE_PERMISSION_DENIED = 4
_EXIT_CODE_JSON_PAYLOAD_ERROR = 5
_EXIT_CODE_NETWORK_ERROR = 6
_EXIT_CODE_OS_ERROR = 7
_EXIT_CODE_INTERRUPTED = 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prism")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    role_parser = subparsers.add_parser("role")
    role_parser.add_argument("role_path", help="Path to the role to scan")
    role_parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit machine-readable JSON output",
    )

    collection_parser = subparsers.add_parser("collection")
    collection_parser.add_argument(
        "collection_path", help="Path to the collection root to scan"
    )
    collection_parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit machine-readable JSON output",
    )

    repo_parser = subparsers.add_parser("repo")
    repo_parser.add_argument("--repo-url", required=True, help="Repository URL")
    repo_parser.add_argument(
        "--repo-role-path",
        default=".",
        help="Role path relative to repository root",
    )
    repo_parser.add_argument(
        "--repo-style-readme-path",
        default=None,
        help="Optional style README path relative to repository root",
    )
    repo_parser.add_argument(
        "--style-readme-path",
        default=None,
        help="Optional explicit style README path",
    )
    repo_parser.add_argument(
        "--repo-ref", default=None, help="Repository branch or ref"
    )
    repo_parser.add_argument(
        "--repo-timeout",
        type=int,
        default=60,
        help="Repository clone timeout in seconds",
    )
    repo_parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit machine-readable JSON output",
    )

    completion_parser = subparsers.add_parser("completion")
    completion_parser.add_argument(
        "shell", choices=("bash",), help="Shell to generate completion for"
    )

    return parser


def _emit_payload(payload: Mapping[str, object], *, emit_json: bool) -> None:
    if emit_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    metadata = payload.get("metadata")
    features = metadata.get("features") if isinstance(metadata, dict) else {}
    role_name = str(payload.get("role_name") or "<unknown>")
    description = str(payload.get("description") or "")
    display_variables = payload.get("display_variables")
    variable_count = (
        len(display_variables) if isinstance(display_variables, dict) else 0
    )
    task_files_scanned = (
        features.get("task_files_scanned", "n/a")
        if isinstance(features, dict)
        else "n/a"
    )

    print(f"Role: {role_name}")
    print(f"Description: {description}")
    print(f"Variables: {variable_count}")
    print(f"Task files scanned: {task_files_scanned}")


def _collection_name_from_path(collection_path: str) -> str:
    normalized_path = collection_path.strip()
    if not normalized_path:
        return "<unknown>"

    if "\\" in normalized_path:
        collection_name = PureWindowsPath(normalized_path).name.strip()
    else:
        collection_name = PurePosixPath(normalized_path).name.strip()

    if collection_name:
        return collection_name
    return (
        PureWindowsPath(normalized_path).name.strip()
        or PurePosixPath(normalized_path).name.strip()
        or "<unknown>"
    )


def _emit_collection_payload(payload: Mapping[str, object], *, emit_json: bool) -> None:
    if emit_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    collection = payload.get("collection") if isinstance(payload, dict) else {}
    collection_data = collection if isinstance(collection, dict) else {}
    collection_metadata_value = collection_data.get("metadata")
    collection_metadata = (
        collection_metadata_value if isinstance(collection_metadata_value, dict) else {}
    )
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}

    namespace = str(collection_metadata.get("namespace") or "").strip()
    name = str(collection_metadata.get("name") or "").strip()
    if namespace and name:
        collection_name = f"{namespace}.{name}"
    elif name:
        collection_name = name
    else:
        collection_path = str(collection_data.get("path") or "").strip()
        collection_name = _collection_name_from_path(collection_path)

    scanned_roles = (
        summary.get("scanned_roles", "n/a") if isinstance(summary, dict) else "n/a"
    )
    roles_failed = (
        summary.get("failed_roles", "n/a") if isinstance(summary, dict) else "n/a"
    )

    print(f"Collection: {collection_name}")
    print(f"Roles scanned: {scanned_roles}")
    print(f"Roles failed: {roles_failed}")


def _handle_repo_command(args: argparse.Namespace) -> int:
    payload = api.scan_repo(
        args.repo_url,
        repo_ref=args.repo_ref,
        repo_role_path=args.repo_role_path,
        repo_timeout=args.repo_timeout,
        repo_style_readme_path=args.repo_style_readme_path,
        style_readme_path=args.style_readme_path,
    )
    if not isinstance(payload, dict):
        payload = json.loads(payload)
    _emit_payload(payload, emit_json=args.emit_json)
    return 0


def _handle_collection_command(args: argparse.Namespace) -> int:
    payload = api.scan_collection(args.collection_path)
    _emit_collection_payload(payload, emit_json=args.emit_json)
    return 0


def _build_bash_completion_script() -> str:
    return "\n".join(
        (
            "# prism bash completion (generated)",
            "_prism_completion() {",
            '    local cur cmd opts=""',
            "    COMPREPLY=()",
            '    cur="${COMP_WORDS[COMP_CWORD]}"',
            '    cmd="${COMP_WORDS[1]}"',
            "",
            "    if [[ ${COMP_CWORD} -eq 1 ]]; then",
            '        COMPREPLY=( $(compgen -W "collection completion repo role" -- "$cur") )',
            "        return 0",
            "    fi",
            "",
            '    if [[ "$cmd" == "completion" && ${COMP_CWORD} -eq 2 ]]; then',
            '        COMPREPLY=( $(compgen -W "bash" -- "$cur") )',
            "        return 0",
            "    fi",
            "",
            '    case "$cmd" in',
            '        role) opts="--json" ;;',
            '        collection) opts="--json" ;;',
            '        repo) opts="--json --repo-ref --repo-role-path --repo-style-readme-path --repo-timeout --repo-url --style-readme-path" ;;',
            "    esac",
            "",
            '    if [[ "$cur" == -* ]]; then',
            '        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )',
            "        return 0",
            "    fi",
            "",
            '    COMPREPLY=( $(compgen -f -- "$cur") )',
            "}",
            "complete -F _prism_completion prism",
            "",
        )
    )


def _handle_completion_command(args: argparse.Namespace) -> int:
    if args.shell != "bash":
        return _EXIT_CODE_GENERIC_ERROR
    print(_build_bash_completion_script())
    return 0


def _map_top_level_exception_to_exit_code(exc: Exception) -> int:
    if isinstance(exc, PrismRuntimeError):
        if exc.category == "network":
            return _EXIT_CODE_NETWORK_ERROR
        if exc.category == "io":
            return _EXIT_CODE_OS_ERROR
        return _EXIT_CODE_GENERIC_ERROR
    if isinstance(exc, FileNotFoundError):
        return _EXIT_CODE_NOT_FOUND
    if isinstance(exc, PermissionError):
        return _EXIT_CODE_PERMISSION_DENIED
    if isinstance(exc, json.JSONDecodeError):
        return _EXIT_CODE_JSON_PAYLOAD_ERROR
    if isinstance(exc, (HTTPError, URLError)):
        return _EXIT_CODE_NETWORK_ERROR
    if isinstance(exc, OSError):
        return _EXIT_CODE_OS_ERROR
    return _EXIT_CODE_GENERIC_ERROR


def _format_top_level_exception(exc: Exception) -> str:
    if isinstance(exc, PrismRuntimeError):
        return f"Error: code={exc.code} category={exc.category} message={exc.message}"
    return f"Error: message={exc}"


def main(argv: Sequence[str] | None = None) -> int:
    """Execute a minimal role scan from the fsrc package CLI."""
    parser = build_parser()
    argv_items = list(argv) if argv is not None else list(sys.argv[1:])

    try:
        args = parser.parse_args(argv_items)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0

    try:
        if args.command == "repo":
            return _handle_repo_command(args)
        if args.command == "collection":
            return _handle_collection_command(args)
        if args.command == "completion":
            return _handle_completion_command(args)
        payload = api.scan_role(args.role_path)
    except KeyboardInterrupt:
        return _EXIT_CODE_INTERRUPTED
    except Exception as exc:
        print(_format_top_level_exception(exc), file=sys.stderr)
        return _map_top_level_exception_to_exit_code(exc)

    _emit_payload(payload, emit_json=args.emit_json)
    return 0
