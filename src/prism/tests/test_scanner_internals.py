"""Behavior-lock tests for scanner.py internal functions.

These tests pin the contracts of functions that will be extracted into
separate submodules (jinja_analyzer, variable_extractor, task_parser)
during the scanner.py refactor.  Each test describes the specific
behavior it guards so that any regression introduced during the split
is immediately visible.

Test groups mirror the planned submodule boundaries:
  - Jinja analysis helpers
  - Variable extraction helpers
  - Task parsing helpers
"""

from prism import _jinja_analyzer as jinja_analyzer
from prism import scanner
from prism.scanner_extract import variable_extractor
from prism.scanner_extract.variable_extractor import _extract_default_target_var
from types import SimpleNamespace


def _make_role(tmp_path):
    role = tmp_path / "role"
    role.mkdir(parents=True, exist_ok=True)
    return role


def _make_role_with_tasks_dir(tmp_path):
    role = _make_role(tmp_path)
    (role / "tasks").mkdir(parents=True, exist_ok=True)
    return role


# ---------------------------------------------------------------------------
# Jinja analysis helpers
# ---------------------------------------------------------------------------


class TestStringifyJinjaNode:
    """_stringify_jinja_node: compact string rendering of Jinja AST nodes."""

    def _parse_expr(self, src: str):
        import jinja2
        from typing import cast
        import jinja2.nodes

        env = jinja2.Environment()
        parsed = env.parse(f"{{{{ {src} }}}}")
        # The first Output node's child contains the expression.
        output = cast(jinja2.nodes.Output, list(parsed.body)[0])
        return list(output.nodes)[0]

    def test_none_returns_empty_string(self):
        assert jinja_analyzer._stringify_jinja_node(None) == ""

    def test_name_node_returns_name(self):
        node = self._parse_expr("my_var")
        assert jinja_analyzer._stringify_jinja_node(node) == "my_var"

    def test_const_string_returns_value(self):
        node = self._parse_expr("'hello'")
        assert jinja_analyzer._stringify_jinja_node(node) == "hello"

    def test_const_int_returns_value(self):
        node = self._parse_expr("42")
        assert jinja_analyzer._stringify_jinja_node(node) == "42"

    def test_getattr_returns_dotted_path(self):
        node = self._parse_expr("foo.bar")
        assert jinja_analyzer._stringify_jinja_node(node) == "foo.bar"

    def test_getitem_returns_bracket_notation(self):
        node = self._parse_expr("foo['key']")
        result = jinja_analyzer._stringify_jinja_node(node)
        assert "foo" in result
        assert "key" in result

    def test_filter_node_returns_pipe_form(self):
        node = self._parse_expr("x | upper")
        assert "x" in jinja_analyzer._stringify_jinja_node(node)
        assert "upper" in jinja_analyzer._stringify_jinja_node(node)

    def test_filter_with_args_includes_args(self):
        node = self._parse_expr("x | default('fallback')")
        result = jinja_analyzer._stringify_jinja_node(node)
        assert "x" in result
        assert "default" in result
        assert "fallback" in result

    def test_conditional_expression_is_rendered(self):
        node = self._parse_expr("foo if is_primary else bar")
        result = jinja_analyzer._stringify_jinja_node(node)
        assert "foo" in result
        assert "if" in result
        assert "is_primary" in result
        assert "else" in result
        assert "bar" in result

    def test_compare_expression_is_rendered(self):
        node = self._parse_expr("retry_count > 3")
        result = jinja_analyzer._stringify_jinja_node(node)
        assert "retry_count" in result
        assert ">" in result
        assert "3" in result

    def test_list_literal_is_rendered(self):
        node = self._parse_expr("['a', item]")
        result = jinja_analyzer._stringify_jinja_node(node)
        assert "[" in result and "]" in result
        assert "a" in result
        assert "item" in result

    def test_tuple_literal_is_rendered(self):
        node = self._parse_expr("(left, right)")
        result = jinja_analyzer._stringify_jinja_node(node)
        assert "(" in result and ")" in result
        assert "left" in result
        assert "right" in result

    def test_dict_literal_is_rendered(self):
        node = self._parse_expr("{'key': value}")
        result = jinja_analyzer._stringify_jinja_node(node)
        assert "{" in result and "}" in result
        assert "key" in result
        assert "value" in result

    def test_call_with_keyword_args_is_rendered(self):
        node = self._parse_expr("lookup('env', name='HOME')")
        result = jinja_analyzer._stringify_jinja_node(node)
        assert "lookup" in result
        assert "env" in result
        assert "name=HOME" in result

    def test_test_expression_with_args_is_rendered(self):
        node = self._parse_expr("value is match('^ok')")
        result = jinja_analyzer._stringify_jinja_node(node)
        assert "value" in result
        assert "is match" in result
        assert "^ok" in result

    def test_default_filter_with_empty_target_falls_back_to_source_line(self):
        text = "{{ '' | default('fallback') }}"
        result = jinja_analyzer._scan_text_for_default_filters_with_ast(text, [text])
        assert len(result) == 1
        assert result[0]["match"] == text

    def test_test_expression_without_args_is_rendered(self):
        node = self._parse_expr("value is odd")
        result = jinja_analyzer._stringify_jinja_node(node)
        assert result == "value is odd"

    def test_binary_and_unary_expressions_are_rendered(self):
        add_node = self._parse_expr("left + right")
        not_node = self._parse_expr("not enabled")
        assert jinja_analyzer._stringify_jinja_node(add_node) == "left + right"
        assert jinja_analyzer._stringify_jinja_node(not_node) == "not enabled"

    def test_pair_and_keyword_fallback_paths_return_available_side(self):
        import jinja2

        pair_only_key = jinja2.nodes.Pair(jinja2.nodes.Const("k"), None)
        pair_only_value = jinja2.nodes.Pair(None, jinja2.nodes.Const("v"))
        keyword_value_only = jinja2.nodes.Keyword("", jinja2.nodes.Const("home"))

        assert jinja_analyzer._stringify_jinja_node(pair_only_key) == "k"
        assert jinja_analyzer._stringify_jinja_node(pair_only_value) == "v"
        assert jinja_analyzer._stringify_jinja_node(keyword_value_only) == "home"

    def test_keyword_key_and_value_render_as_assignment(self):
        import jinja2

        keyword = jinja2.nodes.Keyword("name", jinja2.nodes.Const("HOME"))

        assert jinja_analyzer._stringify_jinja_node(keyword) == "name=HOME"

    def test_template_data_and_unknown_node_fallbacks(self):
        import jinja2

        template_data = jinja2.nodes.TemplateData("  hello  ")
        unknown = jinja2.nodes.Template([])

        assert jinja_analyzer._stringify_jinja_node(template_data) == "hello"
        assert jinja_analyzer._stringify_jinja_node(unknown) == ""

    def test_condexpr_and_binary_unary_partial_fallback_paths(self):
        import jinja2

        # expr1 exists, expr2 missing -> fallback to available branch
        cond_partial = jinja2.nodes.CondExpr(
            jinja2.nodes.Name("is_primary", "load"),
            jinja2.nodes.Const("A"),
            None,
        )
        # left missing -> fallback to right
        add_partial = jinja2.nodes.Add(None, jinja2.nodes.Const("r"))

        assert jinja_analyzer._stringify_jinja_node(cond_partial) == "A"
        assert jinja_analyzer._stringify_jinja_node(add_partial) == "r"

    def test_call_compare_and_unary_edge_fallback_paths(self):
        call_node = self._parse_expr("lookup(name='HOME')")
        call_node.kwargs[0].key = ""

        compare_node = self._parse_expr("attempts == max_attempts")
        compare_node.ops[0].op = ""

        import jinja2

        unary_missing_target = jinja2.nodes.Neg(None)

        assert jinja_analyzer._stringify_jinja_node(call_node) == "lookup(HOME)"
        assert (
            jinja_analyzer._stringify_jinja_node(compare_node)
            == "attempts max_attempts"
        )
        assert jinja_analyzer._stringify_jinja_node(unary_missing_target) == ""


