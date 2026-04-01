"""Jinja2 AST analysis helpers.

These functions are extracted from scanner.py to improve cohesion.
They have zero prism-internal dependencies and can be unit-tested
in complete isolation.

Public (importable) names:
    _JINJA_AST_ENV
    _stringify_jinja_node
    _scan_text_for_all_filters_with_ast
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


def _scan_text_for_all_filters_with_ast(text: str, lines: list[str]) -> list[dict]:
    """Return all filter occurrences discovered via Jinja AST parsing."""
    if "{{" not in text and "{%" not in text:
        return []
    try:
        parsed = _JINJA_AST_ENV.parse(text)
    except (
        jinja2.exceptions.TemplateSyntaxError,
        jinja2.exceptions.TemplateAssertionError,
    ):
        return []

    occurrences: list[dict] = []
    for node in parsed.find_all(jinja2.nodes.Filter):
        line_no = int(getattr(node, "lineno", 1) or 1)
        line_no = max(1, min(line_no, len(lines) if lines else 1))
        line = lines[line_no - 1] if lines else ""

        filter_name = str(getattr(node, "name", "") or "").strip()
        if not filter_name:
            continue

        target = _stringify_jinja_node(getattr(node, "node", None)).strip()
        args = ", ".join(
            value
            for value in (_stringify_jinja_node(arg).strip() for arg in node.args)
            if value
        )

        if target:
            match = (
                f"{target} | {filter_name}({args})"
                if args
                else f"{target} | {filter_name}()"
            )
        else:
            match = line.strip()

        occurrences.append(
            {
                "line_no": line_no,
                "line": line,
                "match": match,
                "args": args,
                "filter_name": filter_name,
            }
        )
    return occurrences


def _scan_text_for_default_filters_with_ast(text: str, lines: list[str]) -> list[dict]:
    """Return default() filter occurrences discovered via Jinja AST parsing."""
    rows = _scan_text_for_all_filters_with_ast(text, lines)
    return [row for row in rows if row.get("filter_name") == "default"]


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
    if isinstance(node, jinja2.nodes.Tuple):
        values = [
            value
            for value in (_stringify_jinja_node(item).strip() for item in node.items)
            if value
        ]
        return f"({', '.join(values)})" if values else "()"
    if isinstance(node, jinja2.nodes.List):
        values = [
            value
            for value in (_stringify_jinja_node(item).strip() for item in node.items)
            if value
        ]
        return f"[{', '.join(values)}]"
    if isinstance(node, jinja2.nodes.Pair):
        key = _stringify_jinja_node(getattr(node, "key", None)).strip()
        value = _stringify_jinja_node(getattr(node, "value", None)).strip()
        if key and value:
            return f"{key}: {value}"
        return key or value
    if isinstance(node, jinja2.nodes.Dict):
        pairs = [
            rendered
            for rendered in (
                _stringify_jinja_node(item).strip()
                for item in getattr(node, "items", []) or []
            )
            if rendered
        ]
        return "{" + ", ".join(pairs) + "}"
    if isinstance(node, jinja2.nodes.Keyword):
        key = str(getattr(node, "key", "") or "").strip()
        value = _stringify_jinja_node(getattr(node, "value", None)).strip()
        if key and value:
            return f"{key}={value}"
        return value
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
        positional = [
            value
            for value in (_stringify_jinja_node(arg).strip() for arg in node.args)
            if value
        ]
        keyword_args: list[str] = []
        for kwarg in getattr(node, "kwargs", []) or []:
            key = str(getattr(kwarg, "key", "") or "").strip()
            value = _stringify_jinja_node(getattr(kwarg, "value", None)).strip()
            if key and value:
                keyword_args.append(f"{key}={value}")
            elif value:
                keyword_args.append(value)
        args = ", ".join(positional + keyword_args)
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
    if isinstance(node, jinja2.nodes.CondExpr):
        condition = _stringify_jinja_node(getattr(node, "test", None)).strip()
        when_true = _stringify_jinja_node(getattr(node, "expr1", None)).strip()
        when_false = _stringify_jinja_node(getattr(node, "expr2", None)).strip()
        if condition and when_true and when_false:
            return f"{when_true} if {condition} else {when_false}"
        return when_true or when_false or condition
    if isinstance(node, jinja2.nodes.Compare):
        left = _stringify_jinja_node(getattr(node, "expr", None)).strip()
        parts = [left] if left else []
        compare_aliases = {
            "eq": "==",
            "ne": "!=",
            "gt": ">",
            "gteq": ">=",
            "lt": "<",
            "lteq": "<=",
            "in": "in",
            "notin": "not in",
        }
        for operand in getattr(node, "ops", []) or []:
            op = str(getattr(operand, "op", "") or "").strip()
            rhs = _stringify_jinja_node(getattr(operand, "expr", None)).strip()
            op = compare_aliases.get(op, op)
            if op and rhs:
                parts.append(f"{op} {rhs}")
            elif rhs:
                parts.append(rhs)
        return " ".join(part for part in parts if part).strip()
    if isinstance(node, jinja2.nodes.BinExpr):
        left = _stringify_jinja_node(getattr(node, "left", None)).strip()
        right = _stringify_jinja_node(getattr(node, "right", None)).strip()
        op = node.__class__.__name__.lower()
        op_aliases = {
            "and": "and",
            "or": "or",
            "add": "+",
            "sub": "-",
            "mul": "*",
            "div": "/",
            "floordiv": "//",
            "mod": "%",
            "pow": "**",
        }
        operator = op_aliases.get(op, op)
        if left and right:
            return f"{left} {operator} {right}"
        return left or right
    if isinstance(node, jinja2.nodes.UnaryExpr):
        target = _stringify_jinja_node(getattr(node, "node", None)).strip()
        op = node.__class__.__name__.lower()
        op_aliases = {
            "not": "not ",
            "neg": "-",
            "pos": "+",
        }
        prefix = op_aliases.get(op, "")
        if prefix and target:
            return f"{prefix}{target}"
        return target
    if isinstance(node, jinja2.nodes.TemplateData):
        return node.data.strip()
    return ""


def _collect_undeclared_jinja_variables(text: str) -> set[str]:
    """Collect undeclared variable names from Jinja template text."""
    if "{{" not in text and "{%" not in text:
        return set()
    try:
        parsed = _JINJA_AST_ENV.parse(text)
    except (
        jinja2.exceptions.TemplateSyntaxError,
        jinja2.exceptions.TemplateAssertionError,
    ):
        return set()
    try:
        return set(meta.find_undeclared_variables(parsed))
    except jinja2.exceptions.TemplateAssertionError:
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
    except (
        jinja2.exceptions.TemplateSyntaxError,
        jinja2.exceptions.TemplateAssertionError,
    ):
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

    for with_node in parsed.find_all(jinja2.nodes.With):
        for target in getattr(with_node, "targets", []) or []:
            local_names.update(_extract_jinja_name_targets(target))

    for call_block in parsed.find_all(jinja2.nodes.CallBlock):
        for arg in getattr(call_block, "args", []) or []:
            if isinstance(arg, jinja2.nodes.Name) and isinstance(arg.name, str):
                local_names.add(arg.name)

    for import_node in parsed.find_all(jinja2.nodes.Import):
        target = getattr(import_node, "target", None)
        if isinstance(target, str) and target:
            local_names.add(target)

    for from_import in parsed.find_all(jinja2.nodes.FromImport):
        for imported in getattr(from_import, "names", []) or []:
            if isinstance(imported, tuple) and len(imported) == 2:
                alias = imported[1]
                name = imported[0]
                if isinstance(alias, str) and alias:
                    local_names.add(alias)
                elif isinstance(name, str) and name:
                    local_names.add(name)
                continue
            if isinstance(imported, str) and imported:
                local_names.add(imported)

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
