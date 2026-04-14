"""Compatibility shim for ansible Jinja analysis policy plugin."""

from __future__ import annotations

from prism.scanner_plugins.parsers.jinja import JinjaAnalysisPolicyPlugin
from prism.scanner_plugins.parsers.jinja import collect_undeclared_jinja_variables


class AnsibleJinjaAnalysisPolicyPlugin(JinjaAnalysisPolicyPlugin):
    """Compatibility alias preserving ansible import ownership surface."""


__all__ = [
    "AnsibleJinjaAnalysisPolicyPlugin",
    "collect_undeclared_jinja_variables",
]