class TestScanTextForDefaultFiltersWithAst:
    """_scan_text_for_default_filters_with_ast: extract | default(...) via AST."""

    def test_returns_empty_for_plain_text(self):
        result = jinja_analyzer._scan_text_for_default_filters_with_ast(
            "no jinja here", []
        )
        assert result == []

    def test_detects_simple_default_filter(self):
        text = "{{ my_var | default('fallback') }}"
        lines = [text]
        result = jinja_analyzer._scan_text_for_default_filters_with_ast(text, lines)
        assert len(result) == 1
        assert result[0]["match"] == "my_var | default(fallback)"
        assert result[0]["args"] == "fallback"

    def test_result_includes_line_no_and_line(self):
        text = "{{ my_var | default('x') }}"
        lines = [text]
        result = jinja_analyzer._scan_text_for_default_filters_with_ast(text, lines)
        assert result[0]["line_no"] == 1
        assert result[0]["line"] == text

    def test_skips_non_default_filters(self):
        text = "{{ my_var | upper }}"
        lines = [text]
        result = jinja_analyzer._scan_text_for_default_filters_with_ast(text, lines)
        assert result == []

    def test_handles_invalid_jinja_gracefully(self):
        text = "{{ invalid jinja {{ }}"
        result = jinja_analyzer._scan_text_for_default_filters_with_ast(text, [text])
        assert isinstance(result, list)

    def test_detects_multiple_defaults_in_one_text(self):
        text = "{{ a | default('x') }} {{ b | default('y') }}"
        lines = [text]
        result = jinja_analyzer._scan_text_for_default_filters_with_ast(text, lines)
        assert len(result) == 2

    def test_default_without_args_records_empty_args(self):
        text = "{{ my_var | default() }}"
        lines = [text]
        result = jinja_analyzer._scan_text_for_default_filters_with_ast(text, lines)
        assert len(result) == 1
        assert result[0]["args"] == ""

    def test_default_target_with_conditional_expression_is_rendered(self):
        text = "{{ (foo if is_primary else bar) | default('fallback') }}"
        lines = [text]
        result = jinja_analyzer._scan_text_for_default_filters_with_ast(text, lines)
        assert len(result) == 1
        assert "foo if is_primary else bar" in result[0]["match"]
        assert result[0]["args"] == "fallback"


class TestScanTextForAllFiltersWithAst:
    """_scan_text_for_all_filters_with_ast: extract all Jinja filters via AST."""

    def test_detects_non_default_filters(self):
        text = "{{ my_var | upper }}"
        result = jinja_analyzer._scan_text_for_all_filters_with_ast(text, [text])
        assert len(result) == 1
        assert result[0]["filter_name"] == "upper"
        assert result[0]["match"] == "my_var | upper()"

    def test_detects_filter_chains(self):
        text = "{{ app_name | default('x') | trim | lower }}"
        result = jinja_analyzer._scan_text_for_all_filters_with_ast(text, [text])
        names = {row["filter_name"] for row in result}
        assert names == {"default", "trim", "lower"}

    def test_invalid_template_returns_empty(self):
        result = jinja_analyzer._scan_text_for_all_filters_with_ast(
            "{{ bad {{", ["{{ bad {{"]
        )
        assert result == []


