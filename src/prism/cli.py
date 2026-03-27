"""CLI entry point for prism.

Provides a small CLI wrapper around :func:`prism.scanner.run_scan`.
"""

from __future__ import annotations
import base64
import argparse
from datetime import datetime, UTC
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import sys
import yaml
from .repo_services import (
    _build_sparse_clone_paths,
    _checkout_repo_scan_role,
    _clone_repo as _repo_clone_repo,
    _fetch_repo_directory_names as _repo_fetch_repo_directory_names,
    _fetch_repo_file as _repo_fetch_repo_file,
    _fetch_repo_contents_payload as _repo_fetch_repo_contents_payload,
    _github_repo_from_url as _repo_github_repo_from_url,
    _normalize_repo_scan_result_payload,
    _normalize_repo_path as _repo_normalize_repo_path,
    _prepare_repo_scan_inputs,
    _repo_name_from_url,
    _repo_path_looks_like_role,
    _repo_scan_workspace,
    _resolve_repo_scan_scanner_report_relpath,
    _resolve_style_readme_candidate,
)
from .scanner import (
    SECTION_CONFIG_FILENAMES,
    parse_style_readme,
    resolve_default_style_guide_source,
    run_scan,
)
from .feedback import load_feedback, apply_feedback_recommendations


class _ReadableYamlDumper(yaml.SafeDumper):
    """YAML dumper that emits multiline strings as literal blocks."""


def _str_presenter(dumper: yaml.SafeDumper, data: str) -> yaml.nodes.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_ReadableYamlDumper.add_representer(str, _str_presenter)

_CAPTURE_SCHEMA_VERSION = 1
_CAPTURE_MAX_SECTIONS = 50
_CAPTURE_MAX_CONTENT_CHARS = 20000
_CAPTURE_MAX_TOTAL_CHARS = 1_000_000
_TRUNCATION_MARKER = "\n[truncated]"

_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"(?im)\\b(password|passwd|token|secret|api[_-]?key)\\b\\s*[:=]\\s*([^\\s]+)"
        ),
        r"\\1: <redacted>",
    ),
    (
        re.compile(r"(?i)\\b(bearer)\\s+[A-Za-z0-9._~+/-]+=*"),
        r"\\1 <redacted>",
    ),
)


def _sanitize_captured_content(text: str) -> str:
    """Redact obvious secret-like tokens from captured markdown content."""
    sanitized = text
    for pattern, replacement in _REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def _truncate_content(text: str, max_chars: int) -> tuple[str, bool]:
    """Return content truncated to max chars with a marker when needed."""
    if len(text) <= max_chars:
        return text, False
    clipped = text[:max_chars].rstrip()
    return f"{clipped}{_TRUNCATION_MARKER}", True


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _bounded_list(items: list[dict], limit: int) -> tuple[list[dict], int]:
    if len(items) <= limit:
        return items, 0
    return items[:limit], len(items) - limit


