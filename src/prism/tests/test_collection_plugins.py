import ast

from prism import collection_plugins as plugins


def _parse_module(src: str) -> ast.Module:
    return ast.parse(src)


def test_extract_filter_symbols_from_direct_return_dict():
    parsed = _parse_module(
        """
class FilterModule:
    def filters(self):
        return {'to_upper': to_upper, 'normalize': helper.normalize}
"""
    )

    symbols, mapping, confidence, method = plugins._extract_filter_symbols(parsed, "")

    assert symbols == ["normalize", "to_upper"]
    assert mapping["to_upper"] == "to_upper"
    assert mapping["normalize"] == "normalize"
    assert confidence == "high"
    assert method == "ast"


def test_extract_filter_symbols_from_named_dict_return():
    parsed = _parse_module(
        """
class FilterModule:
    def filters(self):
        mapping = {'alpha': alpha_impl}
        return mapping
"""
    )

    symbols, mapping, confidence, method = plugins._extract_filter_symbols(parsed, "")

    assert symbols == ["alpha"]
    assert mapping == {"alpha": "alpha_impl"}
    assert confidence == "medium"
    assert method == "ast"


def test_extract_filter_symbols_falls_back_to_regex_when_no_filtermodule():
    parsed = _parse_module("value = {'fallback_key': handler}")
    text = "value = {'fallback_key': handler}"

    symbols, mapping, confidence, method = plugins._extract_filter_symbols(parsed, text)

    assert symbols == ["fallback_key"]
    assert mapping == {"fallback_key": None}
    assert confidence == "low"
    assert method == "mixed"


def test_extract_direct_return_dict_keys_returns_empty_when_return_not_dict():
    parsed = _parse_module(
        """
def filters():
    return mapping
"""
    )
    func = parsed.body[0]

    result = plugins._extract_direct_return_dict_keys(func)

    assert result == {}


def test_extract_named_dict_return_keys_returns_empty_for_non_name_return():
    parsed = _parse_module(
        """
def filters():
    mapping = {'x': fn}
    return {'x': fn}
"""
    )
    func = parsed.body[0]

    result = plugins._extract_named_dict_return_keys(func)

    assert result == {}


def test_extract_documentation_literals_ignores_multi_target_assignments():
    parsed = _parse_module(
        """
a = DOCUMENTATION = 'ignored'
DOCUMENTATION = 'short_description: useful plugin'
"""
    )

    blocks = plugins._extract_documentation_literals(parsed)

    assert blocks["DOCUMENTATION"] == "short_description: useful plugin"


def test_extract_short_description_strips_quotes():
    doc = 'short_description: "quoted summary"'

    summary = plugins._extract_short_description_from_documentation(doc)

    assert summary == "quoted summary"


def test_extract_class_method_capability_hints_ignores_dunder_methods():
    parsed = _parse_module(
        """
class LookupModule:
    def run(self):
        return []

    def __repr__(self):
        return 'x'
"""
    )

    hints = plugins._extract_class_method_capability_hints(parsed, "lookup")

    assert hints == ["LookupModule.run"]


def test_extract_python_plugin_summary_uses_module_docstring_fallback(tmp_path):
    plugin_file = tmp_path / "demo.py"
    plugin_file.write_text(
        '"""Module level summary."""\n\nclass Demo:\n    pass\n',
        encoding="utf-8",
    )

    extracted = plugins._extract_python_plugin_summary(plugin_file, "modules")

    assert extracted is not None
    summary, doc_source, *_rest = extracted
    assert summary == "Module level summary."
    assert doc_source == "module_docstring"


def test_plugin_helpers_for_name_and_language_variants(tmp_path):
    assert plugins._plugin_language(tmp_path / "example.py") == "python"
    assert plugins._plugin_language(tmp_path / "example.unknown") == "unknown"
    assert plugins._plugin_name_from_path(tmp_path / "my_filter.py") == "my_filter"


def test_extract_filter_symbols_returns_empty_when_no_match_patterns():
    parsed = _parse_module("value = 1")

    symbols, mapping, confidence, method = plugins._extract_filter_symbols(parsed, "")

    assert symbols == []
    assert mapping == {}
    assert confidence == "low"
    assert method == "mixed"


def test_function_name_from_ast_value_returns_none_for_unsupported_node():
    node = ast.Constant(value=123)
    assert plugins._function_name_from_ast_value(node) is None


def test_resolve_filter_summary_falls_back_when_no_docs():
    parsed = _parse_module("class FilterModule:\n    pass\n")
    summary, source = plugins._resolve_filter_summary(
        parsed,
        "demo_filter",
        {"demo": None},
    )

    assert summary == "Filter plugin `demo_filter`."
    assert source == "fallback"


def test_module_function_docstrings_collects_class_method_docs():
    parsed = _parse_module(
        """
class Demo:
    def run(self):
        \"\"\"Run docs.\"\"\"
        return None
"""
    )

    docs = plugins._module_function_docstrings(parsed)

    assert docs["run"] == "Run docs."


def test_extract_python_plugin_summary_returns_none_when_file_read_fails(
    monkeypatch, tmp_path
):
    plugin_file = tmp_path / "demo.py"
    plugin_file.write_text("pass\n", encoding="utf-8")

    monkeypatch.setattr(
        plugins.Path,
        "read_text",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("denied")),
    )

    assert plugins._extract_python_plugin_summary(plugin_file, "modules") is None


def test_extract_python_plugin_summary_returns_none_for_syntax_error(tmp_path):
    plugin_file = tmp_path / "broken.py"
    plugin_file.write_text("def broken(:\n", encoding="utf-8")

    assert plugins._extract_python_plugin_summary(plugin_file, "modules") is None


def test_extract_class_method_capability_hints_skips_non_functions():
    parsed = _parse_module(
        """
class LookupModule:
    value = 1
    def run(self):
        return []
"""
    )

    hints = plugins._extract_class_method_capability_hints(parsed, "lookup")

    assert hints == ["LookupModule.run"]


def test_extract_short_description_returns_none_when_key_missing():
    assert (
        plugins._extract_short_description_from_documentation("description: demo")
        is None
    )
