import ast
from pathlib import Path

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
    assert method == plugins.PLUGIN_EXTRACTION_METHOD_BEST_EFFORT


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
    assert method == plugins.PLUGIN_EXTRACTION_METHOD_BEST_EFFORT


def test_extract_filter_symbols_best_effort_method_is_stable_for_all_fallback_paths():
    parsed_with_regex = _parse_module("value = {'fallback_key': handler}")
    parsed_without_regex = _parse_module("value = 1")

    _symbols_a, _mapping_a, confidence_a, method_a = plugins._extract_filter_symbols(
        parsed_with_regex,
        "value = {'fallback_key': handler}",
    )
    _symbols_b, _mapping_b, confidence_b, method_b = plugins._extract_filter_symbols(
        parsed_without_regex,
        "",
    )

    assert confidence_a == "low"
    assert confidence_b == "low"
    assert method_a == plugins.PLUGIN_EXTRACTION_METHOD_BEST_EFFORT
    assert method_b == plugins.PLUGIN_EXTRACTION_METHOD_BEST_EFFORT


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


def test_scan_collection_plugins_records_filter_parse_failures(tmp_path):
    plugin_dir = tmp_path / "plugins" / "filter"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    catalog = plugins.scan_collection_plugins(tmp_path)

    assert catalog["summary"]["files_scanned"] == 1
    assert catalog["summary"]["files_failed"] == 1
    assert catalog["failures"] == [
        {
            "relative_path": "plugins/filter/broken.py",
            "type": "filter",
            "category": "parse",
            "error_type": "SyntaxError",
            "error": catalog["failures"][0]["error"],
            "stage": "ast_parse",
        }
    ]


def test_scan_collection_plugins_records_non_filter_read_failures(
    monkeypatch, tmp_path
):
    plugin_dir = tmp_path / "plugins" / "modules"
    plugin_dir.mkdir(parents=True)
    plugin_file = plugin_dir / "demo.py"
    plugin_file.write_text("def run():\n    return None\n", encoding="utf-8")

    original_read_text = Path.read_text

    def _raise_for_demo(path: Path, *args, **kwargs):
        if path == plugin_file:
            raise OSError("denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _raise_for_demo)

    catalog = plugins.scan_collection_plugins(tmp_path)

    assert catalog["summary"]["files_scanned"] == 1
    assert catalog["summary"]["files_failed"] == 1
    assert catalog["failures"] == [
        {
            "relative_path": "plugins/modules/demo.py",
            "type": "modules",
            "category": "io",
            "error_type": "OSError",
            "error": "denied",
            "stage": "read",
        }
    ]


def test_scan_collection_plugins_keeps_successful_filter_extraction_stable(tmp_path):
    plugin_dir = tmp_path / "plugins" / "filter"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "normalize.py").write_text(
        """
class FilterModule:
    def filters(self):
        return {'normalize': normalize}

def normalize(value):
    \"\"\"Normalize value.\"\"\"
    return value
""".strip()
        + "\n",
        encoding="utf-8",
    )

    catalog = plugins.scan_collection_plugins(tmp_path)

    assert catalog["summary"]["files_scanned"] == 1
    assert catalog["summary"]["files_failed"] == 0
    assert catalog["failures"] == []
    assert len(catalog["by_type"]["filter"]) == 1
    record = catalog["by_type"]["filter"][0]
    assert record["name"] == "normalize"
    assert record["symbols"] == ["normalize"]
    assert record["extraction"]["method"] == plugins.PLUGIN_EXTRACTION_METHOD_AST
    assert record["extraction"]["fallback_used"] is False
