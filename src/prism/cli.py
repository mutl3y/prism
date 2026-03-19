"""CLI entry point for prism.

Provides a small CLI wrapper around :func:`prism.scanner.run_scan`.
"""

from __future__ import annotations
import base64
import argparse
from contextlib import contextmanager
from datetime import datetime, UTC
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import sys
import tempfile
import yaml
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

_ROLE_MARKER_DIRS = frozenset(
    {"defaults", "files", "handlers", "meta", "tasks", "templates", "tests", "vars"}
)
_MIN_ROLE_MARKER_DIRS = 3
_REQUIRED_ROLE_DIRS = frozenset({"defaults", "tasks", "meta"})
_SHARED_TMP_ROOT_NAME = "prism"


@contextmanager
def _repo_scan_workspace():
    """Yield a repo-scan workspace under a shared temp root and clean it up."""
    shared_root = Path(tempfile.gettempdir()) / _SHARED_TMP_ROOT_NAME
    shared_root.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="scan-", dir=shared_root))
    try:
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        try:
            if shared_root.exists() and not any(shared_root.iterdir()):
                shared_root.rmdir()
        except OSError:
            pass


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
                lines.append(
                    f"- `{plugin_name}` [{confidence}]: {symbol_text}"
                )
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
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")


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
    role_parser.add_argument("role_path", help="Path to the Ansible role directory to scan")
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

    repo_parser = subparsers.add_parser("repo", help="Document a role from a repository source")
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
    completion_parser.add_argument("shell", choices=("bash",), help="Shell to generate completion for")
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
        '    COMPREPLY=()',
        '    cur="${COMP_WORDS[COMP_CWORD]}"',
        '    prev="${COMP_WORDS[COMP_CWORD-1]}"',
        '    cmd="${COMP_WORDS[1]}"',
        "",
        "    if [[ ${COMP_CWORD} -eq 1 ]]; then",
        f'        COMPREPLY=( $(compgen -W "{command_words}" -- "$cur") )',
        "        return 0",
        "    fi",
        "",
        "    case \"$cmd\" in",
        *case_lines,
        "        *)",
        '            opts=""',
        "            ;;",
        "    esac",
        "",
        "    if [[ \"$cur\" == -* ]]; then",
        '        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )',
        "        return 0",
        "    fi",
        "",
        "    if [[ \"$cmd\" == \"completion\" && ${COMP_CWORD} -eq 2 ]]; then",
        '        COMPREPLY=( $(compgen -W "bash" -- "$cur") )',
        "        return 0",
        "    fi",
        "",
        "    COMPREPLY=( $(compgen -f -- \"$cur\") )",
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


