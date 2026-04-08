"""Deterministic delegation tests for requirements wrapper compatibility seam."""

from __future__ import annotations

from prism.scanner_extract import requirements_wrapper


def test_format_requirement_line_delegates_to_canonical_helper(monkeypatch):
    calls: list[object] = []

    def fake(item: object) -> str:
        calls.append(item)
        return "formatted"

    monkeypatch.setattr(requirements_wrapper, "_requirements_format_line", fake)

    result = requirements_wrapper.format_requirement_line({"name": "x"})

    assert result == "formatted"
    assert calls == [{"name": "x"}]


def test_normalize_requirements_delegates_to_canonical_helper(monkeypatch):
    calls: list[object] = []

    def fake(requirements: list) -> list[str]:
        calls.append(requirements)
        return ["one", "two"]

    monkeypatch.setattr(requirements_wrapper, "_requirements_normalize", fake)

    reqs = [{"src": "acme.role"}]
    result = requirements_wrapper.normalize_requirements(reqs)

    assert result == ["one", "two"]
    assert calls == [reqs]


def test_normalize_meta_role_dependencies_delegates_to_canonical_helper(monkeypatch):
    calls: list[object] = []

    def fake(meta: dict) -> list[str]:
        calls.append(meta)
        return ["dep"]

    monkeypatch.setattr(requirements_wrapper, "_requirements_normalize_meta_deps", fake)

    meta = {"dependencies": ["a.b"]}
    result = requirements_wrapper.normalize_meta_role_dependencies(meta)

    assert result == ["dep"]
    assert calls == [meta]


def test_normalize_included_role_dependencies_delegates_to_canonical_helper(
    monkeypatch,
):
    calls: list[object] = []

    def fake(features: dict) -> list[str]:
        calls.append(features)
        return ["included.role"]

    monkeypatch.setattr(
        requirements_wrapper,
        "_requirements_normalize_included_roles",
        fake,
    )

    features = {"included_roles": "included.role"}
    result = requirements_wrapper.normalize_included_role_dependencies(features)

    assert result == ["included.role"]
    assert calls == [features]


def test_extract_declared_collections_from_meta_delegates_to_canonical_helper(
    monkeypatch,
):
    calls: list[object] = []

    def fake(meta: dict) -> set[str]:
        calls.append(meta)
        return {"acme.collection"}

    monkeypatch.setattr(
        requirements_wrapper, "_requirements_extract_declared_meta", fake
    )

    meta = {"galaxy_info": {"collections": ["acme.collection"]}}
    result = requirements_wrapper.extract_declared_collections_from_meta(meta)

    assert result == {"acme.collection"}
    assert calls == [meta]


def test_extract_declared_collections_from_requirements_delegates_to_canonical_helper(
    monkeypatch,
):
    calls: list[object] = []

    def fake(requirements: list) -> set[str]:
        calls.append(requirements)
        return {"acme.collection"}

    monkeypatch.setattr(
        requirements_wrapper,
        "_requirements_extract_declared_requirements",
        fake,
    )

    requirements = [{"name": "acme.collection"}]
    result = requirements_wrapper.extract_declared_collections_from_requirements(
        requirements
    )

    assert result == {"acme.collection"}
    assert calls == [requirements]


def test_build_collection_compliance_notes_delegates_with_keyword_args(monkeypatch):
    calls: list[dict[str, object]] = []

    def fake(*, features: dict, meta: dict, requirements: list) -> list[str]:
        calls.append(
            {
                "features": features,
                "meta": meta,
                "requirements": requirements,
            }
        )
        return ["note"]

    monkeypatch.setattr(
        requirements_wrapper,
        "_requirements_build_collection_compliance_notes",
        fake,
    )

    features = {"external_collections": "acme.collection"}
    meta = {"galaxy_info": {"collections": ["acme.collection"]}}
    requirements = [{"name": "acme.collection"}]

    result = requirements_wrapper.build_collection_compliance_notes(
        features=features,
        meta=meta,
        requirements=requirements,
    )

    assert result == ["note"]
    assert calls == [
        {
            "features": features,
            "meta": meta,
            "requirements": requirements,
        }
    ]


def test_build_requirements_display_delegates_with_keyword_args(monkeypatch):
    calls: list[dict[str, object]] = []

    def fake(
        *,
        requirements: list,
        meta: dict,
        features: dict,
        include_collection_checks: bool,
    ) -> tuple[list[str], list[str]]:
        calls.append(
            {
                "requirements": requirements,
                "meta": meta,
                "features": features,
                "include_collection_checks": include_collection_checks,
            }
        )
        return (["req"], ["note"])

    monkeypatch.setattr(requirements_wrapper, "_requirements_build_display", fake)

    requirements = [{"src": "acme.role"}]
    meta = {"dependencies": ["acme.dep"]}
    features = {"included_roles": "acme.dep"}

    result = requirements_wrapper.build_requirements_display(
        requirements=requirements,
        meta=meta,
        features=features,
        include_collection_checks=False,
    )

    assert result == (["req"], ["note"])
    assert calls == [
        {
            "requirements": requirements,
            "meta": meta,
            "features": features,
            "include_collection_checks": False,
        }
    ]
