"""Domain-owned Jinja variable analysis helpers for fsrc."""

from __future__ import annotations

import jinja2
import jinja2.nodes
from jinja2 import meta
from jinja2.sandbox import SandboxedEnvironment

# T4-05: SandboxedEnvironment used as defense-in-depth. This module only calls
# .parse() (AST-only inspection); no template is ever rendered or evaluated
# from role content. Sandbox guards against future regressions where a render
# path is added by mistake.
_JINJA_ENV = SandboxedEnvironment()


class JinjaAnalysisPolicyPlugin:
    """Default Jinja analysis policy implementation for fsrc."""

    @staticmethod
    def collect_undeclared_jinja_variables(text: str) -> set[str]:
        return collect_undeclared_jinja_variables(text)


def collect_undeclared_jinja_variables(text: str) -> set[str]:
    if "{{" not in text and "{%" not in text:
        return set()
    try:
        parsed = _JINJA_ENV.parse(text)
    except (
        jinja2.exceptions.TemplateAssertionError,
        jinja2.exceptions.TemplateSyntaxError,
    ):
        return set()
    try:
        return set(meta.find_undeclared_variables(parsed))
    except jinja2.exceptions.TemplateAssertionError:
        return _collect_undeclared_jinja_variables_from_ast(parsed)


def _collect_undeclared_jinja_variables_from_ast(
    parsed: jinja2.nodes.Template,
) -> set[str]:
    local_bound = _collect_jinja_local_bindings(parsed)
    names: set[str] = set()
    for node in parsed.find_all(jinja2.nodes.Name):
        if getattr(node, "ctx", None) != "load":
            continue
        if isinstance(node.name, str) and node.name and node.name not in local_bound:
            names.add(node.name)
    return names


def _collect_jinja_local_bindings(parsed: jinja2.nodes.Template) -> set[str]:
    local_names: set[str] = set()

    for for_node in parsed.find_all(jinja2.nodes.For):
        local_names.update(_extract_name_targets(getattr(for_node, "target", None)))

    for macro_node in parsed.find_all(jinja2.nodes.Macro):
        for arg in getattr(macro_node, "args", []) or []:
            if isinstance(arg, jinja2.nodes.Name) and isinstance(arg.name, str):
                local_names.add(arg.name)

    for assign_node in parsed.find_all(jinja2.nodes.Assign):
        local_names.update(_extract_name_targets(getattr(assign_node, "target", None)))

    for assign_block in parsed.find_all(jinja2.nodes.AssignBlock):
        local_names.update(_extract_name_targets(getattr(assign_block, "target", None)))

    for with_node in parsed.find_all(jinja2.nodes.With):
        for target in getattr(with_node, "targets", []) or []:
            local_names.update(_extract_name_targets(target))

    return local_names


def _extract_name_targets(node: object) -> set[str]:
    if node is None:
        return set()
    if isinstance(node, jinja2.nodes.Name) and isinstance(node.name, str):
        return {node.name}

    names: set[str] = set()
    for child in getattr(node, "items", []) or []:
        names.update(_extract_name_targets(child))
    return names


__all__ = [
    "JinjaAnalysisPolicyPlugin",
    "collect_undeclared_jinja_variables",
]