def _handle_repo_command(args: argparse.Namespace) -> int:
    """Handle repository-backed role documentation."""
    vars_context_paths = _resolve_vars_context_paths(args)

    with _repo_scan_workspace() as workspace:
        checkout_dir = workspace / "repo"
        repo_dir_names = _fetch_repo_directory_names(
            args.repo_url,
            repo_path=args.repo_role_path,
            ref=args.repo_ref,
            timeout=args.repo_timeout,
        )
        if repo_dir_names is not None and not _repo_path_looks_like_role(repo_dir_names):
            raise FileNotFoundError(
                "repository path does not look like an Ansible role: "
                f"{args.repo_role_path}"
            )
        style_candidates = _build_repo_style_readme_candidates(
            args.repo_style_readme_path
        )
        fetched_repo_style_readme_path = None
        for style_candidate in style_candidates:
            fetched_repo_style_readme_path = _fetch_repo_file(
                args.repo_url,
                style_candidate,
                workspace / "repo-style-readme" / Path(style_candidate).name,
                ref=args.repo_ref,
                timeout=args.repo_timeout,
            )
            if fetched_repo_style_readme_path is not None:
                break
        if args.verbose:
            print(f"Cloning: {args.repo_url}")
        _clone_repo(
            args.repo_url,
            checkout_dir,
            args.repo_ref,
            args.repo_timeout,
            sparse_paths=_build_sparse_clone_paths(
                args.repo_role_path,
                (
                    None
                    if fetched_repo_style_readme_path is not None
                    else style_candidates
                ),
            ),
        )
        role_path = (checkout_dir / args.repo_role_path).resolve()
        if not role_path.exists() or not role_path.is_dir():
            raise FileNotFoundError(
                f"role path not found in cloned repository: {args.repo_role_path}"
            )
        style_readme_path = args.style_readme
        if fetched_repo_style_readme_path is not None:
            style_readme_path = str(fetched_repo_style_readme_path.resolve())
        elif style_candidates:
            for style_candidate in style_candidates:
                candidate_path = (checkout_dir / style_candidate).resolve()
                if candidate_path.is_file():
                    style_readme_path = str(candidate_path)
                    break
        if args.create_style_guide and not style_readme_path:
            style_readme_path = args.style_source or resolve_default_style_guide_source()

        # Load optional feedback from prism-learn to guide scanner behavior
        try:
            feedback = load_feedback(args.feedback_from_learn)
        except (FileNotFoundError, HTTPError, URLError, json.JSONDecodeError, ValueError) as exc:
            print(f"Error loading feedback: {exc}", file=sys.stderr)
            return 1

        # Apply feedback recommendations to override CLI flags if recommended
        applied = apply_feedback_recommendations(
            feedback, args.include_collection_checks
        )
        include_collection_checks = applied["include_collection_checks"]

        outpath = run_scan(
            str(role_path),
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
            detailed_catalog=args.detailed_catalog,
            include_collection_checks=include_collection_checks,
            include_task_parameters=args.task_parameters,
            include_task_runbooks=args.task_runbooks,
            inline_task_runbooks=args.inline_task_runbooks,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            print(outpath, end="")
            return _emit_success(args, outpath)

        effective_readme_config_path = _resolve_effective_readme_config(
            role_path,
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

    # Load optional feedback from prism-learn to guide scanner behavior
    try:
        feedback = load_feedback(args.feedback_from_learn)
    except (FileNotFoundError, HTTPError, URLError, json.JSONDecodeError, ValueError) as exc:
        print(f"Error loading feedback: {exc}", file=sys.stderr)
        return 1

    # Apply feedback recommendations to override CLI flags if recommended
    applied = apply_feedback_recommendations(
        feedback, args.include_collection_checks
    )
    include_collection_checks = applied["include_collection_checks"]

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
        detailed_catalog=args.detailed_catalog,
        include_collection_checks=include_collection_checks,
        include_task_parameters=args.task_parameters,
        include_task_runbooks=args.task_runbooks,
        inline_task_runbooks=args.inline_task_runbooks,
        include_rendered_readme=args.format == "md",
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

    # Load optional feedback from prism-learn to guide scanner behavior
    try:
        feedback = load_feedback(args.feedback_from_learn)
    except (FileNotFoundError, HTTPError, URLError, json.JSONDecodeError, ValueError) as exc:
        print(f"Error loading feedback: {exc}", file=sys.stderr)
        return 1

    # Apply feedback recommendations to override CLI flags if recommended
    applied = apply_feedback_recommendations(
        feedback, args.include_collection_checks
    )
    include_collection_checks = applied["include_collection_checks"]

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
        detailed_catalog=args.detailed_catalog,
        include_collection_checks=include_collection_checks,
        include_task_parameters=args.task_parameters,
        include_task_runbooks=args.task_runbooks,
        inline_task_runbooks=args.inline_task_runbooks,
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
    """Clone a git repository into ``destination`` with shallow history.

    When ``sparse_paths`` is provided, first attempt a sparse/partial checkout to
    reduce downloaded content. If sparse setup fails, behavior depends on
    ``allow_sparse_fallback_to_full``.
    """
    parsed = urlparse(repo_url)
    clone_url = repo_url
    if parsed.scheme in {"http", "https"} and parsed.netloc == "github.com":
        repo_path = parsed.path.strip("/")
        if repo_path and repo_path.count("/") >= 1:
            if not repo_path.endswith(".git"):
                repo_path = f"{repo_path}.git"
            clone_url = f"git@github.com:{repo_path}"

    clone_cmd = ["git", "clone", "--depth", "1"]
    if ref:
        clone_cmd.extend(["--branch", ref, "--single-branch"])

    requested_sparse_paths = [
        path.strip() for path in (sparse_paths or []) if path and path.strip()
    ]
    use_sparse_clone = bool(requested_sparse_paths)
    if use_sparse_clone:
        clone_cmd.extend(["--filter=blob:none", "--sparse"])

    clone_cmd.extend([clone_url, str(destination)])

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

    def _run_clone(cmd: list[str]) -> None:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )

    def _run_sparse_checkout(paths: list[str]) -> None:
        sparse_cmd = [
            "git",
            "-C",
            str(destination),
            "sparse-checkout",
            "set",
            "--no-cone",
            *paths,
        ]
        subprocess.run(
            sparse_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )

    try:
        if use_sparse_clone:
            try:
                _run_clone(clone_cmd)
                _run_sparse_checkout(requested_sparse_paths)
                return
            except subprocess.CalledProcessError as sparse_exc:
                shutil.rmtree(destination, ignore_errors=True)
                if not allow_sparse_fallback_to_full:
                    sparse_stderr = (sparse_exc.stderr or "").strip()
                    raise RuntimeError(
                        "repository sparse checkout failed"
                        + (f": {sparse_stderr}" if sparse_stderr else "")
                    ) from sparse_exc

        fallback_cmd = ["git", "clone", "--depth", "1"]
        if ref:
            fallback_cmd.extend(["--branch", ref, "--single-branch"])
        fallback_cmd.extend([clone_url, str(destination)])
        _run_clone(fallback_cmd)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"repository clone timed out after {timeout}s: {repo_url}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(f"repository clone failed: {stderr or repo_url}") from exc


def _repo_name_from_url(repo_url: str) -> str | None:
    """Extract a best-effort repository name from a URL or SSH git URL."""
    parsed = urlparse(repo_url)
    if parsed.scheme in {"http", "https", "ssh"} and parsed.path:
        name = Path(parsed.path).name
        return name.removesuffix(".git") or None
    if repo_url.startswith("git@") and ":" in repo_url:
        path = repo_url.split(":", 1)[1]
        name = Path(path).name
        return name.removesuffix(".git") or None
    return None


def _github_repo_from_url(repo_url: str) -> tuple[str, str] | None:
    """Return ``(owner, repo)`` for GitHub repo URLs when parseable."""
    parsed = urlparse(repo_url)
    repo_path = ""
    if parsed.scheme in {"http", "https", "ssh"} and parsed.netloc == "github.com":
        repo_path = parsed.path.strip("/")
    elif repo_url.startswith("git@github.com:"):
        repo_path = repo_url.split(":", 1)[1].strip("/")

    parts = [segment for segment in repo_path.split("/") if segment]
    if len(parts) < 2:
        return None

    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    if not owner or not repo:
        return None
    return owner, repo


def _normalize_repo_path(repo_path: str | None) -> str:
    """Normalize repository-relative paths used for remote GitHub probes."""
    normalized_repo_path = (repo_path or "").strip().strip("/")
    if normalized_repo_path in {"", "."}:
        return ""
    return normalized_repo_path


def _fetch_repo_contents_payload(
    repo_url: str,
    repo_path: str | None = None,
    ref: str | None = None,
    timeout: int = 60,
) -> dict | list | None:
    """Fetch GitHub contents API payload for a repo path when possible."""
    repo_coords = _github_repo_from_url(repo_url)
    if repo_coords is None:
        return None

    normalized_repo_path = _normalize_repo_path(repo_path)
    owner, repo = repo_coords
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    if normalized_repo_path:
        api_url = f"{api_url}/{quote(normalized_repo_path, safe='/')}"
    if ref:
        api_url = f"{api_url}?ref={quote(ref, safe='')}"

    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github.object",
            "User-Agent": "prism",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (
        HTTPError,
        URLError,
        OSError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None


def _fetch_repo_directory_names(
    repo_url: str,
    repo_path: str | None = None,
    ref: str | None = None,
    timeout: int = 60,
) -> set[str] | None:
    """Fetch directory names for a GitHub repo path when possible."""
    payload = _fetch_repo_contents_payload(
        repo_url,
        repo_path=repo_path,
        ref=ref,
        timeout=timeout,
    )
    if not isinstance(payload, list):
        return None

    dir_names: set[str] = set()
    for entry in payload:
        if not isinstance(entry, dict) or entry.get("type") != "dir":
            continue
        name = entry.get("name")
        if isinstance(name, str) and name:
            dir_names.add(name)
    return dir_names


def _repo_path_looks_like_role(dir_names: set[str] | None) -> bool:
    """Return True when a directory listing looks like a useful role source."""
    if not dir_names:
        return False

    role_markers = _ROLE_MARKER_DIRS & dir_names
    if _REQUIRED_ROLE_DIRS <= role_markers:
        return True
    return False


def _build_repo_style_readme_candidates(
    repo_style_readme_path: str | None,
) -> list[str]:
    """Build deterministic README path candidates for case-variant fallback."""
    normalized = _normalize_repo_path(repo_style_readme_path)
    if not normalized:
        return []

    candidates: list[str] = [normalized]
    path_obj = Path(normalized)
    file_name = path_obj.name
    parent = path_obj.parent.as_posix()
    if parent == ".":
        parent = ""

    if file_name.lower() == "readme.md":
        for variant in ("README.md", "Readme.md", "readme.md"):
            candidate = f"{parent}/{variant}" if parent else variant
            if candidate not in candidates:
                candidates.append(candidate)

    return candidates


def _fetch_repo_file(
    repo_url: str,
    repo_path: str | None,
    destination: Path,
    ref: str | None = None,
    timeout: int = 60,
) -> Path | None:
    """Fetch a single file from GitHub into ``destination`` when possible.

    Returns ``None`` for unsupported hosts or when the remote fetch fails so
    callers can fall back to clone-based resolution.
    """
    normalized_repo_path = _normalize_repo_path(repo_path)
    if not normalized_repo_path:
        return None

    payload = _fetch_repo_contents_payload(
        repo_url,
        repo_path=normalized_repo_path,
        ref=ref,
        timeout=timeout,
    )
    if not isinstance(payload, dict):
        return None

    if payload.get("type") != "file":
        return None

    content = payload.get("content")
    encoding = payload.get("encoding")
    if not isinstance(content, str) or encoding != "base64":
        return None

    try:
        decoded = base64.b64decode(content)
    except ValueError:
        return None

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(decoded)
    return destination


def _build_sparse_clone_paths(
    repo_role_path: str,
    repo_style_readme_path: str | list[str] | None,
) -> list[str]:
    """Build sparse checkout targets for repo-based scans.

    Returns an empty list when sparse checkout would not reduce scope.
    """
    role_path = (repo_role_path or ".").strip()
    if role_path in {"", "."}:
        return []

    paths = [role_path]
    if isinstance(repo_style_readme_path, list):
        paths.extend(
            path.strip() for path in repo_style_readme_path if path and path.strip()
        )
    elif repo_style_readme_path and repo_style_readme_path.strip():
        paths.append(repo_style_readme_path.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


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
        return int(exc.code)

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
