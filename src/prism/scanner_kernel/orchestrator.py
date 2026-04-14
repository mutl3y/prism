"""Scanner-kernel orchestration ownership helpers for facade delegation."""

from __future__ import annotations

from typing import Any, Callable

from prism.errors import FailurePolicy
from prism.scanner_data.contracts import (
    RunScanOutputPayload as _RunScanOutputPayload,
)


class ExecuteScanWithContextBinding:
    """Late-bound scanner-context execution seam for facade compatibility."""

    def __init__(
        self,
        *,
        resolve_execute_scan_with_context_fn: Callable[[], Callable[..., str | bytes]],
        resolve_di_container_cls: Callable[[], type[Any]],
        resolve_scanner_context_cls: Callable[[], type[Any]],
        resolve_build_run_scan_options_fn: Callable[[], Callable[..., dict[str, Any]]],
        resolve_prepare_scan_context_fn: Callable[[], Callable[..., dict[str, Any]]],
        resolve_build_emit_scan_outputs_args_fn: Callable[
            [], Callable[..., dict[str, Any]]
        ],
        resolve_emit_scan_outputs_fn: Callable[[], Callable[..., str | bytes]],
    ) -> None:
        self._resolve_execute_scan_with_context_fn = (
            resolve_execute_scan_with_context_fn
        )
        self._resolve_di_container_cls = resolve_di_container_cls
        self._resolve_scanner_context_cls = resolve_scanner_context_cls
        self._resolve_build_run_scan_options_fn = resolve_build_run_scan_options_fn
        self._resolve_prepare_scan_context_fn = resolve_prepare_scan_context_fn
        self._resolve_build_emit_scan_outputs_args_fn = (
            resolve_build_emit_scan_outputs_args_fn
        )
        self._resolve_emit_scan_outputs_fn = resolve_emit_scan_outputs_fn

    def __call__(self, **kwargs: Any) -> str | bytes:
        return self._resolve_execute_scan_with_context_fn()(
            **kwargs,
            di_container_cls=self._resolve_di_container_cls(),
            scanner_context_cls=self._resolve_scanner_context_cls(),
            build_run_scan_options_fn=self._resolve_build_run_scan_options_fn(),
            prepare_scan_context_fn=self._resolve_prepare_scan_context_fn(),
            build_emit_scan_outputs_args_fn=self._resolve_build_emit_scan_outputs_args_fn(),
            emit_scan_outputs_fn=self._resolve_emit_scan_outputs_fn(),
        )


class OrchestrateScanPayloadBinding:
    """Late-bound payload orchestration seam for facade compatibility."""

    def __init__(
        self,
        *,
        resolve_orchestrate_scan_payload_fn: Callable[
            [], Callable[..., _RunScanOutputPayload]
        ],
        resolve_di_container_cls: Callable[[], type[Any]],
        resolve_scanner_context_cls: Callable[[], type[Any]],
        resolve_build_run_scan_options_fn: Callable[[], Callable[..., dict[str, Any]]],
        resolve_prepare_scan_context_fn: Callable[[], Callable[..., dict[str, Any]]],
    ) -> None:
        self._resolve_orchestrate_scan_payload_fn = resolve_orchestrate_scan_payload_fn
        self._resolve_di_container_cls = resolve_di_container_cls
        self._resolve_scanner_context_cls = resolve_scanner_context_cls
        self._resolve_build_run_scan_options_fn = resolve_build_run_scan_options_fn
        self._resolve_prepare_scan_context_fn = resolve_prepare_scan_context_fn

    def __call__(self, **kwargs: Any) -> _RunScanOutputPayload:
        return self._resolve_orchestrate_scan_payload_fn()(
            **kwargs,
            di_container_cls=self._resolve_di_container_cls(),
            scanner_context_cls=self._resolve_scanner_context_cls(),
            build_run_scan_options_fn=self._resolve_build_run_scan_options_fn(),
            prepare_scan_context_fn=self._resolve_prepare_scan_context_fn(),
        )