def _render_collection_markdown(payload: dict) -> str:
    max_plugin_rows = 40
    max_filter_rows = 25
    max_role_rows = 60
    max_failure_rows = 30

    collection = payload.get("collection", {}) if isinstance(payload, dict) else {}
    metadata = _as_dict(collection.get("metadata", {}))
    namespace = str(metadata.get("namespace") or "unknown")
    name = str(metadata.get("name") or "collection")
    fqcn = f"{namespace}.{name}"
    version = str(metadata.get("version") or "unknown")

    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    total_roles = int(summary.get("total_roles") or 0)
    scanned_roles = int(summary.get("scanned_roles") or 0)
    failed_roles = int(summary.get("failed_roles") or 0)

    lines: list[str] = [
        f"# {fqcn} Collection Documentation",
        "",
        "## Collection",
        "",
        f"- FQCN: `{fqcn}`",
        f"- Version: {version}",
        "",
        "## Summary",
        "",
        f"- Total roles: {total_roles}",
        f"- Scanned roles: {scanned_roles}",
        f"- Failed roles: {failed_roles}",
    ]

    dependencies = payload.get("dependencies", {}) if isinstance(payload, dict) else {}
    collections = (
        dependencies.get("collections", []) if isinstance(dependencies, dict) else []
    )
    role_dependencies = (
        dependencies.get("roles", []) if isinstance(dependencies, dict) else []
    )
    if collections:
        lines.extend(["", "## Collection Dependencies", ""])
        for item in collections:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("name") or "unknown")
            version = str(item.get("version") or "latest")
            lines.append(f"- `{key}` ({version})")
    if role_dependencies:
        lines.extend(["", "## Role Dependencies", ""])
        for item in role_dependencies:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("name") or "unknown")
            version = str(item.get("version") or "latest")
            lines.append(f"- `{key}` ({version})")

    conflicts = (
        dependencies.get("conflicts", []) if isinstance(dependencies, dict) else []
    )
    if conflicts:
        lines.extend(["", "## Dependency Conflicts", ""])
        for conflict in conflicts:
            if not isinstance(conflict, dict):
                continue
            key = str(conflict.get("key") or "unknown")
            versions = ", ".join(str(v) for v in conflict.get("versions", []))
            lines.append(f"- `{key}`: {versions}")

    roles = payload.get("roles", []) if isinstance(payload, dict) else []
    if roles:
        lines.extend(["", "## Roles", ""])
        sorted_roles = sorted(
            (entry for entry in roles if isinstance(entry, dict)),
            key=lambda entry: str(entry.get("role") or ""),
        )
        bounded_roles, role_overflow = _bounded_list(sorted_roles, max_role_rows)
        for entry in bounded_roles:
            if not isinstance(entry, dict):
                continue
            role_name = str(entry.get("role") or "unknown")
            role_payload = _as_dict(entry.get("payload", {}))
            scanner_counters = _as_dict(
                _as_dict(role_payload.get("metadata", {})).get("scanner_counters", {})
            )
            tasks = int(scanner_counters.get("task_files") or 0)
            templates = int(scanner_counters.get("templates") or 0)
            lines.append(
                f"- [{role_name}](roles/{role_name}.md): task_files={tasks}, templates={templates}"
            )
        if role_overflow:
            lines.append(f"- ... and {role_overflow} more roles")

    plugin_catalog = (
        payload.get("plugin_catalog", {}) if isinstance(payload, dict) else {}
    )
    plugin_summary = _as_dict(plugin_catalog.get("summary", {}))
    plugins_by_type = _as_dict(plugin_catalog.get("by_type", {}))
    plugin_failures = plugin_catalog.get("failures", [])
    if plugin_summary or plugins_by_type:
        lines.extend(["", "## Plugin Catalog", ""])
        lines.append(
            f"- Total plugins: {int(plugin_summary.get('total_plugins') or 0)}"
        )
        lines.append(
            f"- Files scanned: {int(plugin_summary.get('files_scanned') or 0)}"
        )
        lines.append(f"- Files failed: {int(plugin_summary.get('files_failed') or 0)}")

        non_empty_types = [
            plugin_type
            for plugin_type, records in plugins_by_type.items()
            if isinstance(records, list) and records
        ]
        if non_empty_types:
            lines.append(f"- Types present: {', '.join(non_empty_types)}")

        type_rows: list[dict] = []
        for plugin_type, records in plugins_by_type.items():
            if not isinstance(records, list):
                continue
            type_rows.append({"type": str(plugin_type), "count": len(records)})
        type_rows.sort(key=lambda item: item["type"])
        bounded_rows, overflow = _bounded_list(type_rows, max_plugin_rows)
        if bounded_rows:
            lines.extend(["", "### Plugin Types", ""])
            for row in bounded_rows:
                lines.append(f"- `{row['type']}`: {row['count']}")
        if overflow:
            lines.append(f"- ... and {overflow} more plugin types")

        filters = plugins_by_type.get("filter", [])
        if isinstance(filters, list) and filters:
            lines.extend(["", "### Filter Capabilities", ""])
            sorted_filters = sorted(
                (record for record in filters if isinstance(record, dict)),
                key=lambda record: str(record.get("name") or ""),
            )
            bounded_filters, filter_overflow = _bounded_list(
                sorted_filters,
                max_filter_rows,
            )
            for record in bounded_filters:
                plugin_name = str(record.get("name") or "unknown")
                symbols = record.get("symbols", [])
                if isinstance(symbols, list) and symbols:
                    symbol_text = ", ".join(str(symbol) for symbol in symbols[:6])
                    if len(symbols) > 6:
                        symbol_text += ", ..."
                else:
                    symbol_text = "(none discovered)"
                confidence = str(record.get("confidence") or "unknown")
                lines.append(f"- `{plugin_name}` [{confidence}]: {symbol_text}")
            if filter_overflow:
                lines.append(f"- ... and {filter_overflow} more filter plugins")

        if isinstance(plugin_failures, list) and plugin_failures:
            lines.extend(["", "### Plugin Scan Failures", ""])
            for failure in plugin_failures:
                if not isinstance(failure, dict):
                    continue
                relpath = str(failure.get("relative_path") or "unknown")
                stage = str(failure.get("stage") or "unknown")
                error = str(failure.get("error") or "unknown error")
                lines.append(f"- `{relpath}` ({stage}): {error}")

    failures = payload.get("failures", []) if isinstance(payload, dict) else []
    if failures:
        lines.extend(["", "## Role Scan Failures", ""])
        sorted_failures = sorted(
            (failure for failure in failures if isinstance(failure, dict)),
            key=lambda failure: str(failure.get("role") or ""),
        )
        bounded_failures, failure_overflow = _bounded_list(
            sorted_failures,
            max_failure_rows,
        )
        for failure in bounded_failures:
            if not isinstance(failure, dict):
                continue
            role_name = str(failure.get("role") or "unknown")
            error = str(failure.get("error") or "unknown error")
            lines.append(f"- `{role_name}`: {error}")
        if failure_overflow:
            lines.append(f"- ... and {failure_overflow} more role failures")

    lines.append("")
    return "\n".join(lines)


