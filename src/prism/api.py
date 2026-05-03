"""Minimal API entrypoint for the fsrc Prism package lane."""

from __future__ import annotations

import json
from pathlib import Path
import re as _re
from typing import cast

import yaml

from prism.api_layer import collection as api_collection
from prism.api_layer import non_collection as api_non_collection
from prism.api_layer import plugin_facade
from prism.errors import PrismRuntimeError
from prism.errors import FailurePolicy
from prism.path_safety import assert_safe_role_path
from prism.scanner_config.audit_rules import AuditReport, AuditRule
from prism.scanner_io.collection_plugins import scan_collection_plugins
from prism.scanner_io.collection_payload import (
    build_collection_identity,
    build_collection_failure_record,
    build_collection_role_entry,
    build_collection_scan_result,
    render_collection_role_readme,
)
from prism.scanner_io.collection_renderer import write_collection_runbook_artifacts
from prism.scanner_reporting.collection_dependencies import (
    aggregate_collection_dependencies,
)
from prism.scanner_readme import render_readme
from prism.scanner_reporting import render_runbook, render_runbook_csv
from prism.scanner_core import (
    DIContainer,
    FeatureDetector,
    ScanCacheBackend,
    ScannerContext,
)
from prism.scanner_data import (
    CollectionDependencies,
    CollectionFailureRecord,
    CollectionIdentity,
    CollectionPluginCatalog,
    CollectionRoleEntry,
    CollectionScanResult,
    RepoScanResult,
    RunScanOutputPayload,
)
from prism.scanner_data.contracts_request import ScanPolicyContext

NormalizedNonCollectionResult = api_non_collection._NormalizedNonCollectionResult


API_PUBLIC_ENTRYPOINTS: tuple[str, ...] = (
    "scan_collection",
    "scan_role",
    "scan_repo",
)
API_RETAINED_COMPATIBILITY_SEAMS: tuple[str, ...] = ("run_scan",)

_COLLECTION_ROLE_CONTENT_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    FileNotFoundError,
    OSError,
    UnicodeDecodeError,
    ValueError,
    json.JSONDecodeError,
    yaml.YAMLError,
)

_COLLECTION_ROLE_RUNTIME_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    PrismRuntimeError,
    RuntimeError,
)

__all__ = [
    "scan_collection",
    "scan_repo",
    "scan_role",
]


def load_audit_rules_from_file(rules_path: str) -> list[AuditRule]:
    """Load audit rules through the top-level API seam."""
    return plugin_facade.load_audit_rules_from_file(rules_path)


def run_audit(payload: dict[str, object], rules: list[AuditRule]) -> AuditReport:
    """Run audit rules through the top-level API seam."""
    return plugin_facade.run_audit(payload, rules)


def _scan_collection_role_payload(
    role_path: str,
    *,
    compare_role_path: str | None = None,
    style_readme_path: str | None = None,
    role_name_override: str | None = None,
    vars_seed_paths: list[str] | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    readme_config_path: str | None = None,
    adopt_heading_mode: str | None = None,
    style_guide_skeleton: bool = False,
    keep_unknown_style_sections: bool = True,
    exclude_path_patterns: list[str] | None = None,
    style_source_path: str | None = None,
    policy_config_path: str | None = None,
    fail_on_unconstrained_dynamic_includes: bool | None = None,
    fail_on_yaml_like_task_annotations: bool | None = None,
    ignore_unresolved_internal_underscore_references: bool | None = None,
    detailed_catalog: bool = False,
    include_collection_checks: bool = False,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
) -> RunScanOutputPayload:
    return scan_role(
        role_path,
        compare_role_path=compare_role_path,
        style_readme_path=style_readme_path,
        role_name_override=role_name_override,
        vars_seed_paths=vars_seed_paths,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_vars_main=include_vars_main,
        include_scanner_report_link=include_scanner_report_link,
        readme_config_path=readme_config_path,
        adopt_heading_mode=adopt_heading_mode,
        style_guide_skeleton=style_guide_skeleton,
        keep_unknown_style_sections=keep_unknown_style_sections,
        exclude_path_patterns=exclude_path_patterns,
        style_source_path=style_source_path,
        policy_config_path=policy_config_path,
        fail_on_unconstrained_dynamic_includes=(fail_on_unconstrained_dynamic_includes),
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        detailed_catalog=detailed_catalog,
        include_collection_checks=include_collection_checks,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
    )


