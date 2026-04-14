"""Compatibility shim for ansible YAML parsing policy plugin."""

from __future__ import annotations

from prism.scanner_plugins.parsers.yaml import YAMLParsingPolicyPlugin


class AnsibleYAMLParsingPolicyPlugin(YAMLParsingPolicyPlugin):
    """Compatibility alias preserving ansible import ownership surface."""


__all__ = ["AnsibleYAMLParsingPolicyPlugin"]
