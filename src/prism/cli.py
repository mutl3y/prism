"""CLI entrypoint for the fsrc Prism package lane."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import sys
from urllib.error import HTTPError, URLError

import prism.api as api
from prism.errors import PrismRuntimeError
from prism.scanner_io.collection_renderer import (
    format_collection_summary,
    render_collection_markdown,
)
from prism.scanner_io.output import (
    resolve_output_path,
    write_output,
    write_role_scan_output,
)


CLI_PUBLIC_ENTRYPOINTS: tuple[str, ...] = ("main", "build_parser")
CLI_RETAINED_COMPATIBILITY_SEAMS: tuple[str, ...] = ("_handle_repo_command",)

__all__ = ["main", "build_parser"]

_EXIT_CODE_GENERIC_ERROR = 2
_EXIT_CODE_NOT_FOUND = 3
EXIT_CODE_AUDIT_VIOLATIONS = 2
_EXIT_CODE_PERMISSION_DENIED = 4
_EXIT_CODE_JSON_PAYLOAD_ERROR = 5
_EXIT_CODE_NETWORK_ERROR = 6
_EXIT_CODE_OS_ERROR = 7
_EXIT_CODE_INTERRUPTED = 130


def _add_shared_scan_arguments(parser: argparse.ArgumentParser) -> None:
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
        help="Explicit style source markdown path used when resolving style-guide skeletons.",
    )
    parser.add_argument(
        "--create-style-guide",
        action="store_true",
        help="Generate a style-guide skeleton README that keeps only section headings/order.",
    )
    parser.add_argument(
        "--vars-context-path",
        action="append",
        default=None,
        help="Optional external variable context file or directory (can be passed multiple times).",
    )
    parser.add_argument(
        "--vars-seed",
        action="append",
        default=None,
        help="Deprecated alias for --vars-context-path.",
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
        help="Include a scanner report section/link in concise README output.",
    )
    parser.add_argument(
        "--variable-sources",
        choices=("defaults+vars", "defaults-only"),
        default="defaults-only",
        help="Select which role variable files are documented.",
    )
    parser.add_argument(
        "--readme-config",
        default=None,
        help="Optional YAML config controlling README section visibility.",
    )
    parser.add_argument(
        "--policy-config",
        default=None,
        help="Optional pattern-policy override YAML path used during scanning.",
    )
    parser.add_argument(
        "--fail-on-unconstrained-dynamic-includes",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Fail scan when unconstrained dynamic includes are detected.",
    )
    parser.add_argument(
        "--fail-on-yaml-like-task-annotations",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Fail scan when YAML-like marker comment payloads are detected.",
    )
    parser.add_argument(
        "--ignore-unresolved-internal-underscore-references",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Suppress unresolved variable findings for underscore-prefixed internal names.",
    )
    parser.add_argument(
        "--adopt-heading-mode",
        choices=("canonical", "style", "popular"),
        default=None,
        help="Section heading mode when using README config include_sections.",
    )
    parser.add_argument(
        "--keep-unknown-style-sections",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Keep unmapped headings from style README sources as placeholder sections.",
    )
    parser.add_argument(
        "--exclude-path",
        action="append",
        default=None,
        help="Exclude role-relative paths or glob patterns from analysis (can be passed multiple times).",
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
        help="Generate a standalone runbook markdown file.",
    )
    parser.add_argument(
        "--runbook-csv-output",
        default=None,
        help="Generate runbook CSV output.",
    )
    parser.add_argument(
        "--include-collection-checks",
        action="store_true",
        help="Include collection compliance audit notes in requirements sections.",
    )
    parser.add_argument(
        "--audit-rules",
        default=None,
        metavar="PATH",
        help="Path to .prism.yml containing policy_rules for Policy as Code evaluation.",
    )
    parser.add_argument(
        "--fail-on-audit-violations",
        action="store_true",
        help=f"Exit with code {EXIT_CODE_AUDIT_VIOLATIONS} if audit policy violations are found.",
    )


def _add_output_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_template: bool,
    format_choices: tuple[str, ...],
) -> None:
    parser.add_argument("-o", "--output", default="README.md", help="Output file path.")
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
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prism",
        description="Generate documentation for Ansible roles and collections.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    role_parser = subparsers.add_parser("role", help="Document a local role")
    role_parser.add_argument(
        "role_path", help="Path to the Ansible role directory to scan"
    )
    _add_shared_scan_arguments(role_parser)
    _add_output_arguments(
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
    _add_output_arguments(
        collection_parser,
        include_template=False,
        format_choices=("md", "json"),
    )

    repo_parser = subparsers.add_parser(
        "repo", help="Document a role from a repository source"
    )
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

    completion_parser = subparsers.add_parser(
        "completion", help="Generate shell completion output"
    )
    completion_parser.add_argument(
        "shell", choices=("bash",), help="Shell to generate completion for"
    )

    return parser


def _resolve_vars_context_paths(args: argparse.Namespace) -> list[str] | None:
    paths: list[str] = []
    if getattr(args, "vars_context_path", None):
        paths.extend(args.vars_context_path)
    if getattr(args, "vars_seed", None):
        paths.extend(args.vars_seed)
    return paths if paths else None


def _maybe_run_audit(args: argparse.Namespace, payload: dict) -> int:
    """Evaluate audit rules against payload; return CLI exit-code addition (0 if ok)."""
    rules_path = getattr(args, "audit_rules", None)
    if not rules_path:
        return 0

    from prism.scanner_plugins.audit.loader import load_audit_rules_from_file
    from prism.scanner_plugins.audit.runner import run_audit

    rules = load_audit_rules_from_file(rules_path)
    report = run_audit(payload, rules)

    payload["audit_report"] = {
        "summary": report.summary,
        "passed": report.passed,
        "violations": [
            {
                "rule_id": v.rule_id,
                "severity": v.severity,
                "message": v.message,
                "role_path": v.role_path,
                "evidence": list(v.evidence),
            }
            for v in report.violations
        ],
    }

    print(report.summary)
    for violation in report.violations:
        print(
            f"[{violation.severity}] {violation.rule_id}: {violation.message}",
            file=sys.stderr if violation.severity == "error" else sys.stdout,
        )

    if getattr(args, "fail_on_audit_violations", False) and any(
        v.severity == "error" for v in report.violations
    ):
        return EXIT_CODE_AUDIT_VIOLATIONS
    return 0


def _handle_role_command(args: argparse.Namespace) -> int:
    vars_context_paths = _resolve_vars_context_paths(args)

    result = api.scan_role(
        args.role_path,
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
        include_collection_checks=args.include_collection_checks,
        include_task_parameters=args.task_parameters,
        include_task_runbooks=args.task_runbooks,
        inline_task_runbooks=args.inline_task_runbooks,
    )

    written_path = write_role_scan_output(
        dict(result),
        output=args.output,
        output_format=args.format,
        dry_run=args.dry_run,
    )

    audit_exit = _maybe_run_audit(args, dict(result))
    if audit_exit != 0:
        return audit_exit

    if args.verbose and written_path is not None:
        print(f"Written: {written_path}")
    return 0


def _handle_collection_command(args: argparse.Namespace) -> int:
    vars_context_paths = _resolve_vars_context_paths(args)

    payload = api.scan_collection(
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
        include_collection_checks=args.include_collection_checks,
        include_task_parameters=args.task_parameters,
        include_task_runbooks=args.task_runbooks,
        inline_task_runbooks=args.inline_task_runbooks,
        include_rendered_readme=args.format == "md",
        runbook_output_dir=args.runbook_output,
        runbook_csv_output_dir=args.runbook_csv_output,
        include_traceback=args.verbose,
    )

    if args.format == "json":
        rendered: str = (
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
        )
    else:
        rendered = render_collection_markdown(dict(payload))

    if args.dry_run:
        print(rendered, end="")
        return 0

    output_path = resolve_output_path(args.output, args.format)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written_path = write_output(output_path, rendered)

    print(format_collection_summary(dict(payload)))

    audit_exit = _maybe_run_audit(args, dict(payload))
    if audit_exit != 0:
        return audit_exit

    if args.verbose:
        print(f"Written: {written_path}")
    return 0


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
    emit_json = getattr(args, "emit_json", False)
    print(json.dumps(payload, indent=2, sort_keys=True) if emit_json else str(payload))
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
            '        role) opts="-f --format -o --output -t --template -v --verbose --adopt-heading-mode --audit-rules --compare-role-path --concise-readme --create-style-guide --detailed-catalog --dry-run --exclude-path --fail-on-audit-violations --fail-on-unconstrained-dynamic-includes --fail-on-yaml-like-task-annotations --ignore-unresolved-internal-underscore-references --include-collection-checks --include-scanner-report-link --inline-task-runbooks --keep-unknown-style-sections --policy-config --readme-config --runbook-csv-output --runbook-output --scanner-report-output --style-readme --style-source --task-parameters --task-runbooks --variable-sources --vars-context-path --vars-seed" ;;',
            '        collection) opts="-f --format -o --output -v --verbose --adopt-heading-mode --audit-rules --compare-role-path --concise-readme --create-style-guide --detailed-catalog --dry-run --exclude-path --fail-on-audit-violations --fail-on-unconstrained-dynamic-includes --fail-on-yaml-like-task-annotations --ignore-unresolved-internal-underscore-references --include-collection-checks --include-scanner-report-link --inline-task-runbooks --keep-unknown-style-sections --policy-config --readme-config --runbook-csv-output --runbook-output --scanner-report-output --style-readme --style-source --task-parameters --task-runbooks --variable-sources --vars-context-path --vars-seed" ;;',
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
    """Execute a role or collection scan from the fsrc package CLI."""
    parser = build_parser()
    argv_items = list(argv) if argv is not None else list(sys.argv[1:])

    try:
        args = parser.parse_args(argv_items)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0

    try:
        if args.command == "role":
            return _handle_role_command(args)
        if args.command == "collection":
            return _handle_collection_command(args)
        if args.command == "repo":
            return _handle_repo_command(args)
        if args.command == "completion":
            return _handle_completion_command(args)
    except KeyboardInterrupt:
        return _EXIT_CODE_INTERRUPTED
    except Exception as exc:
        print(_format_top_level_exception(exc), file=sys.stderr)
        return _map_top_level_exception_to_exit_code(exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