def _build_collection_identity_typed(collection_root: Path) -> CollectionIdentity:
    return cast(CollectionIdentity, build_collection_identity(collection_root))


def _aggregate_collection_dependencies_typed(
    collection_root: Path,
) -> CollectionDependencies:
    return cast(
        CollectionDependencies,
        aggregate_collection_dependencies(collection_root),
    )


def _scan_collection_plugins_typed(collection_root: Path) -> CollectionPluginCatalog:
    return cast(CollectionPluginCatalog, scan_collection_plugins(collection_root))


def _build_collection_role_entry_typed(
    *,
    role_dir: Path,
    payload: RunScanOutputPayload,
    rendered_readme: str | None,
) -> CollectionRoleEntry:
    return cast(
        CollectionRoleEntry,
        build_collection_role_entry(
            role_dir=role_dir,
            payload=payload,
            rendered_readme=rendered_readme,
        ),
    )


def _build_collection_failure_record_typed(
    *,
    role_dir: Path,
    exc: Exception,
    include_traceback: bool,
) -> CollectionFailureRecord:
    return cast(
        CollectionFailureRecord,
        build_collection_failure_record(
            role_dir=role_dir,
            exc=exc,
            include_traceback=include_traceback,
        ),
    )


def _assert_safe_optional_path(path_value: str | None, *, field_name: str) -> None:
    if path_value is None:
        return
    assert_safe_role_path(path_value, field_name=field_name)


def _assert_safe_optional_path_list(
    path_values: list[str] | None,
    *,
    field_name: str,
) -> None:
    if path_values is None:
        return
    for index, path_value in enumerate(path_values):
        assert_safe_role_path(path_value, field_name=f"{field_name}[{index}]")


def _assert_safe_run_scan_file_inputs(
    *,
    readme_config_path: str | None,
    policy_config_path: str | None,
    vars_seed_paths: list[str] | None,
    style_readme_path: str | None,
    style_source_path: str | None,
    compare_role_path: str | None,
) -> None:
    _assert_safe_optional_path(readme_config_path, field_name="readme_config_path")
    _assert_safe_optional_path(policy_config_path, field_name="policy_config_path")
    _assert_safe_optional_path(style_readme_path, field_name="style_readme_path")
    _assert_safe_optional_path(style_source_path, field_name="style_source_path")
    _assert_safe_optional_path(compare_role_path, field_name="compare_role_path")
    _assert_safe_optional_path_list(vars_seed_paths, field_name="vars_seed_paths")


def _assert_safe_scan_repo_file_inputs(
    *,
    repo_role_path: str,
    repo_style_readme_path: str | None,
    readme_config_path: str | None,
    policy_config_path: str | None,
    vars_seed_paths: list[str] | None,
    style_readme_path: str | None,
    style_source_path: str | None,
    compare_role_path: str | None,
) -> None:
    _assert_safe_optional_path(repo_role_path, field_name="repo_role_path")
    _assert_safe_optional_path(
        repo_style_readme_path,
        field_name="repo_style_readme_path",
    )
    _assert_safe_run_scan_file_inputs(
        readme_config_path=readme_config_path,
        policy_config_path=policy_config_path,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        compare_role_path=compare_role_path,
    )


