"""Canonical ansible scanner plugin package for the fsrc lane."""

from __future__ import annotations

from prism.scanner_plugins.ansible.feature_flags import (
    ANSIBLE_PLUGIN_ENABLED_ENV_VAR,
)
from prism.scanner_plugins.ansible.feature_flags import is_ansible_plugin_enabled
from prism.scanner_plugins.ansible.kernel import ANSIBLE_KERNEL_PLUGIN_MANIFEST
from prism.scanner_plugins.ansible.kernel import AnsibleBaselineKernelPlugin
from prism.scanner_plugins.ansible.kernel import load_ansible_kernel_plugin

__all__ = [
    "ANSIBLE_PLUGIN_ENABLED_ENV_VAR",
    "ANSIBLE_KERNEL_PLUGIN_MANIFEST",
    "AnsibleBaselineKernelPlugin",
    "is_ansible_plugin_enabled",
    "load_ansible_kernel_plugin",
]