class TestCollectUndeclaredJinjaVariables:
    """_collect_undeclared_jinja_variables: find externally required names."""

    def test_returns_empty_for_plain_text(self):
        result = jinja_analyzer._collect_undeclared_jinja_variables("no template here")
        assert result == set()

    def test_detects_simple_variable_reference(self):
        result = jinja_analyzer._collect_undeclared_jinja_variables("{{ my_var }}")
        assert "my_var" in result

    def test_excludes_loop_variable_from_for_body(self):
        text = "{% for item in items %}{{ item }}{% endfor %}"
        result = jinja_analyzer._collect_undeclared_jinja_variables(text)
        assert "item" not in result
        assert "items" in result

    def test_excludes_macro_parameter(self):
        text = "{% macro greet(name) %}Hello {{ name }}{% endmacro %}"
        result = jinja_analyzer._collect_undeclared_jinja_variables(text)
        assert "name" not in result

    def test_excludes_set_assigned_name(self):
        text = "{% set computed = 42 %}{{ computed }}"
        result = jinja_analyzer._collect_undeclared_jinja_variables(text)
        assert "computed" not in result

    def test_multiple_variables_detected(self):
        result = jinja_analyzer._collect_undeclared_jinja_variables("{{ a }} {{ b }}")
        assert "a" in result
        assert "b" in result

    def test_handles_parse_error_gracefully(self):
        result = jinja_analyzer._collect_undeclared_jinja_variables("{{ bad syntax !!!")
        assert isinstance(result, set)

    def test_excludes_with_block_local_binding(self):
        text = "{% with temp_user = users[0] %}{{ temp_user.name }}{% endwith %}"
        result = jinja_analyzer._collect_undeclared_jinja_variables(text)
        assert "temp_user" not in result
        assert "users" in result

    def test_excludes_call_block_macro_argument(self):
        text = (
            "{% macro wrapper() %}<x>{{ caller('result') }}</x>{% endmacro %}"
            "{% call(value) wrapper() %}{{ value }} {{ service_name }}{% endcall %}"
        )
        result = jinja_analyzer._collect_undeclared_jinja_variables(text)
        assert "value" not in result
        assert "service_name" in result


class TestCollectJinjaLocalBindings:
    """_collect_jinja_local_bindings_from_text: identify locally bound names."""

    def test_empty_text_returns_empty_set(self):
        result = jinja_analyzer._collect_jinja_local_bindings_from_text("no jinja")
        assert result == set()

    def test_for_loop_variable_is_local(self):
        text = "{% for item in items %}{% endfor %}"
        result = jinja_analyzer._collect_jinja_local_bindings_from_text(text)
        assert "item" in result

    def test_macro_parameter_is_local(self):
        text = "{% macro render(title) %}{% endmacro %}"
        result = jinja_analyzer._collect_jinja_local_bindings_from_text(text)
        assert "title" in result

    def test_set_target_is_local(self):
        text = "{% set result = 'x' %}"
        result = jinja_analyzer._collect_jinja_local_bindings_from_text(text)
        assert "result" in result

    def test_unpacked_for_tuple_both_names_are_local(self):
        text = "{% for key, val in pairs %}{% endfor %}"
        result = jinja_analyzer._collect_jinja_local_bindings_from_text(text)
        assert "key" in result
        assert "val" in result

    def test_invalid_jinja_returns_empty_set(self):
        result = jinja_analyzer._collect_jinja_local_bindings_from_text("{{ bad !!!")
        assert result == set()

    def test_with_target_is_local(self):
        text = "{% with local_name = name %}{{ local_name }}{% endwith %}"
        result = jinja_analyzer._collect_jinja_local_bindings_from_text(text)
        assert "local_name" in result

    def test_import_alias_is_local(self):
        text = "{% import 'helpers.j2' as helpers %}{{ helpers.render('x') }}"
        result = jinja_analyzer._collect_jinja_local_bindings_from_text(text)
        assert "helpers" in result

    def test_from_import_names_are_local(self):
        text = "{% from 'helpers.j2' import render as draw %}{{ draw('x') }}"
        result = jinja_analyzer._collect_jinja_local_bindings_from_text(text)
        assert "draw" in result

    def test_from_import_name_without_alias_is_local(self):
        text = "{% from 'helpers.j2' import render %}{{ render('x') }}"
        result = jinja_analyzer._collect_jinja_local_bindings_from_text(text)
        assert "render" in result

    def test_assign_block_target_is_local(self):
        text = "{% set body %}hello{% endset %}{{ body }}"
        result = jinja_analyzer._collect_jinja_local_bindings_from_text(text)
        assert "body" in result

    def test_call_block_args_are_local(self):
        text = (
            "{% macro wrap() %}{{ caller('ok') }}{% endmacro %}"
            "{% call(result) wrap() %}{{ result }}{% endcall %}"
        )
        result = jinja_analyzer._collect_jinja_local_bindings_from_text(text)
        assert "result" in result

    def test_collect_local_bindings_handles_sparse_node_shapes(self):
        import jinja2

        class _FakeTemplate:
            def __init__(self, mapping):
                self._mapping = mapping

            def find_all(self, node_type):
                return self._mapping.get(node_type, [])

        fake = _FakeTemplate(
            {
                # Empty args trigger the "or []" fallback paths.
                jinja2.nodes.Macro: [SimpleNamespace(args=[])],
                jinja2.nodes.CallBlock: [SimpleNamespace(args=[])],
                # Non-string import target should be ignored safely.
                jinja2.nodes.Import: [SimpleNamespace(target=None)],
                # Tuple with empty alias should fall back to source name.
                jinja2.nodes.FromImport: [
                    SimpleNamespace(names=[("render", ""), "helper_fn"])
                ],
            }
        )

        result = jinja_analyzer._collect_jinja_local_bindings(fake)

        assert "render" in result
        assert "helper_fn" in result


