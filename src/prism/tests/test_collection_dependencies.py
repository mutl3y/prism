"""Tests for collection dependency aggregation module."""

from __future__ import annotations

from prism.scanner_analysis import collection_dependencies


def test_aggregate_collection_dependencies_tracks_conflicts(tmp_path):
    """Should detect version conflicts across sources."""
    collection_root = tmp_path / "demo_collection"
    (collection_root / "collections").mkdir(parents=True)
    (collection_root / "roles" / "role_a" / "meta").mkdir(parents=True)

    (collection_root / "collections" / "requirements.yml").write_text(
        "---\ncollections:\n  - name: community.general\n    version: 8.0.0\n",
        encoding="utf-8",
    )

    (collection_root / "roles" / "role_a" / "meta" / "requirements.yml").write_text(
        "---\n- name: community.general\n  type: collection\n  version: 7.5.0\n",
        encoding="utf-8",
    )

    result = collection_dependencies.aggregate_collection_dependencies(collection_root)

    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["key"] == "community.general"
    assert result["conflicts"][0]["versions"] == ["7.5.0", "8.0.0"]
    assert result["conflicts"][0]["conflict"] == "version_conflict"


def test_aggregate_collection_dependencies_scans_multiple_roles(tmp_path):
    """Should scan requirements from all roles in collection."""
    collection_root = tmp_path / "demo_collection"
    (collection_root / "collections").mkdir(parents=True)
    (collection_root / "roles" / "role_a" / "meta").mkdir(parents=True)
    (collection_root / "roles" / "role_b" / "meta").mkdir(parents=True)

    (collection_root / "roles" / "role_a" / "meta" / "requirements.yml").write_text(
        "---\n- name: geerlingguy.java\n",
        encoding="utf-8",
    )

    (collection_root / "roles" / "role_b" / "meta" / "requirements.yml").write_text(
        "---\n- name: geerlingguy.mysql\n",
        encoding="utf-8",
    )

    result = collection_dependencies.aggregate_collection_dependencies(collection_root)

    role_names = {r["name"] for r in result["roles"]}
    assert "geerlingguy.java" in role_names
    assert "geerlingguy.mysql" in role_names


def test_aggregate_collection_dependencies_handles_missing_files(tmp_path):
    """Should gracefully handle missing requirements files."""
    collection_root = tmp_path / "demo_collection"
    (collection_root / "collections").mkdir(parents=True)
    (collection_root / "roles").mkdir(parents=True)

    result = collection_dependencies.aggregate_collection_dependencies(collection_root)

    assert result["collections"] == []
    assert result["roles"] == []
    assert result["conflicts"] == []


def test_collection_dependency_key_returns_dotted_names():
    """Should extract dotted collection identifiers."""
    entry = {"name": "community.general"}
    assert (
        collection_dependencies._collection_dependency_key(entry, 0)
        == "community.general"
    )


def test_role_dependency_key_uses_name_when_present():
    """Should use name field if available."""
    entry = {"name": "demo.role"}
    assert collection_dependencies._role_dependency_key(entry, 0) == "demo.role"


def test_role_dependency_key_fallback_to_unknown():
    """Should generate unknown key when name and src are missing."""
    entry = {}
    assert collection_dependencies._role_dependency_key(entry, 5) == "unknown:5"

    """Tests for _collection_dependency_key function."""

    def test_returns_name_if_dotted(self):
        """Should return name if it contains a dot (namespace.name format)."""
        entry = {"name": "community.general"}
        assert (
            collection_dependencies._collection_dependency_key(entry, 0)
            == "community.general"
        )

    def test_returns_src_if_dotted_and_no_slash(self):
        """Should return src if name is missing but src contains a dot and no slash."""
        entry = {"src": "community.general"}
        assert (
            collection_dependencies._collection_dependency_key(entry, 0)
            == "community.general"
        )

    def test_returns_none_if_src_has_slash(self):
        """Should return None for git URLs with slashes."""
        entry = {"src": "git+ssh://example/repo"}
        assert collection_dependencies._collection_dependency_key(entry, 0) is None

    def test_returns_none_if_no_dotted_name(self):
        """Should return None if neither name nor src contains a dot."""
        entry = {"name": "simple_name"}
        assert collection_dependencies._collection_dependency_key(entry, 0) is None

    def test_prefers_name_over_src(self):
        """Should prefer name if both are dotted."""
        entry = {"name": "preferred.name", "src": "other.name"}
        assert (
            collection_dependencies._collection_dependency_key(entry, 0)
            == "preferred.name"
        )

    def test_returns_none_for_empty_entry(self):
        """Should return None for empty entry."""
        assert collection_dependencies._collection_dependency_key({}, 0) is None