def _add_shared_scan_arguments(parser: argparse.ArgumentParser) -> None:
    """Add scan-related options shared by role, collection, and repo modes."""
    parser.add_argument(
        "--compare-role-path",
        default=None,
        help="Optional local role path used as a baseline comparison in the generated review.",
    )
    parser.add_argument(
        "--style-readme",
        default=None,
        help="Optional local README path used as a style guide for section order and headings.",
    )
    parser.add_argument(
        "--style-source",
        default=None,
        help=(
            "Explicit style source markdown path used when resolving style-guide skeletons "
            "or as fallback style input when --style-readme is not provided."
        ),
    )
    parser.add_argument(
        "--create-style-guide",
        action="store_true",
        help=(
            "Generate a style-guide skeleton README that keeps only section headings/order. "
            "When used without --style-readme, style source is resolved from env/cwd/XDG/system/bundled defaults."
        ),
    )
    parser.add_argument(
        "--vars-context-path",
        action="append",
        default=None,
        help=(
            "Optional external variable context file or directory (can be passed multiple times), "
            "for example group_vars/ to improve required/undocumented variable detection. "
            "Context paths are treated as non-authoritative hints."
        ),
    )
    parser.add_argument(
        "--vars-seed",
        action="append",
        default=None,
        help=(
            "Deprecated alias for --vars-context-path. Optional vars seed file or directory "
            "(can be passed multiple times), for example group_vars/ to prime "
            "required/undocumented variable detection."
        ),
    )
    parser.add_argument(
        "--concise-readme",
        action="store_true",
        help="Keep README concise and write scanner-heavy sections to a sidecar report.",
    )
    parser.add_argument(
        "--scanner-report-output",
        default=None,
        help="Optional output path for scanner sidecar report in concise mode.",
    )
    parser.add_argument(
        "--include-scanner-report-link",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Include a scanner report section/link in concise README output "
            "(use --no-include-scanner-report-link to hide it)."
        ),
    )
    parser.add_argument(
        "--variable-sources",
        choices=("defaults+vars", "defaults-only"),
        default="defaults-only",
        help=(
            "Select which role variable files are documented: "
            "'defaults-only' (default) or 'defaults+vars'."
        ),
    )
    parser.add_argument(
        "--readme-config",
        default=None,
        help=(
            "Optional YAML config controlling README section visibility "
            "(defaults to <role>/.prism.yml when present)."
        ),
    )
    parser.add_argument(
        "--policy-config",
        default=None,
        help=(
            "Optional pattern-policy override YAML path used during scanning "
            "(highest precedence over env/cwd/XDG/system policy sources)."
        ),
    )
    parser.add_argument(
        "--fail-on-unconstrained-dynamic-includes",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Fail scan when unconstrained dynamic includes are detected "
            "(include_tasks/import_tasks/include_role/import_role). "
            "Overrides scan.fail_on_unconstrained_dynamic_includes from .prism.yml "
            "when explicitly set."
        ),
    )
    parser.add_argument(
        "--fail-on-yaml-like-task-annotations",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Fail scan when YAML-like marker comment payloads are detected "
            "(for example key: value). Overrides "
            "scan.fail_on_yaml_like_task_annotations from .prism.yml "
            "when explicitly set."
        ),
    )
    parser.add_argument(
        "--ignore-unresolved-internal-underscore-references",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Suppress unresolved variable findings for underscore-prefixed "
            "internal names (for example _tmp, __state). Overrides "
            "scan.ignore_unresolved_internal_underscore_references from .prism.yml "
            "when explicitly set."
        ),
    )
    parser.add_argument(
        "--adopt-heading-mode",
        choices=("canonical", "style", "popular"),
        default=None,
        help=(
            "Section heading mode when using README config include_sections: "
            "canonical (default), style (use include_sections labels), or popular "
            "(use bundled display titles). Can also be set via "
            "readme.adopt_heading_mode in .prism.yml."
        ),
    )
    parser.add_argument(
        "--keep-unknown-style-sections",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Keep unmapped headings from style README sources as placeholder sections "
            "(enabled by default; use --no-keep-unknown-style-sections to suppress)."
        ),
    )
    parser.add_argument(
        "--exclude-path",
        action="append",
        default=None,
        help=(
            "Exclude role-relative paths or glob patterns from analysis "
            "(can be passed multiple times; examples: templates/*, tests/**, vars/main.yml)."
        ),
    )
    parser.add_argument(
        "--detailed-catalog",
        action="store_true",
        help="Include detailed task and handler tables in generated README sections.",
    )
    parser.add_argument(
        "--task-parameters",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include compact task parameter values in detailed task summary tables.",
    )
    parser.add_argument(
        "--task-runbooks",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Render task runbook/comment details when task annotations are present.",
    )
    parser.add_argument(
        "--inline-task-runbooks",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Inline short runbook snippets in the task summary table.",
    )
    parser.add_argument(
        "--runbook-output",
        default=None,
        help=(
            "Generate a standalone runbook markdown file. For the 'role' command, "
            "provide a file path (e.g. RUNBOOK.md). For 'collection' and 'repo' commands, "
            "provide a directory path; per-role runbook files will be written there."
        ),
    )
    parser.add_argument(
        "--runbook-csv-output",
        default=None,
        help=(
            "Generate runbook CSV output (columns: file, task_name, step). "
            "For the 'role' command, provide a file path (e.g. RUNBOOK.csv). "
            "For 'collection' and 'repo' commands, provide a directory path; "
            "per-role CSV files will be written there."
        ),
    )
    parser.add_argument(
        "--include-collection-checks",
        action="store_true",
        help="Include collection compliance audit notes in requirements sections (off by default).",
    )
    parser.add_argument(
        "--feedback-from-learn",
        default=None,
        help=(
            "Optional feedback source for guided audit recommendations from prism-learn. "
            "Can be a local file path (feedback.json) or HTTPS API endpoint URL. "
            "Feedback can override CLI flags based on aggregate role analysis."
        ),
    )


