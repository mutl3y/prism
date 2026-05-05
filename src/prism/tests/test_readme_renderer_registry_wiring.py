"""G6-06: ReadmeRendererPlugin registry round-trip wiring tests.

Validates that the registry correctly stores, retrieves, and lists
readme_renderer plugins, and that the bootstrap registration is wired.
"""

from __future__ import annotations

import pytest

from prism.scanner_plugins import get_default_plugin_registry
from prism.scanner_plugins.ansible.readme_renderer import AnsibleReadmeRendererPlugin
from prism.scanner_plugins.registry import PluginRegistry, PluginStatelessRequired


# ---- round-trip register/get ---------------------------------------------


def test_register_and_get_readme_renderer_plugin_round_trip() -> None:
    reg = PluginRegistry()
    reg.register_readme_renderer_plugin("ansible", AnsibleReadmeRendererPlugin)
    result = reg.get_readme_renderer_plugin("ansible")
    assert result is AnsibleReadmeRendererPlugin


def test_get_readme_renderer_plugin_returns_none_for_unknown() -> None:
    reg = PluginRegistry()
    result = reg.get_readme_renderer_plugin("nonexistent_platform")
    assert result is None


def test_list_readme_renderer_plugins_empty_on_new_registry() -> None:
    reg = PluginRegistry()
    result = reg.list_readme_renderer_plugins()
    assert isinstance(result, dict)
    assert len(result) == 0


def test_list_readme_renderer_plugins_after_registration() -> None:
    reg = PluginRegistry()
    reg.register_readme_renderer_plugin("ansible", AnsibleReadmeRendererPlugin)
    result = reg.list_readme_renderer_plugins()
    assert "ansible" in result
    assert result["ansible"] is AnsibleReadmeRendererPlugin


def test_register_multiple_plugins_and_list_all() -> None:
    reg = PluginRegistry()

    class _FakePlatformPlugin:
        PRISM_PLUGIN_API_VERSION = (1, 0)
        PLUGIN_IS_STATELESS = True

        def default_section_specs(self) -> tuple:
            return ()

        def extra_section_ids(self) -> frozenset:
            return frozenset()

        def scanner_stats_section_ids(self) -> frozenset:
            return frozenset()

        def merge_eligible_section_ids(self) -> frozenset:
            return frozenset()

        def legacy_merge_marker_prefixes(self) -> tuple:
            return ("fake",)

        def render_section_body(self, *_a, **_kw):  # type: ignore[override]
            return None

        def render_identity_section(self, *_a, **_kw):  # type: ignore[override]
            return None

        def default_template_path(self):  # type: ignore[override]
            return None

        def scanner_report_blurb(self, relpath: str) -> str:
            return f"fake blurb: {relpath}"

    reg.register_readme_renderer_plugin("ansible", AnsibleReadmeRendererPlugin)
    reg.register_readme_renderer_plugin("fake_platform", _FakePlatformPlugin)
    result = reg.list_readme_renderer_plugins()
    assert "ansible" in result
    assert "fake_platform" in result


# ---- stateless slot enforcement ------------------------------------------


def test_register_readme_renderer_plugin_requires_stateless_true() -> None:
    reg = PluginRegistry()

    class _Stateful:
        PLUGIN_IS_STATELESS = False

    with pytest.raises(PluginStatelessRequired):
        reg.register_readme_renderer_plugin("bad", _Stateful)  # type: ignore[arg-type]


def test_register_readme_renderer_plugin_accepts_stateless_true() -> None:
    reg = PluginRegistry()

    class _Stateless:
        PLUGIN_IS_STATELESS = True
        PRISM_PLUGIN_API_VERSION = (1, 0)

        def default_section_specs(self) -> tuple:
            return ()

        def extra_section_ids(self) -> frozenset:
            return frozenset()

        def scanner_stats_section_ids(self) -> frozenset:
            return frozenset()

        def merge_eligible_section_ids(self) -> frozenset:
            return frozenset()

        def legacy_merge_marker_prefixes(self) -> tuple:
            return ()

        def render_section_body(self, *_a, **_kw):  # type: ignore[override]
            return None

        def render_identity_section(self, *_a, **_kw):  # type: ignore[override]
            return None

        def default_template_path(self):  # type: ignore[override]
            return None

        def scanner_report_blurb(self, relpath: str) -> str:
            return relpath

    reg.register_readme_renderer_plugin("good", _Stateless)  # type: ignore[arg-type]
    assert reg.get_readme_renderer_plugin("good") is _Stateless


# ---- bootstrap wiring ----------------------------------------------------


def test_bootstrap_registers_ansible_readme_renderer_in_default_registry() -> None:
    result = get_default_plugin_registry().get_readme_renderer_plugin("ansible")
    assert result is AnsibleReadmeRendererPlugin


def test_default_registry_lists_ansible_in_readme_renderer_plugins() -> None:
    result = get_default_plugin_registry().list_readme_renderer_plugins()
    assert "ansible" in result


# ---- fail-closed ValueError from render helpers --------------------------


def test_render_guide_section_body_raises_for_unregistered_platform() -> None:
    from prism.scanner_readme.guide import render_guide_section_body

    with pytest.raises(ValueError, match="unknown_platform_xyz"):
        render_guide_section_body(
            "purpose",
            "r",
            "d",
            {},
            [],
            [],
            {"platform_key": "unknown_platform_xyz"},
        )


def test_render_readme_raises_for_unregistered_platform() -> None:
    import tempfile
    from pathlib import Path

    from prism.scanner_readme.render import render_readme

    with tempfile.TemporaryDirectory() as tmpdir:
        output = str(Path(tmpdir) / "README.md")
        with pytest.raises(ValueError, match="unknown_platform_xyz"):
            render_readme(
                output,
                "r",
                "d",
                {},
                [],
                [],
                metadata={"platform_key": "unknown_platform_xyz"},
            )


# ---- resolve_readme_renderer_plugin resolver tests -----------------------


def test_resolve_readme_renderer_plugin_returns_instance_for_registered_platform() -> (
    None
):
    from prism.scanner_plugins.defaults import resolve_readme_renderer_plugin

    instance = resolve_readme_renderer_plugin("ansible")
    assert isinstance(instance, AnsibleReadmeRendererPlugin)


def test_resolve_readme_renderer_plugin_raises_for_unknown_platform() -> None:
    from prism.scanner_plugins.defaults import resolve_readme_renderer_plugin

    with pytest.raises(ValueError, match="no_such_platform_xyz"):
        resolve_readme_renderer_plugin("no_such_platform_xyz")


def test_resolve_readme_renderer_plugin_uses_injected_registry() -> None:
    from prism.scanner_plugins.defaults import resolve_readme_renderer_plugin

    reg = PluginRegistry()
    reg.register_readme_renderer_plugin("custom", AnsibleReadmeRendererPlugin)

    instance = resolve_readme_renderer_plugin("custom", registry=reg)
    assert isinstance(instance, AnsibleReadmeRendererPlugin)


def test_resolve_readme_renderer_plugin_injected_registry_raises_for_missing() -> None:
    from prism.scanner_plugins.defaults import resolve_readme_renderer_plugin

    empty_reg = PluginRegistry()

    with pytest.raises(ValueError, match="ansible"):
        resolve_readme_renderer_plugin("ansible", registry=empty_reg)