def run_scan(
    role_path: str,
    *,
    role_name_override: str | None = None,
    readme_config_path: str | None = None,
    policy_config_path: str | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    exclude_path_patterns: list[str] | None = None,
    detailed_catalog: bool = False,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    include_collection_checks: bool = True,
    keep_unknown_style_sections: bool = True,
    adopt_heading_mode: str | None = None,
    vars_seed_paths: list[str] | None = None,
    style_readme_path: str | None = None,
    style_source_path: str | None = None,
    style_guide_skeleton: bool = False,
    compare_role_path: str | None = None,
    fail_on_unconstrained_dynamic_includes: bool | None = None,
    fail_on_yaml_like_task_annotations: bool | None = None,
    ignore_unresolved_internal_underscore_references: bool | None = None,
    policy_context: ScanPolicyContext | None = None,
    strict_phase_failures: bool = True,
    scan_pipeline_plugin: str | None = None,
    cache_backend: ScanCacheBackend | None = None,
) -> NormalizedNonCollectionResult:
    """Run the non-collection scanner orchestration through the package seam."""
    assert_safe_role_path(role_path, field_name="role_path")
    default_plugin_registry = cast(
        "plugin_facade.PluginRegistry",
        plugin_facade.get_default_scan_pipeline_registry(),
    )
    _assert_safe_run_scan_file_inputs(
        readme_config_path=readme_config_path,
        policy_config_path=policy_config_path,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        compare_role_path=compare_role_path,
    )
    return api_non_collection.run_scan(
        role_path,
        role_name_override=role_name_override,
        readme_config_path=readme_config_path,
        policy_config_path=policy_config_path,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_vars_main=include_vars_main,
        include_scanner_report_link=include_scanner_report_link,
        exclude_path_patterns=exclude_path_patterns,
        detailed_catalog=detailed_catalog,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        include_collection_checks=include_collection_checks,
        keep_unknown_style_sections=keep_unknown_style_sections,
        adopt_heading_mode=adopt_heading_mode,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        style_guide_skeleton=style_guide_skeleton,
        compare_role_path=compare_role_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        policy_context=policy_context,
        strict_phase_failures=strict_phase_failures,
        scan_pipeline_plugin=scan_pipeline_plugin,
        cache_backend=cache_backend,
        build_run_scan_options_canonical_fn=(
            api_non_collection.build_run_scan_options_canonical
        ),
        route_scan_payload_orchestration_fn=(
            api_non_collection.route_scan_payload_orchestration
        ),
        orchestrate_scan_payload_with_selected_plugin_fn=(
            api_non_collection.orchestrate_scan_payload_with_selected_plugin
        ),
        di_container_cls=DIContainer,
        feature_detector_cls=FeatureDetector,
        scanner_context_cls=ScannerContext,
        resolve_comment_driven_documentation_plugin_fn=(
            plugin_facade.resolve_comment_driven_documentation_plugin
        ),
        default_plugin_registry=default_plugin_registry,
    )


def scan_collection(
    collection_path: str,
    *,
    compare_role_path: str | None = None,
    style_readme_path: str | None = None,
    vars_seed_paths: list[str] | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    readme_config_path: str | None = None,
    adopt_heading_mode: str | None = None,
    style_guide_skeleton: bool = False,
    keep_unknown_style_sections: bool = True,
    exclude_path_patterns: list[str] | None = None,
    style_source_path: str | None = None,
    policy_config_path: str | None = None,
    fail_on_unconstrained_dynamic_includes: bool | None = None,
    fail_on_yaml_like_task_annotations: bool | None = None,
    ignore_unresolved_internal_underscore_references: bool | None = None,
    include_rendered_readme: bool = False,
    detailed_catalog: bool = False,
    include_collection_checks: bool = False,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    runbook_output_dir: str | None = None,
    runbook_csv_output_dir: str | None = None,
    include_traceback: bool = False,
) -> CollectionScanResult:
    """Scan every role under a collection's roles/ folder and return a payload."""
    assert_safe_role_path(collection_path, field_name="collection_path")
    _assert_safe_run_scan_file_inputs(
        readme_config_path=readme_config_path,
        policy_config_path=policy_config_path,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        compare_role_path=compare_role_path,
    )
    return api_collection.scan_collection(
        collection_path,
        compare_role_path=compare_role_path,
        style_readme_path=style_readme_path,
        vars_seed_paths=vars_seed_paths,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_vars_main=include_vars_main,
        include_scanner_report_link=include_scanner_report_link,
        readme_config_path=readme_config_path,
        adopt_heading_mode=adopt_heading_mode,
        style_guide_skeleton=style_guide_skeleton,
        keep_unknown_style_sections=keep_unknown_style_sections,
        exclude_path_patterns=exclude_path_patterns,
        style_source_path=style_source_path,
        policy_config_path=policy_config_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        include_rendered_readme=include_rendered_readme,
        detailed_catalog=detailed_catalog,
        include_collection_checks=include_collection_checks,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        runbook_output_dir=runbook_output_dir,
        runbook_csv_output_dir=runbook_csv_output_dir,
        include_traceback=include_traceback,
        scan_role_fn=_scan_collection_role_payload,
        build_collection_identity_fn=_build_collection_identity_typed,
        aggregate_collection_dependencies_fn=_aggregate_collection_dependencies_typed,
        scan_collection_plugins_fn=_scan_collection_plugins_typed,
        render_collection_role_readme_fn=lambda *, role_name, payload: render_collection_role_readme(
            role_name=role_name,
            payload=payload,
            render_readme_fn=render_readme,
        ),
        write_collection_runbook_artifacts_fn=lambda **kwargs: write_collection_runbook_artifacts(
            **kwargs,
            render_runbook_fn=render_runbook,
            render_runbook_csv_fn=render_runbook_csv,
        ),
        build_collection_role_entry_fn=_build_collection_role_entry_typed,
        build_collection_failure_record_fn=_build_collection_failure_record_typed,
        build_collection_scan_result_fn=build_collection_scan_result,
        collection_role_content_recoverable_errors=(
            _COLLECTION_ROLE_CONTENT_RECOVERABLE_ERRORS
        ),
        collection_role_runtime_recoverable_errors=(
            _COLLECTION_ROLE_RUNTIME_RECOVERABLE_ERRORS
        ),
    )


