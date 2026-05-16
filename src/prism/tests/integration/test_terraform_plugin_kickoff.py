"""Focused contract tests for the first Terraform executable slice."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, get_type_hints


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_src_prism_on_sys_path() -> Iterator[None]:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(SRC_ROOT))
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        yield
    finally:
        sys.path[:] = original_path
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        sys.modules.update(original_modules)


def test_terraform_package_exports_first_slice_contracts() -> None:
    with _prefer_src_prism_on_sys_path():
        terraform_module = importlib.import_module("prism.scanner_plugins.terraform")

    assert hasattr(terraform_module, "TerraformScanPipelinePlugin")
    assert hasattr(terraform_module, "build_terraform_execution_bundle")
    assert hasattr(terraform_module, "TerraformReadmeRendererPlugin")


def test_terraform_scan_pipeline_plugin_emits_platform_context() -> None:
    with _prefer_src_prism_on_sys_path():
        terraform_module = importlib.import_module("prism.scanner_plugins.terraform")

    plugin = terraform_module.TerraformScanPipelinePlugin()
    context = plugin.process_scan_pipeline(
        scan_options={"role_path": "/tmp/terraform-module"},
        scan_context={},
    )

    assert context["plugin_platform"] == "terraform"
    assert context["plugin_name"] == "terraform"
    assert context["plugin_enabled"] is True
    assert context["role_path"] == "/tmp/terraform-module"


def test_terraform_execution_bundle_returns_fail_closed_contract_bundle() -> None:
    with _prefer_src_prism_on_sys_path():
        terraform_module = importlib.import_module("prism.scanner_plugins.terraform")

    bundle = terraform_module.build_terraform_execution_bundle()

    assert "prepared_policy" in bundle
    assert "platform_participants" in bundle

    prepared_policy = bundle["prepared_policy"]
    assert "task_line_parsing" in prepared_policy
    assert "jinja_analysis" in prepared_policy
    assert "task_traversal" in prepared_policy
    assert "yaml_parsing" in prepared_policy
    assert "variable_extractor" in prepared_policy
    assert "task_annotation_parsing" in prepared_policy

    task_line = prepared_policy["task_line_parsing"]
    assert callable(getattr(task_line, "detect_task_module", None))
    assert task_line.detect_task_module({}) is None

    jinja = prepared_policy["jinja_analysis"]
    assert callable(getattr(jinja, "collect_undeclared_jinja_variables", None))
    assert jinja.collect_undeclared_jinja_variables("${var.name}") == set()

    variable_extractor = prepared_policy["variable_extractor"]
    assert callable(getattr(variable_extractor, "collect_include_vars_files", None))
    assert (
        variable_extractor.collect_include_vars_files(
            role_path="/tmp/terraform-module",
            exclude_paths=None,
            collect_task_files=lambda *_args, **_kwargs: [],
            load_yaml_file=lambda *_args, **_kwargs: None,
        )
        == []
    )

    task_annotation = prepared_policy["task_annotation_parsing"]
    assert callable(
        getattr(task_annotation, "extract_task_annotations_for_file", None)
    )
    assert task_annotation.extract_task_annotations_for_file([], include_task_index=True) == (
        [],
        {},
    )

    assert (
        bundle["platform_participants"]["task_line_parsing"]
        is prepared_policy["task_line_parsing"]
    )
    assert (
        bundle["platform_participants"]["jinja_analysis"]
        is prepared_policy["jinja_analysis"]
    )


def test_terraform_readme_renderer_plugin_satisfies_minimal_contract() -> None:
    with _prefer_src_prism_on_sys_path():
        terraform_module = importlib.import_module("prism.scanner_plugins.terraform")
        interfaces_module = importlib.import_module("prism.scanner_plugins.interfaces")

    plugin = terraform_module.TerraformReadmeRendererPlugin()
    assert isinstance(plugin, interfaces_module.ReadmeRendererPlugin)
    assert plugin.PRISM_PLUGIN_API_VERSION == (1, 0)
    assert plugin.PLUGIN_IS_STATELESS is True
    assert plugin.default_section_specs()
    assert "scanner_report" in plugin.extra_section_ids()
    assert plugin.render_section_body(
        "purpose",
        "terraform-vpc",
        "Provision a VPC.",
        {},
        [],
        [],
        {},
    ) == "Provision a VPC."
    assert plugin.render_identity_section(
        "requirements",
        "terraform-vpc",
        "Provision a VPC.",
        [">= 1.6.0"],
        {},
        {},
    ) == "- >= 1.6.0"
    assert plugin.default_template_path() is None
    assert "scanner-report" in plugin.scanner_report_blurb("reports/scan.md")


def test_terraform_slice_public_type_hints_use_canonical_contracts() -> None:
    with _prefer_src_prism_on_sys_path():
        terraform_module = importlib.import_module("prism.scanner_plugins.terraform")
        interfaces_module = importlib.import_module("prism.scanner_plugins.interfaces")

    process_hints = get_type_hints(
        terraform_module.TerraformScanPipelinePlugin.process_scan_pipeline,
        vars(terraform_module),
        vars(terraform_module),
    )
    assert process_hints["scan_options"] is interfaces_module.ScanOptionsDict
    assert process_hints["scan_context"] is interfaces_module.ScanMetadata
    assert process_hints["return"] is interfaces_module.ScanPipelinePreflightContext

    bundle_hints = get_type_hints(
        terraform_module.build_terraform_execution_bundle,
        vars(terraform_module),
        vars(terraform_module),
    )
    assert bundle_hints["scan_options"] == (interfaces_module.ScanOptionsDict | None)
    assert bundle_hints["return"] is interfaces_module.PlatformExecutionBundle