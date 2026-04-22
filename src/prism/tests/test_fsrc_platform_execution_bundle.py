"""Tests for PlatformExecutionBundle contract and Ansible plugin bundle production."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> object:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(FSRC_SOURCE_ROOT))
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


def test_platform_execution_bundle_has_required_keys() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        interfaces_module = importlib.import_module("prism.scanner_plugins.interfaces")

    annotations = interfaces_module.PlatformExecutionBundle.__annotations__
    assert "prepared_policy" in annotations
    assert "platform_participants" in annotations


def test_platform_participants_has_expected_participant_keys() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        interfaces_module = importlib.import_module("prism.scanner_plugins.interfaces")

    annotations = interfaces_module.PlatformParticipants.__annotations__
    assert "task_line_parsing" in annotations
    assert "jinja_analysis" in annotations


def test_platform_execution_bundle_provider_protocol_is_importable() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        interfaces_module = importlib.import_module("prism.scanner_plugins.interfaces")

    assert hasattr(interfaces_module, "PlatformExecutionBundleProvider")
    provider_proto = interfaces_module.PlatformExecutionBundleProvider
    assert hasattr(provider_proto, "__protocol_attrs__") or callable(provider_proto)


def test_ansible_plugin_builds_execution_bundle() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        ansible_module = importlib.import_module("prism.scanner_plugins.ansible")

    bundle = ansible_module.build_ansible_execution_bundle()
    assert isinstance(bundle, dict)
    assert "prepared_policy" in bundle
    assert "platform_participants" in bundle


def test_ansible_bundle_prepared_policy_satisfies_scanner_core_contract() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        ansible_module = importlib.import_module("prism.scanner_plugins.ansible")

    bundle = ansible_module.build_ansible_execution_bundle()
    prepared_policy = bundle["prepared_policy"]

    assert "task_line_parsing" in prepared_policy
    assert "jinja_analysis" in prepared_policy

    task_line = prepared_policy["task_line_parsing"]
    for attr in (
        "TASK_INCLUDE_KEYS",
        "ROLE_INCLUDE_KEYS",
        "INCLUDE_VARS_KEYS",
        "SET_FACT_KEYS",
        "TASK_BLOCK_KEYS",
        "TASK_META_KEYS",
    ):
        assert getattr(task_line, attr, None) is not None, f"missing attribute: {attr}"
    assert callable(getattr(task_line, "detect_task_module", None))

    jinja = prepared_policy["jinja_analysis"]
    assert callable(getattr(jinja, "collect_undeclared_jinja_variables", None))


def test_ansible_bundle_platform_participants_are_same_instances_as_prepared_policy() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        ansible_module = importlib.import_module("prism.scanner_plugins.ansible")

    bundle = ansible_module.build_ansible_execution_bundle()
    assert (
        bundle["platform_participants"]["task_line_parsing"]
        is bundle["prepared_policy"]["task_line_parsing"]
    )
    assert (
        bundle["platform_participants"]["jinja_analysis"]
        is bundle["prepared_policy"]["jinja_analysis"]
    )


def test_bundle_received_through_generic_contract_not_ansible_concrete_type() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        ansible_module = importlib.import_module("prism.scanner_plugins.ansible")

    def _consume_bundle_generically(bundle: Any) -> tuple[bool, bool, bool]:
        prepared = bundle.get("prepared_policy", {})
        participants = bundle.get("platform_participants", {})
        return (
            "task_line_parsing" in prepared,
            "jinja_analysis" in prepared,
            "task_line_parsing" in participants,
        )

    bundle = ansible_module.build_ansible_execution_bundle()
    has_task_line, has_jinja, participants_has_task_line = _consume_bundle_generically(
        bundle
    )
    assert has_task_line
    assert has_jinja
    assert participants_has_task_line


def test_ansible_bundle_prepared_policy_accepted_by_ensure_prepared_policy_bundle() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        ansible_module = importlib.import_module("prism.scanner_plugins.ansible")
        bundle_resolver_module = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )

    bundle = ansible_module.build_ansible_execution_bundle()
    prepared_policy = bundle["prepared_policy"]

    scan_options: dict[str, Any] = {
        "role_path": "/some/role",
        "prepared_policy_bundle": prepared_policy,
        "strict_phase_failures": True,
    }

    result = bundle_resolver_module.ensure_prepared_policy_bundle(
        scan_options=scan_options,
        di=None,
    )

    assert result is prepared_policy or (
        result["task_line_parsing"] is prepared_policy["task_line_parsing"]
        and result["jinja_analysis"] is prepared_policy["jinja_analysis"]
    )


def test_conforming_provider_satisfies_bundle_provider_protocol() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        ansible_module = importlib.import_module("prism.scanner_plugins.ansible")

    class _ConformingProvider:
        def build_execution_bundle(self, scan_options: dict[str, Any]) -> dict:
            return ansible_module.build_ansible_execution_bundle(scan_options)

    provider = _ConformingProvider()
    bundle = provider.build_execution_bundle({})
    assert "prepared_policy" in bundle
    assert "platform_participants" in bundle