def scan_role(
    role_path: str,
    *,
    compare_role_path: str | None = None,
    style_readme_path: str | None = None,
    role_name_override: str | None = None,
    vars_seed_paths: list[str] | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    readme_config_path: str | None = None,
    adopt_heading_mode: str | None = None,
    style_guide_skeleton: bool = False,
    keep_unknown_style_sections: bool = True,
    exclude_path_patterns: list[str] | None = None,
    style_source_path: str | None = None,
    policy_config_path: str | None = None,
    fail_on_unconstrained_dynamic_includes: bool | None = None,
    fail_on_yaml_like_task_annotations: bool | None = None,
    ignore_unresolved_internal_underscore_references: bool | None = None,
    detailed_catalog: bool = False,
    include_collection_checks: bool = False,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    failure_policy: FailurePolicy | None = None,
) -> NormalizedNonCollectionResult:
    """Objective-critical role scan facade for fsrc API consumers."""
    assert_safe_role_path(role_path, field_name="role_path")
    _assert_safe_run_scan_file_inputs(
        readme_config_path=readme_config_path,
        policy_config_path=policy_config_path,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        compare_role_path=compare_role_path,
    )
    return api_non_collection.scan_role(
        role_path,
        compare_role_path=compare_role_path,
        style_readme_path=style_readme_path,
        role_name_override=role_name_override,
        vars_seed_paths=vars_seed_paths,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_vars_main=include_vars_main,
        include_scanner_report_link=include_scanner_report_link,
        readme_config_path=readme_config_path,
        adopt_heading_mode=adopt_heading_mode,
        style_guide_skeleton=style_guide_skeleton,
        keep_unknown_style_sections=keep_unknown_style_sections,
        exclude_path_patterns=exclude_path_patterns,
        style_source_path=style_source_path,
        policy_config_path=policy_config_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        detailed_catalog=detailed_catalog,
        include_collection_checks=include_collection_checks,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        failure_policy=failure_policy,
        run_scan_fn=run_scan,
    )


