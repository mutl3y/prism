"""Command and parser orchestration for prism CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError

from .errors import (
    PrismRuntimeError,
    REPO_SCAN_PAYLOAD_JSON_INVALID,
    REPO_SCAN_PAYLOAD_SHAPE_INVALID,
    REPO_SCAN_PAYLOAD_TYPE_INVALID,
)
from .scanner import SECTION_CONFIG_FILENAMES

_EXIT_CODE_GENERIC_ERROR = 2
_EXIT_CODE_NOT_FOUND = 3
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
    options: set[str] = set()
    for action in parser._actions:
        for option in getattr(action, "option_strings", []):
            if option in {"-h", "--help"}:
                continue
            options.add(option)
    return sorted(options)


def _build_bash_completion_script(
    *,
    parser_factory=build_parser,
) -> str:
    parser = parser_factory()
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
    if explicit_config_path:
        return explicit_config_path
    for cfg_name in SECTION_CONFIG_FILENAMES:
        default_cfg = role_path / cfg_name
        if default_cfg.is_file():
            return str(default_cfg)
    return None


def _resolve_vars_context_paths(args: argparse.Namespace) -> list[str] | None:
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
    *,
    load_feedback,
    apply_feedback_recommendations,
) -> bool | None:
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


def _handle_repo_command(
    args: argparse.Namespace,
    *,
    repo_scan_workspace,
    checkout_repo_scan_role,
    prepare_repo_scan_inputs,
    fetch_repo_directory_names,
    repo_path_looks_like_role,
    fetch_repo_file,
    clone_repo,
    build_sparse_clone_paths,
    resolve_style_readme_candidate,
    resolve_default_style_guide_source,
    run_scan,
    repo_name_from_url,
    resolve_repo_scan_target,
    resolve_repo_scan_scanner_report_relpath,
    resolve_include_collection_checks,
    normalize_repo_json_payload,
    resolve_effective_readme_config,
    save_style_comparison_artifacts,
    emit_success,
    resolve_vars_context_paths,
) -> int:
    vars_context_paths = resolve_vars_context_paths(args)

    with repo_scan_workspace() as workspace:
        if args.verbose:
            print(f"Cloning: {args.repo_url}")
        checkout = resolve_repo_scan_target(
            repo_url=args.repo_url,
            workspace=workspace,
            repo_role_path=args.repo_role_path,
            repo_style_readme_path=args.repo_style_readme_path,
            style_readme_path=args.style_readme,
            repo_ref=args.repo_ref,
            repo_timeout=args.repo_timeout,
            lightweight_readme_only=False,
            checkout_repo_scan_role_fn=checkout_repo_scan_role,
            prepare_repo_scan_inputs_fn=prepare_repo_scan_inputs,
            fetch_repo_directory_names_fn=fetch_repo_directory_names,
            repo_path_looks_like_role_fn=repo_path_looks_like_role,
            fetch_repo_file_fn=fetch_repo_file,
            clone_repo_fn=clone_repo,
            build_sparse_clone_paths_fn=build_sparse_clone_paths,
            resolve_style_readme_candidate_fn=resolve_style_readme_candidate,
        )
        style_readme_path = checkout.effective_style_readme_path
        if args.create_style_guide and not style_readme_path:
            style_readme_path = (
                args.style_source or resolve_default_style_guide_source()
            )

        include_collection_checks = resolve_include_collection_checks(
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
            role_name_override=repo_name_from_url(args.repo_url),
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
            scanner_report_relpath = resolve_repo_scan_scanner_report_relpath(
                concise_readme=args.concise_readme,
                scanner_report_output=args.scanner_report_output,
                primary_output_path=args.output,
            )
            if args.dry_run:
                outpath = normalize_repo_json_payload(
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
                normalized_payload = normalize_repo_json_payload(
                    raw_payload,
                    repo_style_readme_path=checkout.resolved_repo_style_readme_path,
                    scanner_report_relpath=scanner_report_relpath,
                )
                if normalized_payload and normalized_payload != raw_payload:
                    output_path.write_text(normalized_payload, encoding="utf-8")

        if args.dry_run:
            print(outpath, end="")
            return emit_success(args, outpath)

        effective_readme_config_path = resolve_effective_readme_config(
            checkout.role_path,
            args.readme_config,
        )
        style_source_path, style_demo_path = save_style_comparison_artifacts(
            style_readme_path,
            outpath,
            repo_name_from_url(args.repo_url),
            effective_readme_config_path,
            args.keep_unknown_style_sections,
        )
        return emit_success(args, outpath, style_source_path, style_demo_path)


def _handle_collection_command(
    args: argparse.Namespace,
    *,
    scan_collection,
    render_collection_markdown,
    resolve_vars_context_paths,
    resolve_include_collection_checks,
    emit_success,
) -> int:
    vars_context_paths = resolve_vars_context_paths(args)

    include_collection_checks = resolve_include_collection_checks(
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
        include_traceback=args.verbose,
    )
    rendered = (
        json.dumps(payload, indent=2)
        if args.format == "json"
        else render_collection_markdown(payload)
    )
    if args.dry_run:
        print(rendered, end="")
        return emit_success(args, rendered)

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
    return emit_success(args, str(output_path.resolve()))


def _handle_role_command(
    args: argparse.Namespace,
    *,
    run_scan,
    resolve_default_style_guide_source,
    resolve_vars_context_paths,
    resolve_include_collection_checks,
    resolve_effective_readme_config,
    save_style_comparison_artifacts,
    emit_success,
) -> int:
    vars_context_paths = resolve_vars_context_paths(args)

    include_collection_checks = resolve_include_collection_checks(
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
        return emit_success(args, outpath)

    effective_readme_config_path = resolve_effective_readme_config(
        Path(args.role_path),
        args.readme_config,
    )
    style_source_path, style_demo_path = save_style_comparison_artifacts(
        args.style_readme,
        outpath,
        role_config_path=effective_readme_config_path,
        keep_unknown_style_sections=args.keep_unknown_style_sections,
    )
    return emit_success(args, outpath, style_source_path, style_demo_path)


def _handle_completion_command(
    args: argparse.Namespace,
    *,
    build_bash_completion_script,
) -> int:
    if args.shell != "bash":
        print(
            f"Error: unsupported completion shell: {args.shell}",
            file=sys.stderr,
        )
        return 2
    print(build_bash_completion_script(), end="")
    return 0
