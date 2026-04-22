"""Tests for fsrc scanner_config package port."""

from __future__ import annotations


import pytest

from prism.scanner_config.section import (
    DEFAULT_DOC_MARKER_PREFIX,
    SECTION_CONFIG_FILENAME,
    SECTION_CONFIG_FILENAMES,
)
from prism.scanner_config.legacy_retirement import (
    LEGACY_SECTION_CONFIG_FILENAME,
    LEGACY_SECTION_CONFIG_UNSUPPORTED,
    LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE,
    LEGACY_RUNTIME_PATH_UNAVAILABLE,
    format_legacy_retirement_error,
)
from prism.scanner_config.readme import resolve_role_config_file
from prism.scanner_config.marker import load_readme_marker_prefix
from prism.scanner_config.policy import (
    load_fail_on_unconstrained_dynamic_includes,
    load_policy_rules_from_config,
)
from prism.scanner_config.patterns import (
    load_pattern_config,
    build_policy_context,
)
from prism.scanner_config.style import load_section_display_titles


class TestSectionConstants:
    def test_default_doc_marker_prefix(self):
        assert DEFAULT_DOC_MARKER_PREFIX == "prism"

    def test_section_config_filename(self):
        assert SECTION_CONFIG_FILENAME == ".prism.yml"

    def test_section_config_filenames_tuple(self):
        assert isinstance(SECTION_CONFIG_FILENAMES, tuple)
        assert SECTION_CONFIG_FILENAME in SECTION_CONFIG_FILENAMES


class TestLegacyRetirementConstants:
    def test_legacy_section_config_filename(self):
        assert LEGACY_SECTION_CONFIG_FILENAME == ".ansible_role_doc.yml"

    def test_legacy_section_config_unsupported_code(self):
        assert LEGACY_SECTION_CONFIG_UNSUPPORTED == "LEGACY_SECTION_CONFIG_UNSUPPORTED"

    def test_legacy_runtime_path_unavailable_code(self):
        assert LEGACY_RUNTIME_PATH_UNAVAILABLE == "LEGACY_RUNTIME_PATH_UNAVAILABLE"

    def test_format_legacy_retirement_error_format(self):
        result = format_legacy_retirement_error("CODE", "message text")
        assert result == "CODE: message text"

    def test_format_legacy_retirement_error_with_real_constants(self):
        result = format_legacy_retirement_error(
            LEGACY_SECTION_CONFIG_UNSUPPORTED,
            LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE,
        )
        assert result.startswith("LEGACY_SECTION_CONFIG_UNSUPPORTED:")
        assert "ansible_role_doc" in result