def scan_repo(
    repo_url: str,
    *,
    repo_ref: str | None = None,
    repo_role_path: str = ".",
    repo_timeout: int = 60,
    repo_style_readme_path: str | None = None,
    compare_role_path: str | None = None,
    style_readme_path: str | None = None,
    vars_seed_paths: list[str] | None = None,
    concise_readme: bool = False,
    scanner_report_output: str | None = None,
    include_vars_main: bool = True,
    include_scanner_report_link: bool = True,
    readme_config_path: str | None = None,
    adopt_heading_mode: str | None = None,
    style_guide_skeleton: bool = False,
    keep_unknown_style_sections: bool = True,
    exclude_path_patterns: list[str] | None = None,
    style_source_path: str | None = None,
    policy_config_path: str | None = None,
    fail_on_unconstrained_dynamic_includes: bool | None = None,
    fail_on_yaml_like_task_annotations: bool | None = None,
    ignore_unresolved_internal_underscore_references: bool | None = None,
    lightweight_readme_only: bool = False,
    include_collection_checks: bool = False,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    failure_policy: FailurePolicy | None = None,
) -> RepoScanResult:
    """Objective-critical repo scan facade for fsrc API consumers."""
    _assert_safe_scan_repo_file_inputs(
        repo_role_path=repo_role_path,
        repo_style_readme_path=repo_style_readme_path,
        readme_config_path=readme_config_path,
        policy_config_path=policy_config_path,
        vars_seed_paths=vars_seed_paths,
        style_readme_path=style_readme_path,
        style_source_path=style_source_path,
        compare_role_path=compare_role_path,
    )
    return api_non_collection.scan_repo(
        repo_url,
        repo_ref=repo_ref,
        repo_role_path=repo_role_path,
        repo_timeout=repo_timeout,
        repo_style_readme_path=repo_style_readme_path,
        compare_role_path=compare_role_path,
        style_readme_path=style_readme_path,
        vars_seed_paths=vars_seed_paths,
        concise_readme=concise_readme,
        scanner_report_output=scanner_report_output,
        include_vars_main=include_vars_main,
        include_scanner_report_link=include_scanner_report_link,
        readme_config_path=readme_config_path,
        adopt_heading_mode=adopt_heading_mode,
        style_guide_skeleton=style_guide_skeleton,
        keep_unknown_style_sections=keep_unknown_style_sections,
        exclude_path_patterns=exclude_path_patterns,
        style_source_path=style_source_path,
        policy_config_path=policy_config_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        lightweight_readme_only=lightweight_readme_only,
        include_collection_checks=include_collection_checks,
        include_task_parameters=include_task_parameters,
        include_task_runbooks=include_task_runbooks,
        inline_task_runbooks=inline_task_runbooks,
        failure_policy=failure_policy,
        scan_role_fn=scan_role,
        resolve_repo_scan_facade_fn=api_non_collection._resolve_repo_scan_facade,
    )


def resolve_default_style_guide_source(
    explicit_path: str | None = None,
    *,
    env_style_guide_source_path: str = "PRISM_STYLE_SOURCE",
    xdg_data_home_env: str = "XDG_DATA_HOME",
    style_guide_data_dirname: str = "prism",
    style_guide_source_filename: str = "STYLE_GUIDE_SOURCE.md",
    system_style_guide_source_path: object | None = None,
    default_style_guide_source_path: object | None = None,
) -> str:
    from pathlib import Path
    from prism.scanner_config.style import resolve_default_style_guide_source as _impl

    return _impl(
        explicit_path=explicit_path,
        env_style_guide_source_path=env_style_guide_source_path,
        xdg_data_home_env=xdg_data_home_env,
        style_guide_data_dirname=style_guide_data_dirname,
        style_guide_source_filename=style_guide_source_filename,
        system_style_guide_source_path=(
            Path(system_style_guide_source_path)
            if isinstance(system_style_guide_source_path, str)
            else system_style_guide_source_path  # type: ignore[arg-type]
        ),
        default_style_guide_source_path=(
            Path(default_style_guide_source_path)
            if isinstance(default_style_guide_source_path, str)
            else default_style_guide_source_path  # type: ignore[arg-type]
        ),
    )


_FILTER_IGNORED_DIRS: tuple[str, ...] = (
    "molecule",
    ".git",
    "__pycache__",
    ".tox",
    "venv",
    ".venv",
)
_DEFAULT_FILTER_RE = _re.compile(
    r"""(?P<context>.{0,40}?)(\|\s*default\b|\bdefault\s*\()\s*(?P<args>[^)\n]{0,200})""",
    flags=_re.IGNORECASE,
)
_ANY_FILTER_RE = _re.compile(r"""\|\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)""")