class TestRoleDependencyKey:
    """Tests for _role_dependency_key function."""

    def test_returns_name_if_present(self):
        """Should return name if it's not empty."""
        entry = {"name": "demo.role"}
        assert collection_dependencies._role_dependency_key(entry, 0) == "demo.role"

    def test_returns_src_if_name_missing(self):
        """Should return src if name is empty or missing."""
        entry = {"name": "", "src": "demo.role"}
        assert collection_dependencies._role_dependency_key(entry, 2) == "demo.role"

    def test_generates_unknown_key_if_both_missing(self):
        """Should generate 'unknown:index' if both name and src are missing."""
        entry = {"name": "", "src": ""}
        assert collection_dependencies._role_dependency_key(entry, 5) == "unknown:5"

    def test_uses_index_in_unknown_key(self):
        """Should include the correct index in unknown key."""
        assert collection_dependencies._role_dependency_key({}, 42) == "unknown:42"


class TestMergeDependencyEntry:
    """Tests for _merge_dependency_entry function."""

    def test_creates_new_entry_in_bucket(self):
        """Should create a new bucket entry if key doesn't exist."""
        bucket: dict[str, dict] = {}
        entry = {"name": "test.role", "version": "1.0.0"}

        collection_dependencies._merge_dependency_entry(
            bucket,
            key="test.role",
            dep_type="role",
            entry=entry,
            source="roles/requirements.yml",
        )

        assert "test.role" in bucket
        assert bucket["test.role"]["key"] == "test.role"
        assert bucket["test.role"]["type"] == "role"
        assert "1.0.0" in bucket["test.role"]["versions"]
        assert "roles/requirements.yml" in bucket["test.role"]["sources"]

    def test_merges_multiple_entries(self):
        """Should merge multiple entries for the same key."""
        bucket: dict[str, dict] = {}

        collection_dependencies._merge_dependency_entry(
            bucket,
            key="test.role",
            dep_type="role",
            entry={"name": "test.role", "version": "1.0.0"},
            source="collections/requirements.yml",
        )

        collection_dependencies._merge_dependency_entry(
            bucket,
            key="test.role",
            dep_type="role",
            entry={"name": "test.role", "version": "2.0.0"},
            source="roles/role_a/meta/requirements.yml",
        )

        assert bucket["test.role"]["versions"] == {"1.0.0", "2.0.0"}
        assert bucket["test.role"]["sources"] == {
            "collections/requirements.yml",
            "roles/role_a/meta/requirements.yml",
        }

    def test_handles_missing_version(self):
        """Should handle entries with missing version."""
        bucket: dict[str, dict] = {}
        entry = {"name": "test.role"}  # No version

        collection_dependencies._merge_dependency_entry(
            bucket,
            key="test.role",
            dep_type="role",
            entry=entry,
            source="roles/requirements.yml",
        )

        assert bucket["test.role"]["versions"] == set()

    def test_stores_raw_entry(self):
        """Should store raw entry data."""
        bucket: dict[str, dict] = {}
        entry = {"name": "test.role", "version": "1.0.0", "extra": "data"}

        collection_dependencies._merge_dependency_entry(
            bucket,
            key="test.role",
            dep_type="role",
            entry=entry,
            source="roles/requirements.yml",
        )

        assert entry in bucket["test.role"]["raw"]


class TestFinalizeDependencyBucket:
    """Tests for _finalize_dependency_bucket function."""

    def test_returns_sorted_items_and_conflicts(self):
        """Should return sorted items and conflicts list."""
        bucket: dict[str, dict] = {}

        # Add entries
        collection_dependencies._merge_dependency_entry(
            bucket,
            key="role_b",
            dep_type="role",
            entry={"name": "role_b", "version": "1.0.0"},
            source="source_1",
        )
        collection_dependencies._merge_dependency_entry(
            bucket,
            key="role_a",
            dep_type="role",
            entry={"name": "role_a", "version": "1.0.0"},
            source="source_1",
        )

        items, conflicts = collection_dependencies._finalize_dependency_bucket(
            bucket, "test_conflict"
        )

        # Should be sorted by key
        assert items[0]["key"] == "role_a"
        assert items[1]["key"] == "role_b"
        assert conflicts == []

    def test_detects_version_conflicts(self):
        """Should detect and report version conflicts."""
        bucket: dict[str, dict] = {}

        collection_dependencies._merge_dependency_entry(
            bucket,
            key="common.role",
            dep_type="role",
            entry={"name": "common.role", "version": "1.0.0"},
            source="source_1",
        )
        collection_dependencies._merge_dependency_entry(
            bucket,
            key="common.role",
            dep_type="role",
            entry={"name": "common.role", "version": "2.0.0"},
            source="source_2",
        )

        items, conflicts = collection_dependencies._finalize_dependency_bucket(
            bucket, "dependency_conflict"
        )

        assert len(conflicts) == 1
        assert conflicts[0]["conflict"] == "dependency_conflict"
        assert conflicts[0]["versions"] == ["1.0.0", "2.0.0"]

    def test_sets_version_only_if_single(self):
        """Should set version field only if there's a single version."""
        bucket: dict[str, dict] = {}

        # Single version
        collection_dependencies._merge_dependency_entry(
            bucket,
            key="single_version",
            dep_type="role",
            entry={"name": "single_version", "version": "1.0.0"},
            source="source_1",
        )

        # Multiple versions
        collection_dependencies._merge_dependency_entry(
            bucket,
            key="multi_version",
            dep_type="role",
            entry={"name": "multi_version", "version": "1.0.0"},
            source="source_1",
        )
        collection_dependencies._merge_dependency_entry(
            bucket,
            key="multi_version",
            dep_type="role",
            entry={"name": "multi_version", "version": "2.0.0"},
            source="source_2",
        )

        items, _ = collection_dependencies._finalize_dependency_bucket(
            bucket, "test_conflict"
        )

        item_by_key = {item["key"]: item for item in items}
        assert item_by_key["single_version"]["version"] == "1.0.0"
        assert item_by_key["multi_version"]["version"] is None


