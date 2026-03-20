"""Jinja2 AST analysis helpers.

These functions are extracted from scanner.py to improve cohesion.
They have zero prism-internal dependencies and can be unit-tested
in complete isolation.

Public (importable) names:
  _JINJA_AST_ENV
  _stringify_jinja_node
  _scan_text_for_default_filters_with_ast
  _collect_undeclared_jinja_variables
  _collect_undeclared_jinja_variables_from_ast
  _collect_jinja_local_bindings_from_text
  _collect_jinja_local_bindings
  _extract_jinja_name_targets
"""

from __future__ import annotations

import jinja2
import jinja2.nodes
from jinja2 import meta

_JINJA_AST_ENV = jinja2.Environment()


def _scan_text_for_default_filters_with_ast(text: str, lines: list[str]) -> list[dict]:
    """Return occurrences discovered via Jinja AST parsing."""
    if "{{" not in text and "{%" not in text:
        return []
    try:
        parsed = _JINJA_AST_ENV.parse(text)
    except Exception:
        return []

    occurrences: list[dict] = []
    for node in parsed.find_all(jinja2.nodes.Filter):
        if node.name != "default":
            continue
        line_no = int(getattr(node, "lineno", 1) or 1)
        line_no = max(1, min(line_no, len(lines) if lines else 1))
        line = lines[line_no - 1] if lines else ""

        target = _stringify_jinja_node(getattr(node, "node", None)).strip()
        args = ", ".join(
            value
            for value in (_stringify_jinja_node(arg).strip() for arg in node.args)
            if value
        )

        if target:
            match = f"{target} | default({args})" if args else f"{target} | default()"
        else:
            match = line.strip()

        occurrences.append(
            {
                "line_no": line_no,
                "line": line,
                "match": match,
                "args": args,
            }
        )
    return occurrences


def _stringify_jinja_node(node: object) -> str:
    """Best-effort compact string rendering for Jinja AST nodes."""
    if node is None:
        return ""
    if isinstance(node, jinja2.nodes.Const):
        return str(node.value)
    if isinstance(node, jinja2.nodes.Name):
        return node.name
    if isinstance(node, jinja2.nodes.Getattr):
        base = _stringify_jinja_node(node.node)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, jinja2.nodes.Getitem):
        base = _stringify_jinja_node(node.node)
        arg = _stringify_jinja_node(node.arg)
        return f"{base}[{arg}]" if base else f"[{arg}]"
    if isinstance(node, jinja2.nodes.Filter):
        base = _stringify_jinja_node(node.node)
        args = ", ".join(
            value
            for value in (_stringify_jinja_node(arg).strip() for arg in node.args)
            if value
        )
        if args:
            return f"{base} | {node.name}({args})"
        return f"{base} | {node.name}".strip()
    if isinstance(node, jinja2.nodes.Call):
        callee = _stringify_jinja_node(node.node)
        args = ", ".join(
            value
            for value in (_stringify_jinja_node(arg).strip() for arg in node.args)
            if value
        )
        return f"{callee}({args})" if callee else f"({args})"
    if isinstance(node, jinja2.nodes.Test):
        left = _stringify_jinja_node(node.node)
        args = ", ".join(
            value
            for value in (_stringify_jinja_node(arg).strip() for arg in node.args)
            if value
        )
        if args:
            return f"{left} is {node.name}({args})"
        return f"{left} is {node.name}".strip()
    if isinstance(node, jinja2.nodes.TemplateData):
        return node.data.strip()
    return ""


def _collect_undeclared_jinja_variables(text: str) -> set[str]:
    """Collect undeclared variable names from Jinja template text."""
    if "{{" not in text and "{%" not in text:
        return set()
    try:
        parsed = _JINJA_AST_ENV.parse(text)
    except Exception:
        return set()
    try:
        return set(meta.find_undeclared_variables(parsed))
    except Exception:
        # Some Ansible-specific filters are unknown to plain Jinja and can
        # break introspection. Fall back to AST name scanning.
        return _collect_undeclared_jinja_variables_from_ast(parsed)


def _collect_undeclared_jinja_variables_from_ast(
    parsed: jinja2.nodes.Template,
) -> set[str]:
    """Collect variable names from Jinja AST without meta introspection.

    Excludes names locally bound by Jinja control flow constructs so loop
    variables, macro parameters, and ``set`` targets are not treated as
    external inputs.
    """
    local_bound = _collect_jinja_local_bindings(parsed)
    names: set[str] = set()
    for node in parsed.find_all(jinja2.nodes.Name):
        if getattr(node, "ctx", None) != "load":
            continue
        if isinstance(node.name, str) and node.name:
            if node.name in local_bound:
                continue
            names.add(node.name)
    return names


def _collect_jinja_local_bindings_from_text(text: str) -> set[str]:
    """Collect locally bound Jinja variable names from raw template text."""
    if "{{" not in text and "{%" not in text:
        return set()
    try:
        parsed = _JINJA_AST_ENV.parse(text)
    except Exception:
        return set()
    return _collect_jinja_local_bindings(parsed)


def _collect_jinja_local_bindings(parsed: jinja2.nodes.Template) -> set[str]:
    """Collect names introduced by local Jinja scopes in a template."""
    local_names: set[str] = set()

    for for_node in parsed.find_all(jinja2.nodes.For):
        local_names.update(
            _extract_jinja_name_targets(getattr(for_node, "target", None))
        )

    for macro_node in parsed.find_all(jinja2.nodes.Macro):
        for arg in getattr(macro_node, "args", []) or []:
            if isinstance(arg, jinja2.nodes.Name) and isinstance(arg.name, str):
                local_names.add(arg.name)

    for assign_node in parsed.find_all(jinja2.nodes.Assign):
        local_names.update(
            _extract_jinja_name_targets(getattr(assign_node, "target", None))
        )

    for assign_block in parsed.find_all(jinja2.nodes.AssignBlock):
        local_names.update(
            _extract_jinja_name_targets(getattr(assign_block, "target", None))
        )

    return local_names


def _extract_jinja_name_targets(node: object) -> set[str]:
    """Extract identifier names from Jinja assignment/loop target nodes."""
    if node is None:
        return set()
    if isinstance(node, jinja2.nodes.Name) and isinstance(node.name, str):
        return {node.name}

    names: set[str] = set()
    for child in getattr(node, "items", []) or []:
        names.update(_extract_jinja_name_targets(child))
    return names