_NO_AST: object = lambda text, lines: []  # noqa: E731


def _scan_file_for_default_filters_impl(file_path, role_root):
    from prism.scanner_extract.filter_scanner import (
        scan_file_for_default_filters as _impl,
    )

    return _impl(
        file_path,
        role_root,
        default_re=_DEFAULT_FILTER_RE,
        scan_text_for_default_filters_with_ast=_NO_AST,
    )


def _scan_file_for_all_filters_impl(file_path, role_root):
    from prism.scanner_extract.filter_scanner import (
        scan_file_for_all_filters as _impl,
    )

    return _impl(
        file_path,
        role_root,
        any_filter_re=_ANY_FILTER_RE,
        scan_text_for_all_filters_with_ast=_NO_AST,
    )


def scan_for_default_filters(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict]:
    """Scan files under role_path for uses of the default() filter."""
    from prism.scanner_extract.filter_scanner import (
        scan_for_default_filters as _impl,
    )
    from prism.scanner_extract import (
        collect_task_files as _ctf,
        is_relpath_excluded as _ire,
        is_path_excluded as _ipe,
    )

    return _impl(
        role_path,
        exclude_paths=exclude_paths,
        ignored_dirs=_FILTER_IGNORED_DIRS,
        collect_task_files=lambda r, e: _ctf(r, exclude_paths=e),
        is_relpath_excluded=_ire,
        is_path_excluded=_ipe,
        scan_file_for_default_filters=_scan_file_for_default_filters_impl,
    )


def scan_for_all_filters(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict]:
    """Scan files under role_path for all discovered Jinja filters."""
    from prism.scanner_extract.filter_scanner import (
        scan_for_all_filters as _impl,
    )
    from prism.scanner_extract import (
        collect_task_files as _ctf,
        is_relpath_excluded as _ire,
        is_path_excluded as _ipe,
    )

    return _impl(
        role_path,
        exclude_paths=exclude_paths,
        ignored_dirs=_FILTER_IGNORED_DIRS,
        collect_task_files=lambda r, e: _ctf(r, exclude_paths=e),
        is_relpath_excluded=_ire,
        is_path_excluded=_ipe,
        scan_file_for_all_filters=_scan_file_for_all_filters_impl,
    )


def collect_role_contents(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Collect lists of files from common role subdirectories."""
    from prism.scanner_core.scan_facade_helpers import (
        collect_role_contents as _impl,
    )
    from prism.scanner_extract import is_path_excluded as _ipe, load_meta as _lm

    return _impl(
        role_path=role_path,
        exclude_paths=exclude_paths,
        is_path_excluded=_ipe,
        load_meta=_lm,
        extract_role_features=lambda rp, **kw: {},
    )


def compute_quality_metrics(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Compute lightweight role quality metrics."""
    from prism.scanner_core.scan_facade_helpers import (
        compute_quality_metrics as _impl,
    )

    def _collect(rp: str, ep: list[str] | None) -> dict:
        return collect_role_contents(rp, ep)

    def _load_variables(
        *, role_path: str, exclude_paths: list[str] | None = None, **kw: object
    ) -> dict:  # noqa: ARG001
        return {}

    def _scan_filters(rp: str, ep: list[str] | None) -> list:
        return scan_for_default_filters(rp, ep)

    return _impl(
        role_path=role_path,
        exclude_paths=exclude_paths,
        collect_role_contents=_collect,
        load_variables=_load_variables,
        scan_for_default_filters=_scan_filters,
    )


def build_comparison_report(
    target_role_path: str,
    baseline_role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Compare target role quality against a baseline role."""
    from prism.scanner_core.scan_facade_helpers import (
        build_comparison_report as _impl,
    )

    def _metrics(rp: str, ep: list[str] | None) -> dict:
        return compute_quality_metrics(rp, ep)

    return _impl(
        target_role_path=target_role_path,
        baseline_role_path=baseline_role_path,
        exclude_paths=exclude_paths,
        compute_quality_metrics=_metrics,
    )