def build_execute_scan_with_context_binding(
    *,
    resolve_execute_scan_with_context_fn: Callable[[], Callable[..., str | bytes]],
    resolve_di_container_cls: Callable[[], type[Any]],
    resolve_scanner_context_cls: Callable[[], type[Any]],
    resolve_build_run_scan_options_fn: Callable[[], Callable[..., dict[str, Any]]],
    resolve_prepare_scan_context_fn: Callable[[], Callable[..., dict[str, Any]]],
    resolve_build_emit_scan_outputs_args_fn: Callable[
        [], Callable[..., dict[str, Any]]
    ],
    resolve_emit_scan_outputs_fn: Callable[[], Callable[..., str | bytes]],
) -> ExecuteScanWithContextBinding:
    return ExecuteScanWithContextBinding(
        resolve_execute_scan_with_context_fn=resolve_execute_scan_with_context_fn,
        resolve_di_container_cls=resolve_di_container_cls,
        resolve_scanner_context_cls=resolve_scanner_context_cls,
        resolve_build_run_scan_options_fn=resolve_build_run_scan_options_fn,
        resolve_prepare_scan_context_fn=resolve_prepare_scan_context_fn,
        resolve_build_emit_scan_outputs_args_fn=resolve_build_emit_scan_outputs_args_fn,
        resolve_emit_scan_outputs_fn=resolve_emit_scan_outputs_fn,
    )


def build_orchestrate_scan_payload_binding(
    *,
    resolve_orchestrate_scan_payload_fn: Callable[
        [], Callable[..., _RunScanOutputPayload]
    ],
    resolve_di_container_cls: Callable[[], type[Any]],
    resolve_scanner_context_cls: Callable[[], type[Any]],
    resolve_build_run_scan_options_fn: Callable[[], Callable[..., dict[str, Any]]],
    resolve_prepare_scan_context_fn: Callable[[], Callable[..., dict[str, Any]]],
) -> OrchestrateScanPayloadBinding:
    return OrchestrateScanPayloadBinding(
        resolve_orchestrate_scan_payload_fn=resolve_orchestrate_scan_payload_fn,
        resolve_di_container_cls=resolve_di_container_cls,
        resolve_scanner_context_cls=resolve_scanner_context_cls,
        resolve_build_run_scan_options_fn=resolve_build_run_scan_options_fn,
        resolve_prepare_scan_context_fn=resolve_prepare_scan_context_fn,
    )


def run_scan_payload(
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
    include_collection_checks: bool = True,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    strict_phase_failures: bool = True,
    failure_policy: FailurePolicy | None = None,
    runbook_output: str | None = None,
    runbook_csv_output: str | None = None,
    execute_with_runtime_policy_fn: Callable[..., _RunScanOutputPayload],
    orchestrate_scan_payload_fn: Callable[..., _RunScanOutputPayload],
) -> _RunScanOutputPayload:
    del concise_readme
    del scanner_report_output
    del include_scanner_report_link

    return execute_with_runtime_policy_fn(
        role_path=role_path,
        role_name_override=role_name_override,
        readme_config_path=readme_config_path,
        include_vars_main=include_vars_main,
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
        policy_config_path=policy_config_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        strict_phase_failures=strict_phase_failures,
        failure_policy=failure_policy,
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
        invoke_scan_fn=lambda scan_options: orchestrate_scan_payload_fn(
            role_path=role_path,
            scan_options=scan_options,
        ),
    )


def run_scan(
    role_path: str,
    *,
    output: str = "README.md",
    template: str | None = None,
    output_format: str = "md",
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
    dry_run: bool = False,
    include_collection_checks: bool = True,
    include_task_parameters: bool = True,
    include_task_runbooks: bool = True,
    inline_task_runbooks: bool = True,
    strict_phase_failures: bool = True,
    failure_policy: FailurePolicy | None = None,
    runbook_output: str | None = None,
    runbook_csv_output: str | None = None,
    execute_with_runtime_policy_fn: Callable[..., str | bytes],
    execute_scan_with_context_fn: Callable[..., str | bytes],
) -> str | bytes:
    return execute_with_runtime_policy_fn(
        role_path=role_path,
        role_name_override=role_name_override,
        readme_config_path=readme_config_path,
        include_vars_main=include_vars_main,
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
        policy_config_path=policy_config_path,
        fail_on_unconstrained_dynamic_includes=fail_on_unconstrained_dynamic_includes,
        fail_on_yaml_like_task_annotations=fail_on_yaml_like_task_annotations,
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        strict_phase_failures=strict_phase_failures,
        failure_policy=failure_policy,
        runbook_output=runbook_output,
        runbook_csv_output=runbook_csv_output,
        invoke_scan_fn=lambda scan_options: execute_scan_with_context_fn(
            role_path=role_path,
            scan_options=scan_options,
            output=output,
            output_format=output_format,
            concise_readme=concise_readme,
            scanner_report_output=scanner_report_output,
            include_scanner_report_link=include_scanner_report_link,
            template=template,
            dry_run=dry_run,
            runbook_output=runbook_output,
            runbook_csv_output=runbook_csv_output,
        ),
    )
