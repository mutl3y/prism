"""T1-02: targeted unit tests, batch 3 — io/output, dataload, loader.

Pure-Python tests using tmp_path; no scanner runtime invocation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest


# ---- scanner_io/output.py -------------------------------------------------


def test_build_final_output_payload_normalizes_warnings() -> None:
    from prism.scanner_io.output import build_final_output_payload

    p = build_final_output_payload(
        role_name="r",
        description="d",
        variables={"x": 1},
        requirements=[],
        default_filters=[],
        metadata={"warnings": ["w"]},
    )
    assert p["role_name"] == "r"
    assert p["warnings"] == ["w"]

    p2 = build_final_output_payload(
        role_name="r",
        description="d",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={"warnings": "not-a-list"},
    )
    assert p2["warnings"] == []


@pytest.mark.parametrize(
    "name,fmt,expected_suffix",
    [
        ("README.md", "md", ".md"),
        ("README.md", "html", ".html"),
        ("README.md", "json", ".json"),
        ("README.md", "pdf", ".pdf"),
        ("README.html", "html", ".html"),
        ("README.htm", "html", ".htm"),
        ("README.json", "json", ".json"),
        ("README.pdf", "pdf", ".pdf"),
    ],
)
def test_resolve_output_path(name: str, fmt: str, expected_suffix: str) -> None:
    from prism.scanner_io.output import resolve_output_path

    assert resolve_output_path(name, fmt).suffix.lower() == expected_suffix


def test_render_final_output_md_passthrough_and_json() -> None:
    from prism.scanner_io.output import render_final_output
    from prism.scanner_data.contracts_output import FinalOutputPayload

    assert render_final_output("# hi", "md", "title") == "# hi"

    json_out = render_final_output(
        "# hi",
        "json",
        "title",
        payload=cast(FinalOutputPayload, {"a": 1}),
    )
    assert isinstance(json_out, str)
    assert '"a": 1' in json_out and json_out.endswith("\n")


def test_render_final_output_html_basic_structure() -> None:
    from prism.scanner_io.output import render_final_output

    out = render_final_output("# hi", "html", "Title <X>")
    assert isinstance(out, str)
    assert out.startswith("<!doctype html>")
    # title should be html-escaped
    assert "Title &lt;X&gt;" in out


def test_render_final_output_unknown_format_raises() -> None:
    from prism.scanner_io.output import render_final_output
    import pytest

    with pytest.raises(ValueError, match="unknown output_format"):
        render_final_output("body", "weird", "T")


def test_write_output_text_and_bytes(tmp_path: Path) -> None:
    from prism.scanner_io.output import write_output

    p1 = tmp_path / "a.md"
    s = write_output(p1, "hello")
    assert Path(s).read_text(encoding="utf-8") == "hello"

    p2 = tmp_path / "b.bin"
    s2 = write_output(p2, b"\x00\x01\x02")
    assert Path(s2).read_bytes() == b"\x00\x01\x02"


# ---- scanner_io/loader.py -------------------------------------------------


def test_map_argument_spec_type_branches() -> None:
    from prism.scanner_io.loader import map_argument_spec_type

    assert map_argument_spec_type("str") == "string"
    assert map_argument_spec_type("int") == "int"
    assert map_argument_spec_type("bool") == "bool"
    assert map_argument_spec_type("dict") == "dict"
    assert map_argument_spec_type("list") == "list"
    assert map_argument_spec_type("float") == "string"
    assert map_argument_spec_type("RAW") == "string"
    assert map_argument_spec_type("unknown") == "documented"
    assert map_argument_spec_type(123) == "documented"  # type: ignore[arg-type]
    assert map_argument_spec_type(None) == "documented"  # type: ignore[arg-type]


def test_load_yaml_file_with_no_di_falls_back_to_safe_load(tmp_path: Path) -> None:
    from prism.scanner_io.loader import load_yaml_file

    good = tmp_path / "g.yml"
    good.write_text("a: 1\n", encoding="utf-8")
    assert load_yaml_file(good) == {"a": 1}

    bad = tmp_path / "b.yml"
    bad.write_text("a: [oops\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="yaml_load_error"):
        load_yaml_file(bad)

    missing = tmp_path / "m.yml"
    with pytest.raises(RuntimeError, match="yaml_load_error"):
        load_yaml_file(missing)


def test_parse_yaml_candidate_uses_default_policy(tmp_path: Path) -> None:
    from prism.scanner_io.loader import parse_yaml_candidate

    role_root = tmp_path
    bad = tmp_path / "tasks" / "x.yml"
    bad.parent.mkdir()
    bad.write_text("a: [oops\n", encoding="utf-8")
    failure = parse_yaml_candidate(bad, role_root)
    assert failure is not None
    assert failure["file"] == "tasks/x.yml"
    assert "error" in failure


def test_parse_yaml_candidate_reports_encoding_errors(tmp_path: Path) -> None:
    import prism.scanner_io.loader as loader_module

    role_root = tmp_path
    bad = tmp_path / "tasks" / "encoded.yml"
    bad.parent.mkdir()
    bad.write_bytes(b"\xff\xfe\x00\x00")

    original_get_policy = loader_module._get_yaml_parsing_policy
    loader_module._get_yaml_parsing_policy = lambda di=None: object()
    try:
        failure = loader_module.parse_yaml_candidate(bad, role_root)
    finally:
        loader_module._get_yaml_parsing_policy = original_get_policy

    assert failure is not None
    assert failure["file"] == "tasks/encoded.yml"
    assert str(failure["error"]).startswith("encoding_error:")


def test_parse_yaml_candidate_reports_value_errors(tmp_path: Path) -> None:
    import prism.scanner_io.loader as loader_module

    role_root = tmp_path
    bad = tmp_path / "tasks" / "value.yml"
    bad.parent.mkdir()
    bad.write_text("ignored: true\n", encoding="utf-8")

    original_get_policy = loader_module._get_yaml_parsing_policy
    original_safe_load = loader_module.yaml.safe_load
    loader_module._get_yaml_parsing_policy = lambda di=None: object()
    loader_module.yaml.safe_load = lambda text: (_ for _ in ()).throw(
        ValueError("bad value for value.yml")
    )
    try:
        failure = loader_module.parse_yaml_candidate(bad, role_root)
    finally:
        loader_module._get_yaml_parsing_policy = original_get_policy
        loader_module.yaml.safe_load = original_safe_load

    assert failure is not None
    assert failure["file"] == "tasks/value.yml"
    assert failure["error"] == "value_error: bad value for value.yml"


def test_iter_role_yaml_candidates_filters_extensions_and_excludes(
    tmp_path: Path,
) -> None:
    from prism.scanner_io.loader import iter_role_yaml_candidates

    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks" / "a.yml").write_text("a: 1\n", encoding="utf-8")
    (tmp_path / "tasks" / "b.yaml").write_text("b: 2\n", encoding="utf-8")
    (tmp_path / "tasks" / "c.txt").write_text("ignore\n", encoding="utf-8")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "x.yml").write_text("x: 1\n", encoding="utf-8")

    results = list(
        iter_role_yaml_candidates(
            tmp_path,
            exclude_paths=None,
            ignored_dirs={"ignored"},
            is_relpath_excluded_fn=lambda p, ex: False,
            is_path_excluded_fn=lambda p, root, ex: False,
        )
    )
    rels = sorted(p.name for p in results)
    assert rels == ["a.yml", "b.yaml"]


def test_collect_yaml_parse_failures_returns_failures(tmp_path: Path) -> None:
    from prism.scanner_io.loader import collect_yaml_parse_failures

    bad = tmp_path / "x.yml"
    bad.write_text("a: [oops\n", encoding="utf-8")
    good = tmp_path / "y.yml"
    good.write_text("a: 1\n", encoding="utf-8")

    failures = collect_yaml_parse_failures(
        str(tmp_path),
        exclude_paths=None,
        iter_yaml_candidates_fn=lambda root, ex: [bad, good],
    )
    assert len(failures) == 1
    assert failures[0]["file"] == "x.yml"


def test_collect_yaml_parse_failures_preserves_candidate_order(tmp_path: Path) -> None:
    from prism.scanner_io.loader import collect_yaml_parse_failures

    first = tmp_path / "b.yml"
    first.write_text("a: [oops\n", encoding="utf-8")
    second = tmp_path / "a.yml"
    second.write_text("b: [oops\n", encoding="utf-8")

    failures = collect_yaml_parse_failures(
        str(tmp_path),
        exclude_paths=None,
        iter_yaml_candidates_fn=lambda root, ex: [first, second],
    )

    assert [failure["file"] for failure in failures] == ["b.yml", "a.yml"]


# ---- scanner_extract/dataload.py ------------------------------------------


def test_load_role_variable_maps_merges_defaults_and_vars(tmp_path: Path) -> None:
    from prism.scanner_extract.dataload import load_role_variable_maps

    defaults_file = tmp_path / "defaults" / "main.yml"
    defaults_file.parent.mkdir()
    defaults_file.write_text("alpha: 1\nbeta: 2\n", encoding="utf-8")
    vars_file = tmp_path / "vars" / "main.yml"
    vars_file.parent.mkdir()
    vars_file.write_text("gamma: 3\n", encoding="utf-8")

    def iter_candidates(role_root: Path, kind: str) -> list[Path]:
        f = role_root / kind / "main.yml"
        return [f] if f.is_file() else []

    def loader(p: Path) -> object:
        import yaml as _y

        return _y.safe_load(p.read_text(encoding="utf-8"))

    defaults_data, vars_data, defaults_src, vars_src = load_role_variable_maps(
        str(tmp_path),
        include_vars_main=True,
        iter_variable_map_candidates_fn=iter_candidates,
        load_yaml_file_fn=loader,
    )
    assert defaults_data == {"alpha": 1, "beta": 2}
    assert vars_data == {"gamma": 3}
    assert "alpha" in defaults_src and "gamma" in vars_src


def test_load_role_variable_maps_skips_vars_when_disabled(tmp_path: Path) -> None:
    from prism.scanner_extract.dataload import load_role_variable_maps

    def iter_candidates(role_root: Path, kind: str) -> list[Path]:
        return []

    defaults_data, vars_data, _, _ = load_role_variable_maps(
        str(tmp_path),
        include_vars_main=False,
        iter_variable_map_candidates_fn=iter_candidates,
        load_yaml_file_fn=lambda p: None,
    )
    assert defaults_data == {} and vars_data == {}


def test_load_role_variable_maps_ignores_non_dict_yaml(tmp_path: Path) -> None:
    from prism.scanner_extract.dataload import load_role_variable_maps

    def iter_candidates(role_root: Path, kind: str) -> list[Path]:
        return [role_root / "f.yml"]

    defaults_data, vars_data, _, _ = load_role_variable_maps(
        str(tmp_path),
        include_vars_main=True,
        iter_variable_map_candidates_fn=iter_candidates,
        load_yaml_file_fn=lambda p: ["not", "a", "dict"],
    )
    assert defaults_data == {} and vars_data == {}


def test_iter_role_argument_spec_entries_yields_options(tmp_path: Path) -> None:
    from prism.scanner_extract.dataload import iter_role_argument_spec_entries

    arg_specs_file = tmp_path / "meta" / "argument_specs.yml"
    arg_specs_file.parent.mkdir()
    arg_specs_file.write_text(
        "argument_specs:\n  main:\n    options:\n      foo:\n        type: str\n",
        encoding="utf-8",
    )

    def loader(p: Path) -> object:
        import yaml as _y

        return _y.safe_load(p.read_text(encoding="utf-8"))

    def load_meta(role_path: str) -> dict[str, Any]:
        return {}

    entries = list(
        iter_role_argument_spec_entries(
            str(tmp_path),
            load_yaml_file_fn=loader,
            load_meta_fn=load_meta,
        )
    )
    assert any(
        name == "foo" and src == "meta/argument_specs.yml" for src, name, _ in entries
    )


def test_iter_role_argument_spec_entries_skips_templated_names(tmp_path: Path) -> None:
    from prism.scanner_extract.dataload import iter_role_argument_spec_entries

    def loader(p: Path) -> object:
        return None

    def load_meta(role_path: str) -> dict[str, Any]:
        return {
            "argument_specs": {
                "main": {
                    "options": {
                        "{{ templated }}": {"type": "str"},
                        "valid": {"type": "int"},
                        "invalid_spec": "not-a-dict",
                    }
                },
                "bad_task": "not-a-dict",
            }
        }

    entries = list(
        iter_role_argument_spec_entries(
            str(tmp_path),
            load_yaml_file_fn=loader,
            load_meta_fn=load_meta,
        )
    )
    names = [name for _, name, _ in entries]
    assert names == ["valid"]


def test_iter_role_argument_spec_entries_handles_no_meta(tmp_path: Path) -> None:
    from prism.scanner_extract.dataload import iter_role_argument_spec_entries

    entries = list(
        iter_role_argument_spec_entries(
            str(tmp_path),
            load_yaml_file_fn=lambda p: None,
            load_meta_fn=lambda role_path: "not-a-dict",  # type: ignore[arg-type, return-value]
        )
    )
    assert entries == []
