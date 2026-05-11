"""T2-02: ScanOptionsSchema — single source of truth tests."""

from __future__ import annotations

import pytest

from prism.scanner_data.scan_options_schema import (
    SCAN_OPTIONS_SCHEMA,
    ScanOptionsValidationError,
    get_default_scan_options,
    get_scan_options_documentation,
    validate_scan_options,
)


def test_schema_contains_all_canonical_keys() -> None:
    """Schema must include every key produced by build_run_scan_options_canonical."""
    canonical_keys = {
        "role_path",
        "role_name_override",
        "readme_config_path",
        "policy_config_path",
        "include_vars_main",
        "exclude_path_patterns",
        "detailed_catalog",
        "include_task_parameters",
        "include_task_runbooks",
        "inline_task_runbooks",
        "include_collection_checks",
        "keep_unknown_style_sections",
        "adopt_heading_mode",
        "vars_seed_paths",
        "style_readme_path",
        "style_source_path",
        "style_guide_skeleton",
        "compare_role_path",
        "fail_on_unconstrained_dynamic_includes",
        "fail_on_yaml_like_task_annotations",
        "ignore_unresolved_internal_underscore_references",
        "policy_context",
    }
    assert canonical_keys.issubset(set(SCAN_OPTIONS_SCHEMA.keys()))


def test_get_default_scan_options_returns_only_non_none_defaults() -> None:
    defaults = get_default_scan_options()
    assert defaults["include_vars_main"] is True
    assert defaults["detailed_catalog"] is False
    assert "role_path" not in defaults  # has no default


def test_get_scan_options_documentation_renders_table() -> None:
    md = get_scan_options_documentation()
    assert "| Option |" in md
    assert "`role_path`" in md
    assert "str" in md


def test_validate_scan_options_accepts_minimal_valid_options() -> None:
    validate_scan_options({"role_path": "/x"})


def test_validate_scan_options_rejects_non_mapping() -> None:
    with pytest.raises(ScanOptionsValidationError, match="must be a mapping"):
        validate_scan_options(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_validate_scan_options_rejects_unknown_keys() -> None:
    with pytest.raises(ScanOptionsValidationError, match="unknown scan_options key"):
        validate_scan_options({"role_path": "/x", "totally_invalid_key": True})


def test_validate_scan_options_rejects_wrong_type() -> None:
    with pytest.raises(ScanOptionsValidationError, match="expected str"):
        validate_scan_options({"role_path": 123})


def test_validate_scan_options_rejects_disallowed_none() -> None:
    with pytest.raises(ScanOptionsValidationError, match="must not be None"):
        validate_scan_options({"role_path": None})


def test_validate_scan_options_allows_none_for_optional_keys() -> None:
    validate_scan_options({"role_path": "/x", "role_name_override": None})


def test_validate_scan_options_strict_requires_all_required_keys() -> None:
    with pytest.raises(ScanOptionsValidationError, match="missing required"):
        validate_scan_options({"role_path": "/x"}, strict=True)


def test_validate_scan_options_strict_accepts_full_canonical_dict() -> None:
    options = {
        name: (
            "/x"
            if name == "role_path"
            else (
                False
                if entry.types == (bool,) and not entry.allow_none
                else (entry.default if entry.default is not None else None)
            )
        )
        for name, entry in SCAN_OPTIONS_SCHEMA.items()
        if entry.required
    }
    # Above sets required keys; allow None for optional-typed entries.
    validate_scan_options(options, strict=True)


def test_build_run_scan_options_canonical_invokes_validator() -> None:
    """Drift in build_run_scan_options_canonical must surface via the validator."""
    from prism.scanner_core.scan_request import build_run_scan_options_canonical

    out = build_run_scan_options_canonical(
        role_path="/role",
        role_name_override=None,
        readme_config_path=None,
        include_vars_main=True,
        exclude_path_patterns=None,
        detailed_catalog=False,
        include_task_parameters=True,
        include_task_runbooks=True,
        inline_task_runbooks=True,
        include_collection_checks=True,
        keep_unknown_style_sections=True,
        adopt_heading_mode=None,
        vars_seed_paths=None,
        style_readme_path=None,
        style_source_path=None,
        style_guide_skeleton=False,
        compare_role_path=None,
        fail_on_unconstrained_dynamic_includes=None,
        fail_on_yaml_like_task_annotations=None,
        ignore_unresolved_internal_underscore_references=None,
    )
    # Calling validate again must succeed for the canonical output.
    validate_scan_options(out)
    assert out["role_path"] == "/role"