class TestResolveRoleConfigFile:
    def test_returns_default_path_when_no_config_file_present(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        result = resolve_role_config_file(str(role_root))
        assert result == role_root / SECTION_CONFIG_FILENAME

    def test_returns_existing_prism_yml(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        cfg = role_root / ".prism.yml"
        cfg.write_text("markers:\n  prefix: myprefix\n", encoding="utf-8")
        result = resolve_role_config_file(str(role_root))
        assert result == cfg

    def test_raises_for_legacy_config_file_present(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        legacy = role_root / LEGACY_SECTION_CONFIG_FILENAME
        legacy.write_text("markers:\n  prefix: old\n", encoding="utf-8")
        with pytest.raises(RuntimeError) as exc_info:
            resolve_role_config_file(str(role_root))
        assert LEGACY_SECTION_CONFIG_UNSUPPORTED in str(exc_info.value)

    def test_raises_when_explicit_config_path_is_legacy_filename(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        legacy_path = str(role_root / LEGACY_SECTION_CONFIG_FILENAME)
        with pytest.raises(RuntimeError) as exc_info:
            resolve_role_config_file(str(role_root), config_path=legacy_path)
        assert LEGACY_SECTION_CONFIG_UNSUPPORTED in str(exc_info.value)


class TestLoadReadmeMarkerPrefix:
    def test_returns_default_when_no_config_file(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        result = load_readme_marker_prefix(str(role_root))
        assert result == DEFAULT_DOC_MARKER_PREFIX

    def test_loads_prefix_from_valid_yaml(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        cfg = role_root / ".prism.yml"
        cfg.write_text("markers:\n  prefix: mypfx\n", encoding="utf-8")
        result = load_readme_marker_prefix(str(role_root))
        assert result == "mypfx"

    def test_returns_default_for_invalid_prefix_chars(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        cfg = role_root / ".prism.yml"
        cfg.write_text("markers:\n  prefix: 'bad prefix!'\n", encoding="utf-8")
        warnings: list[str] = []
        result = load_readme_marker_prefix(str(role_root), warning_collector=warnings)
        assert result == DEFAULT_DOC_MARKER_PREFIX
        assert any("unsupported characters" in w for w in warnings)


class TestLoadFailOnUnconstrainedDynamicIncludes:
    def test_returns_false_by_default_no_config(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        result = load_fail_on_unconstrained_dynamic_includes(str(role_root))
        assert result is False

    def test_loads_true_from_yaml(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        cfg = role_root / ".prism.yml"
        cfg.write_text(
            "scan:\n  fail_on_unconstrained_dynamic_includes: true\n",
            encoding="utf-8",
        )
        result = load_fail_on_unconstrained_dynamic_includes(str(role_root))
        assert result is True

    def test_loads_false_explicitly_from_yaml(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        cfg = role_root / ".prism.yml"
        cfg.write_text(
            "scan:\n  fail_on_unconstrained_dynamic_includes: false\n",
            encoding="utf-8",
        )
        result = load_fail_on_unconstrained_dynamic_includes(str(role_root))
        assert result is False


class TestLoadPolicyRulesFromConfig:
    def test_returns_empty_list_when_no_config(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        result = load_policy_rules_from_config(str(role_root))
        assert result == []

    def test_returns_rules_from_valid_config(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        cfg = role_root / ".prism.yml"
        cfg.write_text(
            "policy_rules:\n  - id: r1\n    description: Rule one\n",
            encoding="utf-8",
        )
        result = load_policy_rules_from_config(str(role_root))
        assert len(result) == 1
        assert result[0]["id"] == "r1"

    def test_returns_empty_list_when_policy_rules_not_list(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        cfg = role_root / ".prism.yml"
        cfg.write_text("policy_rules: not_a_list\n", encoding="utf-8")
        result = load_policy_rules_from_config(str(role_root))
        assert result == []

    def test_filters_out_non_dict_entries(self, tmp_path):
        role_root = tmp_path / "myrole"
        role_root.mkdir()
        cfg = role_root / ".prism.yml"
        cfg.write_text(
            "policy_rules:\n  - id: good\n    description: ok\n  - just_a_string\n",
            encoding="utf-8",
        )
        result = load_policy_rules_from_config(str(role_root))
        assert len(result) == 1
        assert result[0]["id"] == "good"


class TestLoadPatternConfig:
    def test_returns_dict_with_section_aliases_key(self):
        result = load_pattern_config()
        assert isinstance(result, dict)
        assert "section_aliases" in result

    def test_returns_dict_with_expected_top_level_keys(self):
        result = load_pattern_config()
        assert "sensitivity" in result
        assert "variable_guidance" in result

    def test_override_path_merged(self, tmp_path):
        override = tmp_path / "override.yml"
        override.write_text(
            "section_aliases:\n  my_alias: target_section\n", encoding="utf-8"
        )
        result = load_pattern_config(override_path=override)
        assert result["section_aliases"].get("my_alias") == "target_section"


class TestBuildPolicyContext:
    def test_returns_policy_context_with_expected_keys(self):
        policy = load_pattern_config()
        ctx = build_policy_context(policy)
        assert "section_aliases" in ctx
        assert "ignored_identifiers" in ctx
        assert "variable_guidance_keywords" in ctx

    def test_ignored_identifiers_is_frozenset(self):
        policy = load_pattern_config()
        ctx = build_policy_context(policy)
        assert isinstance(ctx["ignored_identifiers"], frozenset)

    def test_variable_guidance_keywords_is_tuple(self):
        policy = load_pattern_config()
        ctx = build_policy_context(policy)
        assert isinstance(ctx["variable_guidance_keywords"], tuple)

    def test_section_aliases_is_dict(self):
        policy = load_pattern_config()
        ctx = build_policy_context(policy)
        assert isinstance(ctx["section_aliases"], dict)


class TestLoadSectionDisplayTitles:
    def test_returns_empty_dict_for_nonexistent_path(self, tmp_path):
        missing = tmp_path / "no_such_file.yml"
        result = load_section_display_titles(missing)
        assert result == {}

    def test_returns_empty_dict_for_valid_file_without_display_titles_key(
        self, tmp_path
    ):
        f = tmp_path / "titles.yml"
        f.write_text("other_key: value\n", encoding="utf-8")
        result = load_section_display_titles(f)
        assert result == {}

    def test_loads_display_titles_from_valid_yaml(self, tmp_path):
        f = tmp_path / "titles.yml"
        f.write_text(
            "display_titles:\n  requirements: Requirements\n  variables: Variables\n",
            encoding="utf-8",
        )
        result = load_section_display_titles(f)
        assert result["requirements"] == "Requirements"
        assert result["variables"] == "Variables"

    def test_collects_yaml_error_warning(self, tmp_path):
        f = tmp_path / "bad.yml"
        f.write_text(":\n  bad: [\n", encoding="utf-8")
        warnings: list[str] = []
        result = load_section_display_titles(f, warning_collector=warnings)
        assert result == {}
        assert any("YAML" in w or "yaml" in w.lower() for w in warnings)


class TestScannerConfigImports:
    def test_all_top_level_imports_resolvable(self):
        import prism.scanner_config  # noqa: F401
        import prism.scanner_config.section  # noqa: F401
        import prism.scanner_config.legacy_retirement  # noqa: F401
        import prism.scanner_config.readme  # noqa: F401
        import prism.scanner_config.marker  # noqa: F401
        import prism.scanner_config.policy  # noqa: F401
        import prism.scanner_config.patterns  # noqa: F401
        import prism.scanner_config.style  # noqa: F401

    def test_package_exports_key_symbols(self):
        from prism.scanner_config import (  # noqa: F401
            AuditReport,
            AuditRule,
            AuditViolation,
            DEFAULT_DOC_MARKER_PREFIX,
            SECTION_CONFIG_FILENAME,
            build_policy_context,
            load_pattern_config,
            load_policy_rules_from_config,
            load_readme_marker_prefix,
            resolve_role_config_file,
        )
