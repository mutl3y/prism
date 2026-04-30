"""Ansible plugin feature-flag helpers for scanner runtime routing."""

from __future__ import annotations

import os

from prism.scanner_kernel.repo_context import _TRUTHY_VALUES

KERNEL_ENABLED_ENV_VAR = "PRISM_KERNEL_ENABLED"
ANSIBLE_PLUGIN_ENABLED_ENV_VAR = "PRISM_ANSIBLE_PLUGIN_ENABLED"


def is_ansible_plugin_enabled() -> bool:
    """Return True when both kernel and ansible plugin flags are enabled."""
    kernel_enabled = os.environ.get(KERNEL_ENABLED_ENV_VAR, "").lower()
    ansible_enabled = os.environ.get(ANSIBLE_PLUGIN_ENABLED_ENV_VAR, "").lower()
    return kernel_enabled in _TRUTHY_VALUES and ansible_enabled in _TRUTHY_VALUES