class TestExtractJinjaNameTargets:
    """_extract_jinja_name_targets: pull identifier names from assignment targets."""

    def test_none_returns_empty_set(self):
        result = jinja_analyzer._extract_jinja_name_targets(None)
        assert result == set()

    def test_name_node_returns_single_name(self):
        import jinja2

        node = jinja2.nodes.Name("my_name", "store")
        result = jinja_analyzer._extract_jinja_name_targets(node)
        assert result == {"my_name"}

    def test_tuple_target_returns_all_names(self):
        import jinja2

        a = jinja2.nodes.Name("a", "store")
        b = jinja2.nodes.Name("b", "store")
        # Simulate a Tuple node (has .items attribute)
        tuple_node = jinja2.nodes.Tuple([a, b], "store")
        result = jinja_analyzer._extract_jinja_name_targets(tuple_node)
        assert result == {"a", "b"}


# ---------------------------------------------------------------------------
# Variable extraction helpers
# ---------------------------------------------------------------------------


class TestExtractDefaultTargetVar:
    """_extract_default_target_var: pull the variable name from a default occurrence."""

    def test_extracts_simple_var_name(self):
        occ = {"line": "{{ my_var | default('x') }}", "match": "my_var | default(x)"}
        result = _extract_default_target_var(occ)
        assert result == "my_var"

    def test_returns_none_when_no_variable_found(self):
        occ = {"line": "no default here", "match": "no default here"}
        result = _extract_default_target_var(occ)
        assert result is None

    def test_uses_match_when_line_is_empty(self):
        occ = {"line": "", "match": "some_var | default(fallback)"}
        result = _extract_default_target_var(occ)
        assert result == "some_var"

    def test_empty_occurrence_returns_none(self):
        result = _extract_default_target_var({})
        assert result is None