class TestAggregateCollectionDependencies:
    """Tests for _aggregate_collection_dependencies function."""

    def test_aggregates_collection_and_role_dependencies(self, tmp_path):
        """Should aggregate dependencies from all sources."""
        collection_root = tmp_path / "demo_collection"
        (collection_root / "collections").mkdir(parents=True)
        (collection_root / "roles" / "role_a" / "meta").mkdir(parents=True)

        # Collection-level requirements
        (collection_root / "collections" / "requirements.yml").write_text(
            "---\ncollections:\n  - name: community.general\n    version: 8.0.0\n",
            encoding="utf-8",
        )

        # Role-level requirements
        (collection_root / "roles" / "role_a" / "meta" / "requirements.yml").write_text(
            "---\n- name: community.general\n  type: collection\n  version: 7.5.0\n",
            encoding="utf-8",
        )

        result = collection_dependencies.aggregate_collection_dependencies(
            collection_root
        )

        assert "collections" in result
        assert "roles" in result
        assert "conflicts" in result

    def test_detects_version_conflicts_across_sources(self, tmp_path):
        """Should detect version conflicts across different sources."""
        collection_root = tmp_path / "demo_collection"
        (collection_root / "collections").mkdir(parents=True)
        (collection_root / "roles" / "role_a" / "meta").mkdir(parents=True)

        (collection_root / "collections" / "requirements.yml").write_text(
            "---\ncollections:\n  - name: community.general\n    version: 8.0.0\n",
            encoding="utf-8",
        )

        (collection_root / "roles" / "role_a" / "meta" / "requirements.yml").write_text(
            "---\n- name: community.general\n  type: collection\n  version: 7.5.0\n",
            encoding="utf-8",
        )

        result = collection_dependencies.aggregate_collection_dependencies(
            collection_root
        )

        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["key"] == "community.general"
        assert result["conflicts"][0]["versions"] == ["7.5.0", "8.0.0"]

    def test_handles_missing_requirements_files(self, tmp_path):
        """Should gracefully handle missing requirements files."""
        collection_root = tmp_path / "demo_collection"
        (collection_root / "collections").mkdir(parents=True)
        (collection_root / "roles").mkdir(parents=True)

        # No requirements.yml files created

        result = collection_dependencies.aggregate_collection_dependencies(
            collection_root
        )

        assert result["collections"] == []
        assert result["roles"] == []
        assert result["conflicts"] == []

    def test_includes_all_sources_in_result(self, tmp_path):
        """Should include source information for each dependency."""
        collection_root = tmp_path / "demo_collection"
        (collection_root / "collections").mkdir(parents=True)
        (collection_root / "roles" / "role_a" / "meta").mkdir(parents=True)

        (collection_root / "collections" / "requirements.yml").write_text(
            "---\ncollections:\n  - name: community.general\n    version: 8.0.0\n",
            encoding="utf-8",
        )

        (collection_root / "roles" / "role_a" / "meta" / "requirements.yml").write_text(
            "---\n- name: community.general\n  type: collection\n  version: 8.0.0\n",
            encoding="utf-8",
        )

        result = collection_dependencies.aggregate_collection_dependencies(
            collection_root
        )

        general = [c for c in result["collections"] if c["key"] == "community.general"][
            0
        ]
        assert set(general["sources"]) == {
            "collections/requirements.yml",
            "roles/role_a/meta/requirements.yml",
        }

    def test_scans_multiple_roles(self, tmp_path):
        """Should scan requirements from all roles."""
        collection_root = tmp_path / "demo_collection"
        (collection_root / "collections").mkdir(parents=True)
        (collection_root / "roles" / "role_a" / "meta").mkdir(parents=True)
        (collection_root / "roles" / "role_b" / "meta").mkdir(parents=True)

        (collection_root / "roles" / "role_a" / "meta" / "requirements.yml").write_text(
            "---\n- name: geerlingguy.java\n",
            encoding="utf-8",
        )

        (collection_root / "roles" / "role_b" / "meta" / "requirements.yml").write_text(
            "---\n- name: geerlingguy.mysql\n",
            encoding="utf-8",
        )

        result = collection_dependencies.aggregate_collection_dependencies(
            collection_root
        )

        role_names = {r["name"] for r in result["roles"]}
        assert "geerlingguy.java" in role_names
        assert "geerlingguy.mysql" in role_names
