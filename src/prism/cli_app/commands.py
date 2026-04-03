"""Package-owned command handlers for Prism CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from prism.errors import PrismRuntimeError


def handle_repo_command(
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
    finalize_repo_json_output_fn,
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
            outpath = finalize_repo_json_output_fn(
                outpath,
                dry_run=args.dry_run,
                repo_style_readme_path=checkout.resolved_repo_style_readme_path,
                scanner_report_relpath=scanner_report_relpath,
                normalize_repo_json_payload=normalize_repo_json_payload,
            )

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


def handle_collection_command(
    args: argparse.Namespace,
    *,
    scan_collection,
    render_collection_markdown,
    resolve_vars_context_paths,
    resolve_include_collection_checks,
    emit_success,
    resolve_cli_output_path_fn,
    persist_collection_role_markdown_documents_fn,
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

    output_path = resolve_cli_output_path_fn(args.output, args.format)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    if args.format == "md":
        persist_collection_role_markdown_documents_fn(
            output_path=output_path,
            payload=payload,
        )
    return emit_success(args, str(output_path.resolve()))


def handle_role_command(
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


def handle_completion_command(
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


def map_top_level_exception_to_exit_code(exc: Exception) -> int:
    if isinstance(exc, PrismRuntimeError):
        if exc.category == "network":
            return 6
        if exc.category == "io":
            return 7
        return 2
    if isinstance(exc, FileNotFoundError):
        return 3
    if isinstance(exc, PermissionError):
        return 4
    if isinstance(exc, json.JSONDecodeError):
        return 5
    return 7 if isinstance(exc, OSError) else 2
