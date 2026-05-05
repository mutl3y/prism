"""Unit tests for prism.scanner_plugins.ansible.feature_flags (FIND-13 closure)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from prism.scanner_plugins.ansible.feature_flags import (
    ANSIBLE_PLUGIN_ENABLED_ENV_VAR,
    KERNEL_ENABLED_ENV_VAR,
    is_ansible_plugin_enabled,
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(KERNEL_ENABLED_ENV_VAR, raising=False)
    monkeypatch.delenv(ANSIBLE_PLUGIN_ENABLED_ENV_VAR, raising=False)


def test_disabled_when_no_env_vars_set(clean_env: None) -> None:
    assert is_ansible_plugin_enabled() is False


def test_disabled_when_only_kernel_enabled(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(KERNEL_ENABLED_ENV_VAR, "1")
    assert is_ansible_plugin_enabled() is False


def test_disabled_when_only_ansible_plugin_enabled(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ANSIBLE_PLUGIN_ENABLED_ENV_VAR, "1")
    assert is_ansible_plugin_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "True", "YES", "on", "ON"])
def test_enabled_for_truthy_values(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(KERNEL_ENABLED_ENV_VAR, value)
    monkeypatch.setenv(ANSIBLE_PLUGIN_ENABLED_ENV_VAR, value)
    assert is_ansible_plugin_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "anything", ""])
def test_disabled_for_non_truthy_values(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(KERNEL_ENABLED_ENV_VAR, value)
    monkeypatch.setenv(ANSIBLE_PLUGIN_ENABLED_ENV_VAR, value)
    assert is_ansible_plugin_enabled() is False


def test_env_var_names_are_documented_constants() -> None:
    assert KERNEL_ENABLED_ENV_VAR == "PRISM_KERNEL_ENABLED"
    assert ANSIBLE_PLUGIN_ENABLED_ENV_VAR == "PRISM_ANSIBLE_PLUGIN_ENABLED"
    assert (
        KERNEL_ENABLED_ENV_VAR not in os.environ
        or os.environ.get(KERNEL_ENABLED_ENV_VAR) is not None
    )


def test_feature_flags_module_avoids_private_kernel_constant_import() -> None:
    module_path = (
        Path(__file__).resolve().parents[1] / "scanner_plugins/ansible/feature_flags.py"
    )
    source = module_path.read_text(encoding="utf-8")

    assert "scanner_kernel.repo_context" not in source
    assert "_TRUTHY_VALUES" not in source