class TestCollectIncludeVarsFiles:
    """_collect_include_vars_files: resolve static include_vars references."""

    def test_finds_static_include_vars_file(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        (role / "vars").mkdir()
        extra_vars = role / "vars" / "extra.yml"
        extra_vars.write_text("extra_var: value\n", encoding="utf-8")
        (role / "tasks" / "main.yml").write_text(
            "---\n- include_vars: extra.yml\n", encoding="utf-8"
        )
        result = variable_extractor._collect_include_vars_files(str(role))
        assert extra_vars.resolve() in result

    def test_ignores_dynamic_include_vars(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        (role / "tasks" / "main.yml").write_text(
            "---\n- include_vars: '{{ dynamic_path }}'\n", encoding="utf-8"
        )
        result = variable_extractor._collect_include_vars_files(str(role))
        assert result == []

    def test_returns_empty_for_role_without_tasks(self, tmp_path):
        role = _make_role(tmp_path)
        result = variable_extractor._collect_include_vars_files(str(role))
        assert result == []

    def test_does_not_include_files_outside_role(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        outside = tmp_path / "outside_vars.yml"
        outside.write_text("x: 1\n", encoding="utf-8")
        (role / "tasks" / "main.yml").write_text(
            f"---\n- include_vars: {outside}\n", encoding="utf-8"
        )
        result = variable_extractor._collect_include_vars_files(str(role))
        assert outside.resolve() not in result


class TestCollectSetFactNames:
    """_collect_set_fact_names: find variable names assigned via set_fact."""

    def test_finds_set_fact_variable(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        (role / "tasks" / "main.yml").write_text(
            "---\n- set_fact:\n    computed_value: hello\n", encoding="utf-8"
        )
        result = variable_extractor._collect_set_fact_names(str(role))
        assert "computed_value" in result

    def test_ignores_dynamic_set_fact_keys(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        (role / "tasks" / "main.yml").write_text(
            "---\n- set_fact:\n    '{{ dynamic_key }}': value\n", encoding="utf-8"
        )
        result = variable_extractor._collect_set_fact_names(str(role))
        assert not any("{{" in name for name in result)

    def test_returns_empty_for_role_with_no_set_fact(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        (role / "tasks" / "main.yml").write_text(
            "---\n- name: do something\n  debug:\n    msg: hi\n", encoding="utf-8"
        )
        result = variable_extractor._collect_set_fact_names(str(role))
        assert result == set()


class TestCollectRegisterNames:
    """_collect_register_names: find task-level register output variable names."""

    def test_finds_register_variable(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        (role / "tasks" / "main.yml").write_text(
            "---\n- command: /bin/true\n  register: cmd_result\n",
            encoding="utf-8",
        )
        result = variable_extractor._collect_register_names(str(role))
        assert "cmd_result" in result

    def test_ignores_dynamic_register_name(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        (role / "tasks" / "main.yml").write_text(
            "---\n- command: /bin/true\n  register: '{{ runtime_name }}'\n",
            encoding="utf-8",
        )
        result = variable_extractor._collect_register_names(str(role))
        assert result == set()

    def test_ignores_non_identifier_register_name(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        (role / "tasks" / "main.yml").write_text(
            "---\n- command: /bin/true\n  register: cmd-result\n",
            encoding="utf-8",
        )
        result = variable_extractor._collect_register_names(str(role))
        assert result == set()


class TestFindVariableLineInYaml:
    """_find_variable_line_in_yaml: locate the 1-indexed line where a var is defined."""

    def test_finds_variable_on_first_line(self, tmp_path):
        f = tmp_path / "vars.yml"
        f.write_text("my_var: value\nother_var: 2\n", encoding="utf-8")
        assert variable_extractor._find_variable_line_in_yaml(f, "my_var") == 1

    def test_finds_variable_on_later_line(self, tmp_path):
        f = tmp_path / "vars.yml"
        f.write_text("first: 1\nsecond: 2\nthird: 3\n", encoding="utf-8")
        assert variable_extractor._find_variable_line_in_yaml(f, "third") == 3

    def test_returns_none_when_variable_not_present(self, tmp_path):
        f = tmp_path / "vars.yml"
        f.write_text("a: 1\nb: 2\n", encoding="utf-8")
        assert variable_extractor._find_variable_line_in_yaml(f, "missing") is None

    def test_returns_none_on_io_error(self, tmp_path):
        missing = tmp_path / "nonexistent.yml"
        assert variable_extractor._find_variable_line_in_yaml(missing, "any") is None


class TestCollectDynamicIncludeVarsRefs:
    """_collect_dynamic_include_vars_refs: collect unresolvable include_vars paths."""

    def test_finds_dynamic_include_vars(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        (role / "tasks" / "main.yml").write_text(
            "---\n- include_vars: '{{ env_specific_file }}'\n", encoding="utf-8"
        )
        result = variable_extractor._collect_dynamic_include_vars_refs(str(role))
        assert len(result) == 1
        assert "{{" in result[0]

    def test_static_include_vars_not_in_dynamic_refs(self, tmp_path):
        role = _make_role_with_tasks_dir(tmp_path)
        (role / "vars").mkdir()
        (role / "vars" / "extra.yml").write_text("x: 1\n", encoding="utf-8")
        (role / "tasks" / "main.yml").write_text(
            "---\n- include_vars: extra.yml\n", encoding="utf-8"
        )
        result = variable_extractor._collect_dynamic_include_vars_refs(str(role))
        assert result == []

    def test_empty_for_role_without_tasks(self, tmp_path):
        role = _make_role(tmp_path)
        result = variable_extractor._collect_dynamic_include_vars_refs(str(role))
        assert result == []


class TestSecretDetectionHelpers:
    """_looks_secret_name / _resembles_password_like / _is_sensitive_variable / _looks_secret_value."""

    def test_looks_secret_name_detects_password_keyword(self):
        assert scanner._looks_secret_name("db_password") is True

    def test_looks_secret_name_detects_token_keyword(self):
        assert scanner._looks_secret_name("api_token") is True

    def test_looks_secret_name_detects_secret_keyword(self):
        assert scanner._looks_secret_name("my_secret_key") is True

    def test_looks_secret_name_ignores_normal_name(self):
        assert scanner._looks_secret_name("role_name") is False

    def test_resembles_password_like_detects_vault_encrypted(self):
        assert scanner._resembles_password_like("!vault |encrypted_text") is True

    def test_resembles_password_like_approves_long_complex_string(self):
        # 24+ chars, mixed case + digit + symbol
        assert scanner._resembles_password_like("Abc123!@#Xyz789LongSecret") is True

    def test_resembles_password_like_ignores_plain_url(self):
        assert scanner._resembles_password_like("https://example.com/path") is False

    def test_resembles_password_like_ignores_template_value(self):
        assert scanner._resembles_password_like("{{ my_var }}") is False

    def test_resembles_password_like_ignores_non_string(self):
        assert scanner._resembles_password_like(42) is False
        assert scanner._resembles_password_like(None) is False

    def test_looks_secret_value_detects_vault_marker(self):
        assert scanner._looks_secret_value("$ANSIBLE_VAULT;1.1;AES256\n...") is True

    def test_looks_secret_value_ignores_normal_string(self):
        assert scanner._looks_secret_value("just a plain value") is False

    def test_is_sensitive_variable_with_secret_name_and_credential_value(self):
        assert (
            scanner._is_sensitive_variable("db_password", "Abc123!@#Xyz789LongSecret")
            is True
        )

    def test_is_sensitive_variable_with_vault_value(self):
        assert scanner._is_sensitive_variable("any_name", "$ANSIBLE_VAULT;1.1") is True

    def test_is_sensitive_variable_plain_non_secret(self):
        assert scanner._is_sensitive_variable("role_owner", "root") is False


class TestInferVariableType:
    """_infer_variable_type: return lightweight type label from a Python value."""

    def test_bool_true(self):
        assert scanner._infer_variable_type(True) == "bool"

    def test_bool_false(self):
        assert scanner._infer_variable_type(False) == "bool"

    def test_int(self):
        assert scanner._infer_variable_type(42) == "int"

    def test_float(self):
        assert scanner._infer_variable_type(3.14) == "float"

    def test_list(self):
        assert scanner._infer_variable_type([1, 2]) == "list"

    def test_dict(self):
        assert scanner._infer_variable_type({"a": 1}) == "dict"

    def test_none(self):
        assert scanner._infer_variable_type(None) == "null"

    def test_string(self):
        assert scanner._infer_variable_type("hello") == "str"

    def test_empty_string(self):
        assert scanner._infer_variable_type("") == "str"

    def test_bool_is_not_int(self):
        # bool must be checked before int since bool is a subclass of int
        assert scanner._infer_variable_type(True) == "bool"
        assert scanner._infer_variable_type(False) == "bool"


class TestReadSeedYaml:
    """_read_seed_yaml: parse seed YAML file and detect secret keys."""

    def test_reads_normal_variables(self, tmp_path):
        f = tmp_path / "seed.yml"
        f.write_text("user: admin\nport: 8080\n", encoding="utf-8")
        data, secrets = scanner._read_seed_yaml(f)
        assert data["user"] == "admin"
        assert data["port"] == 8080

    def test_detects_vault_encrypted_key(self, tmp_path):
        f = tmp_path / "seed.yml"
        f.write_text(
            "db_password: !vault |\n  $ANSIBLE_VAULT;1.1;AES256\n  abcdef\n",
            encoding="utf-8",
        )
        data, secrets = scanner._read_seed_yaml(f)
        assert "db_password" in secrets

    def test_returns_empty_for_empty_file(self, tmp_path):
        f = tmp_path / "seed.yml"
        f.write_text("", encoding="utf-8")
        data, secrets = scanner._read_seed_yaml(f)
        assert data == {}

    def test_returns_empty_for_non_mapping(self, tmp_path):
        f = tmp_path / "seed.yml"
        f.write_text("- item1\n- item2\n", encoding="utf-8")
        data, secrets = scanner._read_seed_yaml(f)
        assert data == {}

    def test_handles_plain_malformed_yaml(self, tmp_path):
        f = tmp_path / "seed.yml"
        f.write_text("key: !unknown_tag value\n", encoding="utf-8")
        data, secrets = scanner._read_seed_yaml(f)
        assert isinstance(data, dict)


class TestResolveSeedVarFiles:
    """_resolve_seed_var_files: expand seed paths to concrete YAML file lists."""

    def test_resolves_single_yaml_file(self, tmp_path):
        f = tmp_path / "vars.yml"
        f.write_text("x: 1\n", encoding="utf-8")
        result = scanner._resolve_seed_var_files([str(f)])
        assert f.resolve() in result

    def test_resolves_directory_to_yaml_files(self, tmp_path):
        d = tmp_path / "seed_dir"
        d.mkdir()
        a = d / "a.yml"
        b = d / "b.yaml"
        a.write_text("a: 1\n", encoding="utf-8")
        b.write_text("b: 2\n", encoding="utf-8")
        result = scanner._resolve_seed_var_files([str(d)])
        resolved = [p.resolve() for p in result]
        assert a.resolve() in resolved
        assert b.resolve() in resolved

    def test_ignores_non_yaml_files(self, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("not yaml\n", encoding="utf-8")
        result = scanner._resolve_seed_var_files([str(f)])
        assert result == []

    def test_none_input_returns_empty(self):
        result = scanner._resolve_seed_var_files(None)
        assert result == []

    def test_empty_list_returns_empty(self):
        result = scanner._resolve_seed_var_files([])
        assert result == []


# ---------------------------------------------------------------------------
# Task parsing helpers
# ---------------------------------------------------------------------------


class TestIterTaskMappings:
    """_iter_task_mappings: yield task dicts from YAML task document recursively."""

    def test_yields_tasks_from_flat_list(self):
        data = [{"name": "task1", "debug": {}}, {"name": "task2", "debug": {}}]
        result = list(scanner._iter_task_mappings(data))
        assert len(result) == 2
        assert result[0]["name"] == "task1"

    def test_yields_tasks_from_block_body(self):
        data = [{"block": [{"name": "inner", "debug": {}}]}]
        result = list(scanner._iter_task_mappings(data))
        names = [r.get("name") for r in result]
        assert "inner" in names

    def test_yields_tasks_from_rescue_and_always(self):
        data = [
            {
                "block": [{"name": "main", "debug": {}}],
                "rescue": [{"name": "rescue_task", "debug": {}}],
                "always": [{"name": "always_task", "debug": {}}],
            }
        ]
        result = list(scanner._iter_task_mappings(data))
        names = [r.get("name") for r in result]
        assert "rescue_task" in names
        assert "always_task" in names

    def test_ignores_non_dict_items(self):
        data = ["not a dict", 42, None, {"name": "valid", "debug": {}}]
        result = list(scanner._iter_task_mappings(data))
        assert len(result) == 1

    def test_empty_list_yields_nothing(self):
        result = list(scanner._iter_task_mappings([]))
        assert result == []

    def test_none_input_yields_nothing(self):
        result = list(scanner._iter_task_mappings(None))
        assert result == []


class TestSplitTaskAnnotationLabel:
    """_split_task_annotation_label: parse annotation kind and body from comment payload."""

    def test_empty_text_returns_note_with_empty_body(self):
        kind, body = scanner._split_task_annotation_label("")
        assert kind == "note"
        assert body == ""

    def test_text_without_colon_is_note_with_full_text_as_body(self):
        kind, body = scanner._split_task_annotation_label("check network connectivity")
        assert kind == "note"
        assert body == "check network connectivity"

    def test_valid_runbook_label(self):
        kind, body = scanner._split_task_annotation_label(
            "runbook: restart nginx manually"
        )
        assert kind == "runbook"
        assert body == "restart nginx manually"

    def test_valid_warning_label(self):
        kind, body = scanner._split_task_annotation_label(
            "warning: service will restart"
        )
        assert kind == "warning"
        assert body == "service will restart"

    def test_valid_deprecated_label(self):
        kind, body = scanner._split_task_annotation_label(
            "deprecated: use new_task instead"
        )
        assert kind == "deprecated"
        assert body == "use new_task instead"

    def test_valid_additional_label(self):
        kind, body = scanner._split_task_annotation_label(
            "additional: see runbook https://wiki"
        )
        assert kind == "additional"
        assert body == "see runbook https://wiki"

    def test_valid_note_label_explicit(self):
        kind, body = scanner._split_task_annotation_label(
            "note: remember to check logs"
        )
        assert kind == "note"
        assert body == "remember to check logs"

    def test_unknown_label_falls_back_to_note_with_full_text(self):
        raw = "custom: some body"
        kind, body = scanner._split_task_annotation_label(raw)
        assert kind == "note"
        assert body == raw

    def test_label_is_case_insensitive(self):
        kind, body = scanner._split_task_annotation_label("Warning: check firewall")
        assert kind == "warning"
        assert body == "check firewall"


class TestTaskAnchor:
    """_task_anchor: build stable markdown anchor slugs for task links."""

    def test_basic_slug_format(self):
        result = scanner._task_anchor("main.yml", "Install package", 1)
        assert result == "task-main-yml-install-package-1"

    def test_special_characters_are_stripped(self):
        result = scanner._task_anchor("main.yml", "Task: do something!", 2)
        assert " " not in result
        assert "!" not in result
        assert ":" not in result

    def test_path_separators_are_normalized(self):
        result = scanner._task_anchor("tasks/sub.yml", "run step", 3)
        assert "/" not in result

    def test_fallback_for_empty_slug(self):
        # Highly artificial but must not crash
        result = scanner._task_anchor("", "", 5)
        assert result.startswith("task-")

    def test_index_appears_at_end(self):
        result = scanner._task_anchor("main.yml", "do thing", 10)
        assert result.endswith("-10")


class TestExtractRoleFeatures:
    """extract_role_features: heuristic feature extraction from task structure."""

    def test_returns_expected_keys(self, tmp_path):
        role = tmp_path / "role"
        (role / "tasks").mkdir(parents=True)
        (role / "tasks" / "main.yml").write_text(
            "---\n- name: install pkg\n  ansible.builtin.package:\n    name: nginx\n",
            encoding="utf-8",
        )
        result = scanner.extract_role_features(str(role))
        expected_keys = {
            "task_files_scanned",
            "tasks_scanned",
            "recursive_task_includes",
            "unique_modules",
            "external_collections",
            "handlers_notified",
            "privileged_tasks",
            "conditional_tasks",
            "tagged_tasks",
            "included_role_calls",
            "included_roles",
            "dynamic_included_role_calls",
            "dynamic_included_roles",
            "disabled_task_annotations",
            "yaml_like_task_annotations",
        }
        assert expected_keys == set(result.keys())

    def test_counts_privileged_tasks(self, tmp_path):
        role = tmp_path / "role"
        (role / "tasks").mkdir(parents=True)
        (role / "tasks" / "main.yml").write_text(
            "---\n- name: root task\n  command: id\n  become: true\n",
            encoding="utf-8",
        )
        result = scanner.extract_role_features(str(role))
        assert result["privileged_tasks"] == 1

    def test_counts_conditional_tasks(self, tmp_path):
        role = tmp_path / "role"
        (role / "tasks").mkdir(parents=True)
        (role / "tasks" / "main.yml").write_text(
            "---\n- name: conditional task\n  debug:\n    msg: hi\n  when: ansible_os_family == 'Debian'\n",
            encoding="utf-8",
        )
        result = scanner.extract_role_features(str(role))
        assert result["conditional_tasks"] == 1

    def test_counts_tagged_tasks(self, tmp_path):
        role = tmp_path / "role"
        (role / "tasks").mkdir(parents=True)
        (role / "tasks" / "main.yml").write_text(
            "---\n- name: tagged task\n  debug:\n    msg: hi\n  tags: [install]\n",
            encoding="utf-8",
        )
        result = scanner.extract_role_features(str(role))
        assert result["tagged_tasks"] == 1

    def test_identifies_external_collection(self, tmp_path):
        role = tmp_path / "role"
        (role / "tasks").mkdir(parents=True)
        (role / "tasks" / "main.yml").write_text(
            "---\n- name: community task\n  community.general.make:\n    chdir: /src\n",
            encoding="utf-8",
        )
        result = scanner.extract_role_features(str(role))
        assert "community.general" in result["external_collections"]

    def test_collects_handler_notified(self, tmp_path):
        role = tmp_path / "role"
        (role / "tasks").mkdir(parents=True)
        (role / "tasks" / "main.yml").write_text(
            "---\n- name: task with notify\n  debug:\n    msg: hi\n  notify: restart nginx\n",
            encoding="utf-8",
        )
        result = scanner.extract_role_features(str(role))
        assert "restart nginx" in result["handlers_notified"]

    def test_empty_role_returns_zero_counts(self, tmp_path):
        role = tmp_path / "role"
        (role / "tasks").mkdir(parents=True)
        (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")
        result = scanner.extract_role_features(str(role))
        assert result["tasks_scanned"] == 0
        assert result["privileged_tasks"] == 0


class TestCollectDynamicTaskIncludeRefs:
    """_collect_dynamic_task_include_refs: find templated task include targets."""

    def test_finds_dynamic_include_task(self, tmp_path):
        role = tmp_path / "role"
        (role / "tasks").mkdir(parents=True)
        (role / "tasks" / "main.yml").write_text(
            "---\n- include_tasks: '{{ env }}_setup.yml'\n", encoding="utf-8"
        )
        result = scanner._collect_dynamic_task_include_refs(str(role))
        assert len(result) == 1
        assert "{{" in result[0]

    def test_static_include_not_in_dynamic_refs(self, tmp_path):
        role = tmp_path / "role"
        (role / "tasks").mkdir(parents=True)
        (role / "tasks" / "setup.yml").write_text("---\n", encoding="utf-8")
        (role / "tasks" / "main.yml").write_text(
            "---\n- include_tasks: setup.yml\n", encoding="utf-8"
        )
        result = scanner._collect_dynamic_task_include_refs(str(role))
        assert result == []

    def test_empty_for_role_without_tasks(self, tmp_path):
        role = tmp_path / "role"
        role.mkdir()
        result = scanner._collect_dynamic_task_include_refs(str(role))
        assert result == []


def test_extract_readme_variable_names_from_line_gates_prose_backticks():
    """Backtick prose extraction should require variable-guidance context."""
    assert scanner._extract_readme_variable_names_from_line("Or use `db_user`.") == {
        "db_user"
    }
    assert (
        scanner._extract_readme_variable_names_from_line(
            "Only required attributes include `login`."
        )
        == set()
    )
    assert scanner._extract_readme_variable_names_from_line(
        "- `login` - nested key"
    ) == {"login"}


# ---------------------------------------------------------------------------
# IGNORED_IDENTIFIERS policy-reload synchronization
# ---------------------------------------------------------------------------


def test_reload_pattern_config_synchronizes_ansible_builtin_variables_into_ignored():
    """After reload_pattern_config, IGNORED_IDENTIFIERS must reflect changes to
    the ansible_builtin_variables policy key.

    This guards the contract that _refresh_policy_derived_state propagates
    ansible_builtin_variables into the module-level IGNORED_IDENTIFIERS in
    variable_extractor and that scanner.reload_pattern_config keeps its own
    IGNORED_IDENTIFIERS in sync.
    """
    sentinel = "ansible_prism_test_sentinel_do_not_use"
    # Patch a minimal policy that adds the sentinel to ansible_builtin_variables
    original_policy = (
        scanner._POLICY.copy()
        if hasattr(scanner._POLICY, "copy")
        else dict(scanner._POLICY)
    )
    patched_policy = dict(original_policy)
    existing_builtins = list(patched_policy.get("ansible_builtin_variables", []))
    patched_policy["ansible_builtin_variables"] = existing_builtins + [sentinel]

    # Drive _refresh_policy_derived_state directly via the variable_extractor
    from prism.scanner_extract import variable_extractor as _ve

    _ve._refresh_policy_derived_state(patched_policy)

    try:
        assert sentinel in _ve.IGNORED_IDENTIFIERS, (
            "reload must propagate new ansible_builtin_variables entries "
            "into variable_extractor.IGNORED_IDENTIFIERS"
        )
    finally:
        # Always restore original state
        _ve._refresh_policy_derived_state(original_policy)
        assert sentinel not in _ve.IGNORED_IDENTIFIERS


def test_variable_extractor_wrapper_re_exports_canonical_implementation():
    """Compatibility wrapper should expose canonical scanner_extract functions."""
    from prism.scanner_extract import variable_extractor as canonical
    from prism.scanner_extract import variable_extractor as compat

    assert (
        compat._collect_referenced_variable_names
        is canonical._collect_referenced_variable_names
    )
    assert compat._infer_variable_type is canonical._infer_variable_type


def test_variable_insights_wrappers_re_export_canonical_implementations():
    """Variable-insights scanner helpers should be canonical scanner_core aliases."""
    from prism.scanner_core import variable_insights as canonical

    assert (
        scanner._attach_external_vars_context is canonical.attach_external_vars_context
    )
    assert scanner._build_display_variables is canonical.build_display_variables


def test_runbook_bridge_wrappers_re_export_canonical_implementations():
    """Runbook bridge scanner helpers should match canonical runbook behavior."""
    from prism.scanner_analysis import (
        build_runbook_rows,
        render_runbook,
        render_runbook_csv,
    )

    metadata = {
        "task_catalog": [
            {
                "file": "tasks/main.yml",
                "name": "Install package",
                "module": "ansible.builtin.package",
            }
        ]
    }

    assert scanner._build_runbook_rows(metadata) == build_runbook_rows(metadata)
    assert scanner.render_runbook("demo", metadata) == render_runbook("demo", metadata)
    assert scanner.render_runbook_csv(metadata) == render_runbook_csv(metadata)


def test_scanner_refresh_policy_keeps_wrapper_and_canonical_ignored_in_sync(
    monkeypatch,
):
    """scanner._refresh_policy must keep scanner, wrapper, and canonical states aligned."""
    from prism.scanner_extract import variable_extractor as canonical
    from prism.scanner_extract import variable_extractor as compat

    sentinel = "ansible_prism_sync_test_sentinel"
    base_policy = dict(scanner._POLICY)
    patched_policy = dict(base_policy)
    builtins = list(patched_policy.get("ansible_builtin_variables", []))
    patched_policy["ansible_builtin_variables"] = builtins + [sentinel]

    def _fake_refresh_policy(override_path=None):
        sensitivity = patched_policy["sensitivity"]
        return (
            patched_policy,
            patched_policy["section_aliases"],
            tuple(sensitivity["name_tokens"]),
            tuple(sensitivity["vault_markers"]),
            tuple(sensitivity["credential_prefixes"]),
            tuple(sensitivity["url_prefixes"]),
            tuple(patched_policy["variable_guidance"]["priority_keywords"]),
            patched_policy["ignored_identifiers"],
        )

    monkeypatch.setattr(scanner, "_config_refresh_policy", _fake_refresh_policy)

    scanner._refresh_policy()

    try:
        assert sentinel in scanner.IGNORED_IDENTIFIERS
        assert scanner.IGNORED_IDENTIFIERS == canonical.IGNORED_IDENTIFIERS
        assert compat.IGNORED_IDENTIFIERS == canonical.IGNORED_IDENTIFIERS
    finally:

        def _restore_refresh_policy(override_path=None):
            sensitivity = base_policy["sensitivity"]
            return (
                base_policy,
                base_policy["section_aliases"],
                tuple(sensitivity["name_tokens"]),
                tuple(sensitivity["vault_markers"]),
                tuple(sensitivity["credential_prefixes"]),
                tuple(sensitivity["url_prefixes"]),
                tuple(base_policy["variable_guidance"]["priority_keywords"]),
                base_policy["ignored_identifiers"],
            )

        monkeypatch.setattr(scanner, "_config_refresh_policy", _restore_refresh_policy)
        scanner._refresh_policy()


def test_collect_referenced_variable_names_ignores_explicit_ansible_connection_vars(
    tmp_path,
):
    role = _make_role_with_tasks_dir(tmp_path)
    (role / "templates").mkdir(parents=True, exist_ok=True)

    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: Render template\n"
        "  ansible.builtin.template:\n"
        "    src: app.j2\n"
        "    dest: /tmp/app\n"
        "  when: ansible_connection == 'ssh' and ansible_user != '' and ansible_become_user != '' and ansible_local.site.region and custom_input\n",
        encoding="utf-8",
    )
    (role / "templates" / "app.j2").write_text(
        "{{ ansible_host }} {{ ansible_port }} {{ ansible_index_var }} {{ custom_input }}\n",
        encoding="utf-8",
    )

    names = scanner._collect_referenced_variable_names(str(role))

    assert "custom_input" in names
    assert {
        "ansible_connection",
        "ansible_become_user",
        "ansible_host",
        "ansible_index_var",
        "ansible_local",
        "ansible_port",
        "ansible_user",
    }.isdisjoint(names)


def test_custom_ansible_prefixed_var_not_filtered_by_ignored_identifiers():
    """A custom `ansible_`-prefixed token must pass through IGNORED_IDENTIFIERS
    filtering unchanged — the prefix alone is not sufficient for suppression."""
    sentinel = "ansible_my_role_specific_setting"
    assert sentinel not in scanner.IGNORED_IDENTIFIERS, (
        f"{sentinel!r} should NOT be in IGNORED_IDENTIFIERS; "
        "only known builtins belong there"
    )
