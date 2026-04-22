"""Minimal API entrypoint for the fsrc Prism package lane."""

from __future__ import annotations

import json
import re as _re
from typing import Any

import yaml

from prism.api_layer import collection as api_collection
from prism.api_layer import non_collection as api_non_collection
from prism.errors import PrismRuntimeError
from prism.errors import FailurePolicy
from prism.collection_plugins import scan_collection_plugins
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
from prism.scanner_core.di import DIContainer
from prism.scanner_core.feature_detector import FeatureDetector
from prism.scanner_core.scanner_context import ScannerContext
from prism.scanner_data import CollectionScanResult, RepoScanResult, RoleScanResult

API_PUBLIC_ENTRYPOINTS: tuple[str, ...] = ("scan_collection", "scan_role", "scan_repo")
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

build_run_scan_options_canonical = api_non_collection.build_run_scan_options_canonical
route_scan_payload_orchestration = api_non_collection.route_scan_payload_orchestration
orchestrate_scan_payload_with_selected_plugin = (
    api_non_collection.orchestrate_scan_payload_with_selected_plugin
)

resolve_comment_driven_documentation_plugin = (
    api_non_collection.resolve_comment_driven_documentation_plugin
)
DEFAULT_PLUGIN_REGISTRY = api_non_collection.DEFAULT_PLUGIN_REGISTRY

__all__ = ["scan_collection", "scan_repo", "scan_role"]

_repo_scan_facade: Any = None


def _resolve_repo_scan_facade() -> Any:
    if _repo_scan_facade is not None:
        return _repo_scan_facade
    return api_non_collection._resolve_repo_scan_facade()


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
    policy_context: dict[str, object] | None = None,
    strict_phase_failures: bool = True,
    scan_pipeline_plugin: str | None = None,
) -> dict[str, object]:
    """Run the non-collection scanner orchestration through the package seam."""
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
        build_run_scan_options_canonical_fn=build_run_scan_options_canonical,
        route_scan_payload_orchestration_fn=route_scan_payload_orchestration,
        orchestrate_scan_payload_with_selected_plugin_fn=(
            orchestrate_scan_payload_with_selected_plugin
        ),
        di_container_cls=DIContainer,
        feature_detector_cls=FeatureDetector,
        scanner_context_cls=ScannerContext,
        resolve_comment_driven_documentation_plugin_fn=(
            resolve_comment_driven_documentation_plugin
        ),
        default_plugin_registry=DEFAULT_PLUGIN_REGISTRY,
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
        scan_role_fn=scan_role,
        build_collection_identity_fn=build_collection_identity,
        aggregate_collection_dependencies_fn=aggregate_collection_dependencies,
        scan_collection_plugins_fn=scan_collection_plugins,
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
        build_collection_role_entry_fn=build_collection_role_entry,
        build_collection_failure_record_fn=build_collection_failure_record,
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
) -> RoleScanResult:
    """Objective-critical role scan facade for fsrc API consumers."""
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
        resolve_repo_scan_facade_fn=_resolve_repo_scan_facade,
    )


def resolve_default_style_guide_source(
    explicit_path: str | None = None, **kwargs: Any
) -> str:
    from prism.scanner_config.style import resolve_default_style_guide_source as _impl

    return _impl(explicit_path=explicit_path, **kwargs)


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
