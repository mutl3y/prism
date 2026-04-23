"""T4-05: Jinja2 sandbox audit guardrails.

Locks in the audit findings:
1. Role content is never used as a Jinja template source — it is only
   parsed for AST inspection in analysis_policy.collect_undeclared_jinja_variables.
2. The analysis env uses SandboxedEnvironment as defense-in-depth.
3. The render env (rendering_seams.build_render_jinja_environment) is used
   only to render Prism's own bundled .j2 templates with role-derived data
   as the context, not as the template body.
"""

from __future__ import annotations

import ast
from pathlib import Path

import jinja2
from jinja2.sandbox import SandboxedEnvironment

from prism.scanner_data.rendering_seams import build_render_jinja_environment
from prism.scanner_plugins.parsers.jinja.analysis_policy import _JINJA_ENV


def test_analysis_env_is_sandboxed() -> None:
    assert isinstance(_JINJA_ENV, SandboxedEnvironment)


def test_render_env_returns_jinja_environment(tmp_path: Path) -> None:
    env = build_render_jinja_environment(template_dir=tmp_path)
    assert isinstance(env, jinja2.Environment)


def test_no_render_call_in_analysis_module() -> None:
    module_path = (
        Path(__file__).resolve().parent.parent
        / "scanner_plugins"
        / "parsers"
        / "jinja"
        / "analysis_policy.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in {"render", "from_string"}:
            raise AssertionError(
                f"analysis_policy.py contains forbidden Jinja attribute "
                f"access: {node.attr} at line {node.lineno}"
            )


def test_no_unsandboxed_jinja_environment_in_role_content_paths() -> None:
    forbidden_files = (
        Path(__file__).resolve().parent.parent
        / "scanner_plugins"
        / "parsers"
        / "jinja"
        / "analysis_policy.py",
    )
    for path in forbidden_files:
        source = path.read_text(encoding="utf-8")
        assert (
            "jinja2.Environment()" not in source
        ), f"{path.name} must not instantiate raw jinja2.Environment for role content"
