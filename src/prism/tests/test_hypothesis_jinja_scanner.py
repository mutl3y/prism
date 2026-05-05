"""Property-based tests for Jinja scanning and task-module detection robustness."""

from __future__ import annotations

import keyword
import string

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from prism.scanner_plugins.ansible.task_line_parsing import detect_task_module
from prism.scanner_plugins.parsers.jinja.analysis_policy import (
    collect_undeclared_jinja_variables,
)

_IDENTIFIER = st.text(
    alphabet=string.ascii_lowercase + string.digits + "_",
    min_size=1,
    max_size=12,
).filter(
    lambda value: value.isidentifier()
    and not keyword.iskeyword(value)
    and value not in {"true", "false", "none", "loop"}
)

_NON_MARKER_TEXT = st.text(
    alphabet=st.characters(blacklist_characters="{}"),
    max_size=40,
)


@settings(max_examples=100)
@given(st.text())
def test_jinja_scanner_never_crashes_on_arbitrary_text(text: str) -> None:
    """collect_undeclared_jinja_variables must not propagate uncaught exceptions.

    TemplateSyntaxError and TemplateAssertionError are caught internally.
    Any other exception escaping is a regression.
    """
    result = collect_undeclared_jinja_variables(text)
    assert isinstance(result, set)


@settings(max_examples=100)
@given(st.text())
def test_jinja_scanner_returns_only_string_variable_names(text: str) -> None:
    """All variable names returned must be non-empty strings."""
    result = collect_undeclared_jinja_variables(text)
    for name in result:
        assert isinstance(name, str)
        assert name  # Jinja variable names are never empty identifiers


@settings(max_examples=100)
@given(st.text())
def test_jinja_scanner_returns_empty_set_when_no_jinja_markers(text: str) -> None:
    """Strings with no '{{' or '{%' markers must immediately return an empty set."""
    if "{{" in text or "{%" in text:
        return  # skip strings that contain Jinja markers
    result = collect_undeclared_jinja_variables(text)
    assert result == set()


@settings(max_examples=100)
@given(st.dictionaries(st.text(max_size=40), st.one_of(st.text(), st.none())))
def test_detect_task_module_never_crashes_on_arbitrary_dict(task: dict) -> None:
    """detect_task_module must return str | None for any dict input without raising."""
    result = detect_task_module(task)
    assert result is None or isinstance(result, str)


@settings(max_examples=100)
@given(st.text(max_size=80))
def test_detect_task_module_on_single_key_dict(key: str) -> None:
    """detect_task_module with a single-key dict must return str | None without raising."""
    result = detect_task_module({key: "value"})
    assert result is None or isinstance(result, str)


@settings(max_examples=80)
@given(
    loop_var=_IDENTIFIER,
    iterable=_IDENTIFIER,
    condition=_IDENTIFIER,
    free_var=_IDENTIFIER,
)
def test_jinja_scanner_excludes_nested_loop_locals(
    loop_var: str,
    iterable: str,
    condition: str,
    free_var: str,
) -> None:
    """Nested control structures should report free vars but not loop-local bindings."""
    assume(len({loop_var, iterable, condition, free_var}) == 4)
    template = (
        f"{{% for {loop_var} in {iterable} %}}"
        f"{{% if {condition} %}}"
        f"{{{{ {loop_var} }}}} {{{{ {free_var} }}}}"
        "{% endif %}{% endfor %}"
    )
    result = collect_undeclared_jinja_variables(template)
    assert loop_var not in result
    assert iterable in result
    assert condition in result
    assert free_var in result


@settings(max_examples=80)
@given(argument_name=_IDENTIFIER, free_var=_IDENTIFIER)
def test_jinja_scanner_excludes_macro_arguments(
    argument_name: str,
    free_var: str,
) -> None:
    """Macro argument bindings should stay local while free variables remain visible."""
    assume(argument_name != free_var)
    template = (
        f"{{% macro demo({argument_name}) %}}"
        f"{{{{ {argument_name} }}}} {{{{ {free_var} }}}}"
        "{% endmacro %}"
        "{{ demo('value') }}"
        f"{{{{ {free_var} }}}}"
    )
    result = collect_undeclared_jinja_variables(template)
    assert argument_name not in result
    assert free_var in result


@settings(max_examples=40, deadline=None)
@given(
    chunks=st.lists(_NON_MARKER_TEXT, min_size=96, max_size=192),
    variable_name=_IDENTIFIER,
)
def test_jinja_scanner_handles_large_unicode_templates(
    chunks: list[str],
    variable_name: str,
) -> None:
    """Large marker-heavy templates should stay within the stable scanner contract."""
    template = "\n".join(f"{chunk} {{{{ {variable_name} }}}}" for chunk in chunks)
    result = collect_undeclared_jinja_variables(template)
    assert variable_name in result
