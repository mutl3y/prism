"""Focused contract tests for the first executable Kubernetes plugin slice."""

from __future__ import annotations

from prism.scanner_plugins.interfaces import ReadmeRendererPlugin
from prism.scanner_plugins.kubernetes import (
    KubernetesReadmeRendererPlugin,
    KubernetesScanPipelinePlugin,
    build_kubernetes_execution_bundle,
)
from prism.tests.fixtures.fixtures_kubernetes_pipeline import (
    build_kubernetes_scan_context,
    build_kubernetes_scan_options,
)


def test_kubernetes_package_exports_first_executable_slice() -> None:
    assert KubernetesScanPipelinePlugin.PLUGIN_IS_STATELESS is True
    assert KubernetesReadmeRendererPlugin.PLUGIN_IS_STATELESS is True
    assert KubernetesReadmeRendererPlugin.PRISM_PLUGIN_API_VERSION == (1, 0)


def test_kubernetes_scan_pipeline_plugin_sets_platform_metadata() -> None:
    plugin = KubernetesScanPipelinePlugin()

    result = plugin.process_scan_pipeline(
        scan_options=build_kubernetes_scan_options(),
        scan_context=build_kubernetes_scan_context(),
    )

    assert result["plugin_platform"] == "kubernetes"
    assert result["plugin_name"] == "kubernetes"
    assert result["plugin_enabled"] is True
    assert result["kubernetes_plugin_enabled"] is True


def test_kubernetes_execution_bundle_returns_fail_closed_contract_stubs() -> None:
    bundle = build_kubernetes_execution_bundle(build_kubernetes_scan_options())

    assert set(bundle) == {"prepared_policy", "platform_participants"}
    assert (
        bundle["platform_participants"]["task_line_parsing"]
        is bundle["prepared_policy"]["task_line_parsing"]
    )
    assert (
        bundle["platform_participants"]["jinja_analysis"]
        is bundle["prepared_policy"]["jinja_analysis"]
    )

    task_line = bundle["prepared_policy"]["task_line_parsing"]
    assert task_line.TASK_INCLUDE_KEYS == frozenset()
    assert task_line.ROLE_INCLUDE_KEYS == frozenset()

    try:
        task_line.detect_task_module({"name": "demo"})
    except ValueError as exc:
        assert "kubernetes execution bundle" in str(exc)
    else:
        raise AssertionError("expected fail-closed task line parsing stub")


def test_kubernetes_readme_renderer_is_runtime_compatible() -> None:
    plugin = KubernetesReadmeRendererPlugin()

    assert isinstance(plugin, ReadmeRendererPlugin)
    assert plugin.default_section_specs()[0] == (
        "purpose",
        "Workload purpose and capabilities",
    )
    assert plugin.legacy_merge_marker_prefixes() == ("prism", "kubernetes-doc")
    assert "scanner_report" in plugin.extra_section_ids()
