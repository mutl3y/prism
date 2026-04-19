"""Tests for GF2-W2-T02: plugin-injectable collection namespace filtering."""

from __future__ import annotations

import importlib


def _load_requirements():
    return importlib.import_module("prism.scanner_extract.requirements")


def _load_catalog():
    return importlib.import_module("prism.scanner_extract.task_catalog_assembly")


def _load_adapters():
    return importlib.import_module("prism.scanner_core.task_extract_adapters")


# --- RED: _extract_collection_from_module_name with prefix parameter ---


class TestExtractCollectionFromModuleName:
    def test_filters_ansible_prefix_when_provided(self):
        mod = _load_catalog()
        result = mod._extract_collection_from_module_name(
            "ansible.builtin.copy",
            builtin_collection_prefixes=frozenset({"ansible."}),
        )
        assert result is None

    def test_returns_collection_when_no_prefixes(self):
        mod = _load_catalog()
        result = mod._extract_collection_from_module_name(
            "ansible.builtin.copy",
            builtin_collection_prefixes=frozenset(),
        )
        assert result == "ansible.builtin"

    def test_returns_non_builtin_collection(self):
        mod = _load_catalog()
        result = mod._extract_collection_from_module_name(
            "community.general.ufw",
            builtin_collection_prefixes=frozenset({"ansible."}),
        )
        assert result == "community.general"

    def test_filters_custom_prefix(self):
        mod = _load_catalog()
        result = mod._extract_collection_from_module_name(
            "myorg.internal.module",
            builtin_collection_prefixes=frozenset({"myorg."}),
        )
        assert result is None

    def test_default_no_filtering(self):
        mod = _load_catalog()
        result = mod._extract_collection_from_module_name("ansible.builtin.copy")
        assert result == "ansible.builtin"

    def test_short_module_name_returns_none(self):
        mod = _load_catalog()
        result = mod._extract_collection_from_module_name("copy")
        assert result is None


class TestPublicExtractCollectionWrapper:
    def test_public_wrapper_accepts_prefix(self):
        mod = _load_catalog()
        result = mod.extract_collection_from_module_name(
            "ansible.builtin.copy",
            builtin_collection_prefixes=frozenset({"ansible."}),
        )
        assert result is None

    def test_adapter_accepts_prefix(self):
        adapters = _load_adapters()
        result = adapters.extract_collection_from_module_name(
            "ansible.builtin.copy",
            builtin_collection_prefixes=frozenset({"ansible."}),
        )
        assert result is None


# --- RED: extract_declared_collections_from_meta with prefix parameter ---


class TestExtractDeclaredCollectionsFromMeta:
    def test_filters_ansible_prefix_when_provided(self):
        mod = _load_requirements()
        meta = {
            "galaxy_info": {"collections": ["ansible.netcommon", "community.general"]}
        }
        result = mod.extract_declared_collections_from_meta(
            meta, builtin_collection_prefixes=frozenset({"ansible."})
        )
        assert result == {"community.general"}

    def test_returns_all_when_no_prefixes(self):
        mod = _load_requirements()
        meta = {
            "galaxy_info": {"collections": ["ansible.netcommon", "community.general"]}
        }
        result = mod.extract_declared_collections_from_meta(
            meta, builtin_collection_prefixes=frozenset()
        )
        assert result == {"ansible.netcommon", "community.general"}

    def test_default_no_filtering(self):
        mod = _load_requirements()
        meta = {
            "galaxy_info": {"collections": ["ansible.netcommon", "community.general"]}
        }
        result = mod.extract_declared_collections_from_meta(meta)
        assert result == {"ansible.netcommon", "community.general"}


# --- RED: extract_declared_collections_from_requirements with prefix parameter ---


class TestExtractDeclaredCollectionsFromRequirements:
    def test_filters_ansible_prefix_when_provided(self):
        mod = _load_requirements()
        reqs = [
            {"name": "ansible.netcommon"},
            {"name": "community.general"},
        ]
        result = mod.extract_declared_collections_from_requirements(
            reqs, builtin_collection_prefixes=frozenset({"ansible."})
        )
        assert result == {"community.general"}

    def test_returns_all_when_no_prefixes(self):
        mod = _load_requirements()
        reqs = [
            {"name": "ansible.netcommon"},
            {"name": "community.general"},
        ]
        result = mod.extract_declared_collections_from_requirements(
            reqs, builtin_collection_prefixes=frozenset()
        )
        assert result == {"ansible.netcommon", "community.general"}

    def test_default_no_filtering(self):
        mod = _load_requirements()
        reqs = [
            {"name": "ansible.netcommon"},
            {"name": "community.general"},
        ]
        result = mod.extract_declared_collections_from_requirements(reqs)
        assert result == {"ansible.netcommon", "community.general"}


# --- RED: build_collection_compliance_notes threads prefix ---


class TestBuildCollectionComplianceNotes:
    def test_threads_prefix_to_declared_extractors(self):
        mod = _load_requirements()
        features = {"external_collections": "community.general"}
        meta = {
            "galaxy_info": {"collections": ["community.general", "ansible.netcommon"]}
        }
        reqs = [{"name": "community.general"}, {"name": "ansible.netcommon"}]
        notes = mod.build_collection_compliance_notes(
            features=features,
            meta=meta,
            requirements=reqs,
            builtin_collection_prefixes=frozenset({"ansible."}),
        )
        assert len(notes) >= 1
        assert "community.general" in notes[0]

    def test_no_prefix_includes_all_declared(self):
        mod = _load_requirements()
        features = {"external_collections": "community.general"}
        meta = {
            "galaxy_info": {"collections": ["ansible.netcommon", "community.general"]}
        }
        reqs = [{"name": "community.general"}]
        notes_with = mod.build_collection_compliance_notes(
            features=features,
            meta=meta,
            requirements=reqs,
            builtin_collection_prefixes=frozenset(),
        )
        notes_without = mod.build_collection_compliance_notes(
            features=features,
            meta=meta,
            requirements=reqs,
        )
        assert notes_with == notes_without


# --- RED: build_requirements_display threads prefix ---


class TestBuildRequirementsDisplay:
    def test_threads_prefix(self):
        mod = _load_requirements()
        result, _ = mod.build_requirements_display(
            requirements=[],
            meta={},
            features={},
            builtin_collection_prefixes=frozenset({"ansible."}),
        )
        assert isinstance(result, list)


# --- Acceptance: no hardcoded ansible references in filter logic ---


class TestNoHardcodedAnsibleFiltering:
    def test_no_startswith_ansible_in_requirements(self):
        import inspect

        mod = _load_requirements()
        src_meta = inspect.getsource(mod.extract_declared_collections_from_meta)
        src_reqs = inspect.getsource(mod.extract_declared_collections_from_requirements)
        assert 'startswith("ansible.' not in src_meta
        assert "startswith('ansible." not in src_meta
        assert 'startswith("ansible.' not in src_reqs
        assert "startswith('ansible." not in src_reqs

    def test_no_startswith_ansible_in_catalog(self):
        import inspect

        mod = _load_catalog()
        src = inspect.getsource(mod._extract_collection_from_module_name)
        assert 'startswith("ansible.' not in src
        assert "startswith('ansible." not in src

    def test_no_non_ansible_in_requirements_docstrings(self):
        mod = _load_requirements()
        doc1 = mod.extract_declared_collections_from_meta.__doc__ or ""
        doc2 = mod.extract_declared_collections_from_requirements.__doc__ or ""
        assert "non-ansible" not in doc1.lower()
        assert "non-ansible" not in doc2.lower()
