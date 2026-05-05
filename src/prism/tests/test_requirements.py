"""Unit tests for prism.scanner_extract.requirements (FIND-13 closure)."""

from __future__ import annotations

from prism.scanner_extract.requirements import (
    build_collection_compliance_notes,
    extract_declared_collections_from_meta,
    extract_declared_collections_from_requirements,
    format_requirement_line,
    normalize_included_role_dependencies,
    normalize_meta_role_dependencies,
    normalize_requirements,
)


def test_format_requirement_line_dict_with_src_and_version() -> None:
    assert format_requirement_line({"src": "geerlingguy.nginx", "version": "1.0"}) == (
        "geerlingguy.nginx (version: 1.0)"
    )


def test_format_requirement_line_dict_falls_back_to_name() -> None:
    assert format_requirement_line({"name": "role.x"}) == "role.x"


def test_format_requirement_line_string_returns_str() -> None:
    assert format_requirement_line("plain.role") == "plain.role"


def test_normalize_requirements_drops_empty_lines() -> None:
    out = normalize_requirements(["a", {"src": ""}, {"src": "b", "version": "2"}])
    assert out == ["a", "b (version: 2)"]


def test_normalize_meta_role_dependencies_returns_empty_for_non_list() -> None:
    assert normalize_meta_role_dependencies({"dependencies": None}) == []
    assert normalize_meta_role_dependencies({}) == []


def test_normalize_meta_role_dependencies_formats_entries() -> None:
    out = normalize_meta_role_dependencies(
        {"dependencies": [{"src": "a"}, {"name": "b", "version": "1"}]}
    )
    assert out == ["a", "b (version: 1)"]


def test_normalize_included_role_dependencies_handles_none_sentinel() -> None:
    assert normalize_included_role_dependencies({"included_roles": "none"}) == []
    assert normalize_included_role_dependencies({}) == []


def test_normalize_included_role_dependencies_dedupes_and_sorts() -> None:
    out = normalize_included_role_dependencies({"included_roles": "z, a, a, m"})
    assert out == ["a", "m", "z"]


def test_extract_declared_collections_from_meta_filters_invalid_and_builtin() -> None:
    meta = {
        "galaxy_info": {
            "collections": ["ns.col", "ns2.col2", "builtin.x", "invalid", 123]
        }
    }
    result = extract_declared_collections_from_meta(
        meta, builtin_collection_prefixes=frozenset({"builtin."})
    )
    assert result == {"ns.col", "ns2.col2"}


def test_extract_declared_collections_from_meta_returns_empty_for_bad_input() -> None:
    assert extract_declared_collections_from_meta({}) == set()
    assert extract_declared_collections_from_meta({"galaxy_info": []}) == set()


def test_extract_declared_collections_from_requirements_handles_dict_entries() -> None:
    reqs = [
        {"src": "ns.a"},
        {"name": "ns.b"},
        "ns.c whatever",
        "single",
        123,
    ]
    result = extract_declared_collections_from_requirements(reqs)
    assert result == {"ns.a", "ns.b", "ns.c"}


def test_build_collection_compliance_notes_returns_empty_when_none() -> None:
    notes = build_collection_compliance_notes(
        features={"external_collections": "none"},
        meta={},
        requirements=[],
    )
    assert notes == []


def test_build_collection_compliance_notes_lists_detected_and_missing() -> None:
    notes = build_collection_compliance_notes(
        features={"external_collections": "ns.a, ns.b"},
        meta={"galaxy_info": {"collections": ["ns.a"]}},
        requirements=[{"src": "ns.b"}],
    )
    detected_line = next(n for n in notes if "Detected external collections" in n)
    assert "ns.a" in detected_line and "ns.b" in detected_line
