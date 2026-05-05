"""G6-06: ReadmeRendererPlugin stub isolation tests.

Validates that a non-Ansible stub plugin can be registered in the
readme_renderer slot without interfering with the Ansible plugin, and
that the registry correctly routes by platform_key.
"""

from __future__ import annotations

import pathlib
from typing import Any


from prism.scanner_plugins.ansible.readme_renderer import AnsibleReadmeRendererPlugin
from prism.scanner_plugins.registry import PluginRegistry


# ---------------------------------------------------------------------------
# Stub plugin fixture
# ---------------------------------------------------------------------------


class _TerraformStubReadmePlugin:
    """Minimal stub simulating a hypothetical Terraform readme plugin."""

    PRISM_PLUGIN_API_VERSION: tuple[int, int] = (1, 0)
    PLUGIN_IS_STATELESS: bool = True

    def default_section_specs(self) -> tuple[tuple[str, str], ...]:
        return (("terraform_resources", "Terraform Resources"),)

    def extra_section_ids(self) -> frozenset[str]:
        return frozenset({"tfvars_reference"})

    def scanner_stats_section_ids(self) -> frozenset[str]:
        return frozenset({"terraform_resources"})

    def merge_eligible_section_ids(self) -> frozenset[str]:
        return frozenset()

    def legacy_merge_marker_prefixes(self) -> tuple[str, ...]:
        return ("prism",)

    def render_section_body(
        self,
        section_id: str,
        role_name: str,
        description: str,
        variables: dict[str, Any],
        requirements: list[Any],
        default_filters: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> str | None:
        if section_id == "terraform_resources":
            return "## Terraform resources rendered by stub"
        return None

    def render_identity_section(
        self,
        section_id: str,
        role_name: str,
        description: str,
        requirements: list[Any],
        identity_metadata: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str | None:
        return None

    def default_template_path(self) -> pathlib.Path | None:
        return None

    def scanner_report_blurb(self, scanner_report_relpath: str) -> str:
        return f"Terraform report: {scanner_report_relpath}"


# ---------------------------------------------------------------------------
# Registration isolation
# ---------------------------------------------------------------------------


def test_stub_registers_without_polluting_ansible_slot() -> None:
    reg = PluginRegistry()
    reg.register_readme_renderer_plugin("ansible", AnsibleReadmeRendererPlugin)
    reg.register_readme_renderer_plugin("terraform", _TerraformStubReadmePlugin)

    assert reg.get_readme_renderer_plugin("ansible") is AnsibleReadmeRendererPlugin
    assert reg.get_readme_renderer_plugin("terraform") is _TerraformStubReadmePlugin


def test_stub_platform_key_does_not_affect_ansible_rendering() -> None:
    ansible_plugin = AnsibleReadmeRendererPlugin()
    stub_plugin = _TerraformStubReadmePlugin()

    # Ansible renders 'purpose' correctly
    ansible_result = ansible_plugin.render_section_body(
        "purpose", "my_role", "My desc", {}, [], [], {}
    )
    assert ansible_result == "My desc"

    # Stub returns None for 'purpose' — no cross-contamination
    stub_result = stub_plugin.render_section_body(
        "purpose", "my_role", "My desc", {}, [], [], {}
    )
    assert stub_result is None


def test_stub_renders_its_own_section_correctly() -> None:
    stub_plugin = _TerraformStubReadmePlugin()
    result = stub_plugin.render_section_body(
        "terraform_resources", "infra", "d", {}, [], [], {}
    )
    assert result is not None
    assert "stub" in result.lower()


def test_registry_routing_by_platform_key() -> None:
    reg = PluginRegistry()
    reg.register_readme_renderer_plugin("ansible", AnsibleReadmeRendererPlugin)
    reg.register_readme_renderer_plugin("terraform", _TerraformStubReadmePlugin)

    ansible_cls = reg.get_readme_renderer_plugin("ansible")
    terraform_cls = reg.get_readme_renderer_plugin("terraform")

    assert ansible_cls is AnsibleReadmeRendererPlugin
    assert terraform_cls is _TerraformStubReadmePlugin
    assert ansible_cls is not terraform_cls


def test_stub_scanner_report_blurb_differs_from_ansible() -> None:
    ansible_plugin = AnsibleReadmeRendererPlugin()
    stub_plugin = _TerraformStubReadmePlugin()
    relpath = "report.md"

    ansible_blurb = ansible_plugin.scanner_report_blurb(relpath)
    stub_blurb = stub_plugin.scanner_report_blurb(relpath)

    assert ansible_blurb != stub_blurb
    assert "Terraform" in stub_blurb


def test_stub_default_template_path_returns_none() -> None:
    stub_plugin = _TerraformStubReadmePlugin()
    assert stub_plugin.default_template_path() is None


def test_ansible_default_template_path_not_none() -> None:
    ansible_plugin = AnsibleReadmeRendererPlugin()
    assert ansible_plugin.default_template_path() is not None


# ---------------------------------------------------------------------------
# Isolated registry – ansible slot unaffected by stub registry
# ---------------------------------------------------------------------------


def test_isolated_registry_does_not_see_default_registry_entries() -> None:
    isolated = PluginRegistry()
    # New empty registry should not have ansible pre-registered
    result = isolated.get_readme_renderer_plugin("ansible")
    assert result is None


def test_stub_legacy_prefixes_subset_of_ansible_prefixes() -> None:
    ansible_plugin = AnsibleReadmeRendererPlugin()
    stub_plugin = _TerraformStubReadmePlugin()

    ansible_prefixes = set(ansible_plugin.legacy_merge_marker_prefixes())
    stub_prefixes = set(stub_plugin.legacy_merge_marker_prefixes())

    # stub only uses 'prism' — which is also in ansible set
    assert stub_prefixes.issubset(ansible_prefixes)