def _add_common_output_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_template: bool,
    format_choices: tuple[str, ...],
) -> None:
    """Add shared output/rendering options to a parser."""
    parser.add_argument(
        "-o", "--output", default="README.md", help="Output README file path"
    )
    if include_template:
        parser.add_argument(
            "-t",
            "--template",
            default=None,
            help="Template path (optional). If omitted, uses bundled template.",
        )
    parser.add_argument(
        "-f",
        "--format",
        default=format_choices[0],
        choices=format_choices,
        help=f"Output format ({', '.join(format_choices)}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render output without writing files; prints the rendered result to stdout.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )


def _add_repo_arguments(parser: argparse.ArgumentParser) -> None:
    """Add repository-scan specific arguments."""
    parser.add_argument(
        "--repo-url",
        required=True,
        help="GitHub/Git repository URL to clone and scan.",
    )
    parser.add_argument(
        "--repo-ref",
        default=None,
        help="Optional branch, tag, or ref to clone from the repository.",
    )
    parser.add_argument(
        "--repo-role-path",
        default=".",
        help="Role path inside the cloned repository (default: repository root).",
    )
    parser.add_argument(
        "--repo-timeout",
        type=int,
        default=60,
        help="Timeout in seconds for repository clone operations (default: 60).",
    )
    parser.add_argument(
        "--repo-style-readme-path",
        default=None,
        help="Optional README path inside a cloned repository to use as a style guide.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    The parser is organized around distinct role, collection, repo, and
    completion workflows.
    """
    p = argparse.ArgumentParser(
        prog="prism",
        description="Generate documentation for Ansible roles and collections.",
    )
    subparsers = p.add_subparsers(dest="command")
    subparsers.required = True

    role_parser = subparsers.add_parser("role", help="Document a local role")
    role_parser.add_argument(
        "role_path", help="Path to the Ansible role directory to scan"
    )
    _add_shared_scan_arguments(role_parser)
    _add_common_output_arguments(
        role_parser,
        include_template=True,
        format_choices=("md", "html", "json", "pdf"),
    )

    collection_parser = subparsers.add_parser(
        "collection", help="Document a local Ansible collection root"
    )
    collection_parser.add_argument(
        "collection_path",
        help="Path to the Ansible collection root (requires galaxy.yml and roles/)",
    )
    _add_shared_scan_arguments(collection_parser)
    _add_common_output_arguments(
        collection_parser,
        include_template=False,
        format_choices=("md", "json"),
    )

    repo_parser = subparsers.add_parser(
        "repo", help="Document a role from a repository source"
    )
    _add_repo_arguments(repo_parser)
    _add_shared_scan_arguments(repo_parser)
    _add_common_output_arguments(
        repo_parser,
        include_template=True,
        format_choices=("md", "html", "json", "pdf"),
    )

    completion_parser = subparsers.add_parser(
        "completion", help="Generate shell completion output"
    )
    completion_parser.add_argument(
        "shell", choices=("bash",), help="Shell to generate completion for"
    )
    return p


def _collect_option_strings(parser: argparse.ArgumentParser) -> list[str]:
    """Collect sorted unique option strings for a parser."""
    options: set[str] = set()
    for action in parser._actions:
        for option in getattr(action, "option_strings", []):
            if option in {"-h", "--help"}:
                continue
            options.add(option)
    return sorted(options)


def _build_bash_completion_script() -> str:
    """Generate a bash completion script from the live parser structure."""
    parser = build_parser()
    subparsers_action = next(
        (
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ),
        None,
    )
    if subparsers_action is None:
        raise RuntimeError("subcommand parser is not configured")

    commands = sorted(subparsers_action.choices)
    command_words = " ".join(commands)

    command_options: dict[str, str] = {}
    for command in commands:
        subparser = subparsers_action.choices[command]
        words: list[str] = []
        words.extend(_collect_option_strings(subparser))
        for action in subparser._actions:
            if action.option_strings:
                continue
            if action.dest == "help":
                continue
            if isinstance(action.choices, (list, tuple)):
                words.extend(str(choice) for choice in action.choices)
        command_options[command] = " ".join(sorted(set(words)))

    case_lines: list[str] = []
    for command in commands:
        options = command_options.get(command, "")
        case_lines.extend(
            [
                f"        {command})",
                f'            opts="{options}"',
                "            ;;",
            ]
        )

    script = [
        "# prism bash completion (generated)",
        "_prism_completion() {",
        "    local cur prev cmd opts",
        "    COMPREPLY=()",
        '    cur="${COMP_WORDS[COMP_CWORD]}"',
        '    prev="${COMP_WORDS[COMP_CWORD-1]}"',
        '    cmd="${COMP_WORDS[1]}"',
        "",
        "    if [[ ${COMP_CWORD} -eq 1 ]]; then",
        f'        COMPREPLY=( $(compgen -W "{command_words}" -- "$cur") )',
        "        return 0",
        "    fi",
        "",
        '    case "$cmd" in',
        *case_lines,
        "        *)",
        '            opts=""',
        "            ;;",
        "    esac",
        "",
        '    if [[ "$cur" == -* ]]; then',
        '        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )',
        "        return 0",
        "    fi",
        "",
        '    if [[ "$cmd" == "completion" && ${COMP_CWORD} -eq 2 ]]; then',
        '        COMPREPLY=( $(compgen -W "bash" -- "$cur") )',
        "        return 0",
        "    fi",
        "",
        '    COMPREPLY=( $(compgen -f -- "$cur") )',
        "}",
        "complete -F _prism_completion prism",
        "",
    ]
    return "\n".join(script)


def _resolve_effective_readme_config(
    role_path: Path,
    explicit_config_path: str | None,
) -> str | None:
    """Return the configured or auto-discovered README config path."""
    if explicit_config_path:
        return explicit_config_path
    for cfg_name in SECTION_CONFIG_FILENAMES:
        default_cfg = role_path / cfg_name
        if default_cfg.is_file():
            return str(default_cfg)
    return None


def _emit_success(
    args: argparse.Namespace,
    outpath: str,
    style_source_path: str | None = None,
    style_demo_path: str | None = None,
) -> int:
    """Emit verbose success details and return a successful exit code."""
    if args.verbose:
        if args.dry_run:
            print("\nDry run: no files written.")
        else:
            print("Wrote:", outpath)
        if style_source_path:
            print("Style guide source:", style_source_path)
        if style_demo_path:
            print("Generated demo copy:", style_demo_path)
    return 0


def _resolve_vars_context_paths(args: argparse.Namespace) -> list[str] | None:
    """Resolve context paths from new and legacy flags with deprecation warning."""
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


def _resolve_include_collection_checks(
    feedback_source: str | None,
    include_collection_checks: bool,
) -> bool | None:
    """Load feedback and resolve the effective collection-checks flag."""
    try:
        feedback = load_feedback(feedback_source)
    except (
        FileNotFoundError,
        HTTPError,
        URLError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"Error loading feedback: {exc}", file=sys.stderr)
        return None

    applied = apply_feedback_recommendations(feedback, include_collection_checks)
    return bool(applied["include_collection_checks"])


def _normalize_repo_json_payload(
    rendered_payload: str,
    *,
    repo_style_readme_path: str | None,
    scanner_report_relpath: str | None,
) -> str:
    """Normalize repo-backed JSON payload metadata paths when parseable."""
    normalized_payload = _normalize_repo_scan_result_payload(
        rendered_payload,
        repo_style_readme_path=repo_style_readme_path,
        scanner_report_relpath=scanner_report_relpath,
    )
    if isinstance(normalized_payload, str):
        return normalized_payload
    return rendered_payload


def _handle_repo_command(args: argparse.Namespace) -> int:
    """Handle repository-backed role documentation."""
    vars_context_paths = _resolve_vars_context_paths(args)

    with _repo_scan_workspace() as workspace:
        if args.verbose:
            print(f"Cloning: {args.repo_url}")
        checkout = _checkout_repo_scan_role(
            args.repo_url,
            workspace=workspace,
            repo_role_path=args.repo_role_path,
            repo_style_readme_path=args.repo_style_readme_path,
            style_readme_path=args.style_readme,
            repo_ref=args.repo_ref,
            repo_timeout=args.repo_timeout,
            prepare_repo_scan_inputs=_prepare_repo_scan_inputs,
            fetch_repo_directory_names=_fetch_repo_directory_names,
            repo_path_looks_like_role=_repo_path_looks_like_role,
            fetch_repo_file=_fetch_repo_file,
            clone_repo=_clone_repo,
            build_sparse_clone_paths=_build_sparse_clone_paths,
            resolve_style_readme_candidate=_resolve_style_readme_candidate,
        )
        style_readme_path = checkout.effective_style_readme_path
        if args.create_style_guide and not style_readme_path:
            style_readme_path = (
                args.style_source or resolve_default_style_guide_source()
            )

        include_collection_checks = _resolve_include_collection_checks(
            args.feedback_from_learn,
            args.include_collection_checks,
        )
        if include_collection_checks is None:
            return 1

        outpath = run_scan(
            str(checkout.role_path),
            output=args.output,
            template=args.template,
            output_format=args.format,
            compare_role_path=args.compare_role_path,
            style_readme_path=style_readme_path,
            role_name_override=_repo_name_from_url(args.repo_url),
            vars_seed_paths=vars_context_paths,
            concise_readme=args.concise_readme,
            scanner_report_output=args.scanner_report_output,
            include_vars_main=args.variable_sources == "defaults+vars",
            include_scanner_report_link=args.include_scanner_report_link,
            readme_config_path=args.readme_config,
            adopt_heading_mode=args.adopt_heading_mode,
            style_guide_skeleton=args.create_style_guide,
            keep_unknown_style_sections=args.keep_unknown_style_sections,
            exclude_path_patterns=args.exclude_path,
            style_source_path=args.style_source,
            policy_config_path=args.policy_config,
            fail_on_unconstrained_dynamic_includes=args.fail_on_unconstrained_dynamic_includes,
            fail_on_yaml_like_task_annotations=args.fail_on_yaml_like_task_annotations,
            ignore_unresolved_internal_underscore_references=args.ignore_unresolved_internal_underscore_references,
            detailed_catalog=args.detailed_catalog,
            include_collection_checks=include_collection_checks,
            include_task_parameters=args.task_parameters,
            include_task_runbooks=args.task_runbooks,
            inline_task_runbooks=args.inline_task_runbooks,
            runbook_output=args.runbook_output,
            runbook_csv_output=args.runbook_csv_output,
            dry_run=args.dry_run,
        )
        if args.format == "json":
            scanner_report_relpath = _resolve_repo_scan_scanner_report_relpath(
                concise_readme=args.concise_readme,
                scanner_report_output=args.scanner_report_output,
                primary_output_path=args.output,
            )
            if args.dry_run:
                outpath = _normalize_repo_json_payload(
                    outpath,
                    repo_style_readme_path=checkout.resolved_repo_style_readme_path,
                    scanner_report_relpath=scanner_report_relpath,
                )
            else:
                output_path = Path(outpath)
                try:
                    raw_payload = output_path.read_text(encoding="utf-8")
                except OSError:
                    raw_payload = ""
                normalized_payload = _normalize_repo_json_payload(
                    raw_payload,
                    repo_style_readme_path=checkout.resolved_repo_style_readme_path,
                    scanner_report_relpath=scanner_report_relpath,
                )
                if normalized_payload and normalized_payload != raw_payload:
                    output_path.write_text(normalized_payload, encoding="utf-8")

        if args.dry_run:
            print(outpath, end="")
            return _emit_success(args, outpath)

        effective_readme_config_path = _resolve_effective_readme_config(
            checkout.role_path,
            args.readme_config,
        )
        style_source_path, style_demo_path = _save_style_comparison_artifacts(
            style_readme_path,
            outpath,
            _repo_name_from_url(args.repo_url),
            effective_readme_config_path,
            args.keep_unknown_style_sections,
        )
        return _emit_success(args, outpath, style_source_path, style_demo_path)


def _handle_collection_command(args: argparse.Namespace) -> int:
    """Handle local collection-root documentation."""
    from .api import scan_collection

    vars_context_paths = _resolve_vars_context_paths(args)

    include_collection_checks = _resolve_include_collection_checks(
        args.feedback_from_learn,
        args.include_collection_checks,
    )
    if include_collection_checks is None:
        return 1

    payload = scan_collection(
        args.collection_path,
        compare_role_path=args.compare_role_path,
        style_readme_path=args.style_readme,
        vars_seed_paths=vars_context_paths,
        concise_readme=args.concise_readme,
        scanner_report_output=args.scanner_report_output,
        include_vars_main=args.variable_sources == "defaults+vars",
        include_scanner_report_link=args.include_scanner_report_link,
        readme_config_path=args.readme_config,
        adopt_heading_mode=args.adopt_heading_mode,
        style_guide_skeleton=args.create_style_guide,
        keep_unknown_style_sections=args.keep_unknown_style_sections,
        exclude_path_patterns=args.exclude_path,
        style_source_path=args.style_source,
        policy_config_path=args.policy_config,
        fail_on_unconstrained_dynamic_includes=args.fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=args.fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=args.ignore_unresolved_internal_underscore_references,
        detailed_catalog=args.detailed_catalog,
        include_collection_checks=include_collection_checks,
        include_task_parameters=args.task_parameters,
        include_task_runbooks=args.task_runbooks,
        inline_task_runbooks=args.inline_task_runbooks,
        include_rendered_readme=args.format == "md",
        runbook_output_dir=args.runbook_output,
        runbook_csv_output_dir=args.runbook_csv_output,
    )
    rendered = (
        json.dumps(payload, indent=2)
        if args.format == "json"
        else _render_collection_markdown(payload)
    )
    if args.dry_run:
        print(rendered, end="")
        return _emit_success(args, rendered)

    output_path = Path(args.output)
    if args.format == "json" and output_path.suffix.lower() != ".json":
        output_path = output_path.with_suffix(".json")
    if args.format == "md" and output_path.suffix.lower() != ".md":
        output_path = output_path.with_suffix(".md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    if args.format == "md":
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
            (roles_dir / f"{role_name}.md").write_text(
                role_doc,
                encoding="utf-8",
            )
    return _emit_success(args, str(output_path.resolve()))


def _handle_role_command(args: argparse.Namespace) -> int:
    """Handle local role documentation."""
    vars_context_paths = _resolve_vars_context_paths(args)

    include_collection_checks = _resolve_include_collection_checks(
        args.feedback_from_learn,
        args.include_collection_checks,
    )
    if include_collection_checks is None:
        return 1

    style_readme_path = args.style_readme
    if args.create_style_guide and not style_readme_path:
        style_readme_path = args.style_source or resolve_default_style_guide_source()
    outpath = run_scan(
        args.role_path,
        output=args.output,
        template=args.template,
        output_format=args.format,
        compare_role_path=args.compare_role_path,
        style_readme_path=style_readme_path,
        vars_seed_paths=vars_context_paths,
        concise_readme=args.concise_readme,
        scanner_report_output=args.scanner_report_output,
        include_vars_main=args.variable_sources == "defaults+vars",
        include_scanner_report_link=args.include_scanner_report_link,
        readme_config_path=args.readme_config,
        adopt_heading_mode=args.adopt_heading_mode,
        style_guide_skeleton=args.create_style_guide,
        keep_unknown_style_sections=args.keep_unknown_style_sections,
        exclude_path_patterns=args.exclude_path,
        style_source_path=args.style_source,
        policy_config_path=args.policy_config,
        fail_on_unconstrained_dynamic_includes=args.fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=args.fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=args.ignore_unresolved_internal_underscore_references,
        detailed_catalog=args.detailed_catalog,
        include_collection_checks=include_collection_checks,
        include_task_parameters=args.task_parameters,
        include_task_runbooks=args.task_runbooks,
        inline_task_runbooks=args.inline_task_runbooks,
        runbook_output=args.runbook_output,
        runbook_csv_output=args.runbook_csv_output,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(outpath, end="")
        return _emit_success(args, outpath)

    effective_readme_config_path = _resolve_effective_readme_config(
        Path(args.role_path),
        args.readme_config,
    )
    style_source_path, style_demo_path = _save_style_comparison_artifacts(
        args.style_readme,
        outpath,
        role_config_path=effective_readme_config_path,
        keep_unknown_style_sections=args.keep_unknown_style_sections,
    )
    return _emit_success(args, outpath, style_source_path, style_demo_path)


def _handle_completion_command(args: argparse.Namespace) -> int:
    """Handle shell completion generation requests."""
    if args.shell != "bash":
        print(
            f"Error: unsupported completion shell: {args.shell}",
            file=sys.stderr,
        )
        return 2
    print(_build_bash_completion_script(), end="")
    return 0


def _clone_repo(
    repo_url: str,
    destination: Path,
    ref: str | None = None,
    timeout: int = 60,
    sparse_paths: list[str] | None = None,
    allow_sparse_fallback_to_full: bool = True,
) -> None:
    """Compatibility shim backed by ``repo_services._clone_repo``."""
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
    """Compatibility shim backed by ``repo_services._github_repo_from_url``."""
    return _repo_github_repo_from_url(repo_url)


def _normalize_repo_path(repo_path: str | None) -> str:
    """Compatibility shim backed by ``repo_services._normalize_repo_path``."""
    return _repo_normalize_repo_path(repo_path)


def _fetch_repo_contents_payload(
    repo_url: str,
    repo_path: str | None = None,
    ref: str | None = None,
    timeout: int = 60,
    *,
    opener=urlopen,
) -> dict | list | None:
    """Compatibility shim backed by ``repo_services._fetch_repo_contents_payload``."""
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
    """Compatibility shim backed by ``repo_services._fetch_repo_directory_names``."""
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
    """Compatibility shim backed by ``repo_services._fetch_repo_file``."""
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
    """Save source/demo comparison artifacts beside generated output."""
    if not style_readme_path:
        return None, None

    source = Path(style_readme_path)
    if not source.is_file():
        raise FileNotFoundError(f"style README not found: {style_readme_path}")

    output_path = Path(generated_output)
    style_slug = style_source_name or source.stem
    if style_slug.lower() in {"readme", "source_style_guide", "style_guide_source"}:
        style_slug = source.parent.name or style_slug
    style_slug = re.sub(r"^style_", "", style_slug, flags=re.IGNORECASE)
    style_slug = re.sub(
        r"\.source_style_guide$|\.style_guide_source$",
        "",
        style_slug,
        flags=re.IGNORECASE,
    )
    style_slug = (
        re.sub(r"[^a-zA-Z0-9]+", "_", style_slug).strip("_").lower() or "style_guide"
    )
    expected_style_dir_name = f"style_{style_slug}"
    if output_path.parent.name == expected_style_dir_name:
        style_dir = output_path.parent
    else:
        style_dir = output_path.parent / expected_style_dir_name
    style_dir.mkdir(parents=True, exist_ok=True)

    source_suffix = source.suffix or ".md"
    source_destination = style_dir / f"SOURCE_STYLE_GUIDE{source_suffix}"
    if source.resolve() != source_destination.resolve():
        shutil.copyfile(source, source_destination)

    output_suffix = output_path.suffix or ".md"
    demo_destination = style_dir / f"DEMO_GENERATED{output_suffix}"
    if output_path.resolve() != demo_destination.resolve():
        shutil.copyfile(output_path, demo_destination)

    if keep_unknown_style_sections:
        keep_demo_destination = (
            style_dir / f"DEMO_GENERATED_KEEP_UNKNOWN{output_suffix}"
        )
        if output_path.resolve() != keep_demo_destination.resolve():
            shutil.copyfile(output_path, keep_demo_destination)

    cfg_destination = style_dir / "ROLE_README_CONFIG.yml"

    # Include the role-level README config beside demo artifacts when available.
    if role_config_path:
        cfg_source = Path(role_config_path)
        if cfg_source.is_file():
            if cfg_source.resolve() != cfg_destination.resolve():
                shutil.copyfile(cfg_source, cfg_destination)
            return str(source_destination.resolve()), str(demo_destination.resolve())

    # If a role config is not present, synthesize a source-of-truth config sample
    # showing unknown style headings captured from the style guide.
    parsed = parse_style_readme(str(source))
    unknown_sections: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    total_chars = 0
    truncated_any = False

    for section in parsed.get("sections", []):
        if section.get("id") != "unknown":
            continue
        if len(unknown_sections) >= _CAPTURE_MAX_SECTIONS:
            truncated_any = True
            break

        title = str(section.get("title") or "").strip()
        key = re.sub(r"\\s+", " ", title).lower()
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)

        body = str(section.get("body") or "").strip()
        body = _sanitize_captured_content(body)
        body, truncated_one = _truncate_content(body, _CAPTURE_MAX_CONTENT_CHARS)
        if truncated_one:
            truncated_any = True

        proposed_chars = total_chars + len(title) + len(body)
        if proposed_chars > _CAPTURE_MAX_TOTAL_CHARS:
            remaining = max(0, _CAPTURE_MAX_TOTAL_CHARS - total_chars - len(title))
            body, _ = _truncate_content(body, remaining)
            truncated_any = True

        unknown_sections.append({"title": title, "content": body})
        total_chars += len(title) + len(body)

        if total_chars >= _CAPTURE_MAX_TOTAL_CHARS:
            break

    unknown_sections.sort(key=lambda row: row["title"].lower())

    payload = {
        "readme": {
            "capture_metadata": {
                "schema_version": _CAPTURE_SCHEMA_VERSION,
                "captured_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "style_source_path": str(source),
                "truncated": truncated_any,
            },
            "unknown_style_sections": unknown_sections,
        }
    }
    cfg_lines = [
        "# Auto-generated sample: promote this file into the role as .prism.yml",
        "# to keep unknown style sections as your source-of-truth.",
        yaml.dump(
            payload,
            Dumper=_ReadableYamlDumper,
            sort_keys=False,
            default_flow_style=False,
            width=10000,
        ).rstrip(),
        "",
    ]
    rendered_cfg = "\n".join(cfg_lines)
    existing_cfg = (
        cfg_destination.read_text(encoding="utf-8")
        if cfg_destination.exists()
        else None
    )
    if existing_cfg != rendered_cfg:
        cfg_destination.write_text(rendered_cfg, encoding="utf-8")

    return str(source_destination.resolve()), str(demo_destination.resolve())


def main(argv=None) -> int:
    """CLI entrypoint.

    ``argv`` may be provided for testing; returns an exit code integer.
    """
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
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
